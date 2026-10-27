"""
Policy gateway tests: schema allowlist, approval binding (run/ticket/tool/args hash),
reviewer edits, expiry, denial auditing and the kill switch.
"""
import time

import pytest
from fastapi import HTTPException

from services import mcp_registry
from services.gateway import gateway
from services.mcp_billing import server as mcp_billing
from services.gateway.tokens import ScopedJWT, make_args_hash

RUN, TICKET = "run-1", "tkt-1"
REQUESTER = "john.smith@acme-corp.com"


@pytest.fixture(autouse=True)
def _reset_gateway_state():
    gateway._approvals.clear()
    gateway._idempotency_store.clear()
    gateway._run_budgets.clear()
    gateway._audit_log.clear()
    gateway._kill_switch = False
    mcp_billing._idempotency_store.clear()
    mcp_billing._refunds.clear()
    yield
    gateway._kill_switch = False


def trusted_context():
    invoice = {"id": "INV-001", "invoice_date": "2026-10-17T00:00:00+00:00", "amount_cents": 3000}
    return {
        "ticket_id": TICKET,
        "account_id": "ACC-001",
        "account": {
            "id": "ACC-001",
            "is_strategic": False,
            "is_legal_hold": False,
            "authorized_contacts": [REQUESTER],
        },
        "requester_email": REQUESTER,
        "requester": {"verified": True, "email": REQUESTER},
        "invoice": invoice,
        "invoices": ["INV-001"],
        "INV-001": invoice,
    }


def make_request(tool, args, approval_id=None, run_id=RUN, ticket_id=TICKET, context=None):
    token = ScopedJWT(secret=gateway.GATEWAY_JWT_SECRET).generate(
        run_id=run_id, ticket_id=ticket_id, tool=tool, args_hash=make_args_hash(tool, args)
    )
    return gateway.GatewayRequest(
        run_id=run_id,
        ticket_id=ticket_id,
        tool=tool,
        args=args,
        token=token,
        approval_id=approval_id,
        trusted_context=context if context is not None else trusted_context(),
    )


REFUND_ARGS = {"invoice_id": "INV-001", "amount_cents": 3000, "reason": "duplicate", "idempotency_key": "k1"}


def register(approval_id="appr-1", status="approved", args=None, **overrides):
    record = {
        "id": approval_id,
        "run_id": RUN,
        "ticket_id": TICKET,
        "tool": "billing.issue_refund",
        "args_hash": make_args_hash("billing.issue_refund", args or REFUND_ARGS),
        "status": status,
        "expires_at": time.time() + 3600,
    }
    record.update(overrides)
    gateway.register_approval_record(record)


# ── Step 2: schema / allowlist comes from the MCP registry ─────────────────

def test_every_registered_tool_passes_allowlist():
    for tool in mcp_registry.list_all_tools():
        assert gateway._required_args(tool["qualified_name"]) is not None


def test_unknown_tool_rejected():
    with pytest.raises(HTTPException) as exc:
        gateway.step2_validate_schema(make_request("ticketing.patch_ticket", {"ticket_id": TICKET}))
    assert exc.value.status_code == 403


def test_preview_plan_change_uses_registry_arg_names():
    gateway.step2_validate_schema(
        make_request("billing.preview_plan_change", {"subscription_id": "SUB-001", "target_plan": "pro"})
    )


def test_set_tags_is_allowed_and_missing_args_rejected():
    gateway.step2_validate_schema(make_request("ticketing.set_tags", {"ticket_id": TICKET, "tags": ["x"]}))
    with pytest.raises(HTTPException) as exc:
        gateway.step2_validate_schema(make_request("ticketing.set_tags", {"ticket_id": TICKET}))
    assert exc.value.status_code == 422


# ── Step 6: approval binding ───────────────────────────────────────────────

async def test_refund_without_approval_is_denied_and_audited():
    with pytest.raises(HTTPException) as exc:
        await gateway.execute(make_request("billing.issue_refund", REFUND_ARGS))
    assert "APPROVAL REQUIRED" in exc.value.detail
    assert [e["event"] for e in gateway._audit_log] == ["tool_call_denied"]


async def test_approved_refund_executes_once_and_replays():
    register()
    res = await gateway.execute(make_request("billing.issue_refund", REFUND_ARGS, approval_id="appr-1"))
    assert res.success and not res.idempotent_replay
    assert res.result["status"] == "succeeded"
    replay = await gateway.execute(make_request("billing.issue_refund", REFUND_ARGS, approval_id="appr-1"))
    assert replay.idempotent_replay


async def test_pending_approval_is_rejected():
    register(status="pending")
    with pytest.raises(HTTPException) as exc:
        await gateway.execute(make_request("billing.issue_refund", REFUND_ARGS, approval_id="appr-1"))
    assert "not 'approved'" in exc.value.detail


async def test_args_tampering_after_approval_is_rejected():
    register()
    tampered = {**REFUND_ARGS, "amount_cents": 2900}
    with pytest.raises(HTTPException) as exc:
        await gateway.execute(make_request("billing.issue_refund", tampered, approval_id="appr-1"))
    assert "HASH MISMATCH" in exc.value.detail


async def test_approval_cannot_be_reused_on_another_ticket():
    register()
    ctx = trusted_context()
    ctx["ticket_id"] = "tkt-2"
    with pytest.raises(HTTPException) as exc:
        await gateway.execute(
            make_request("billing.issue_refund", REFUND_ARGS, approval_id="appr-1", ticket_id="tkt-2", context=ctx)
        )
    assert "different run or ticket" in exc.value.detail


async def test_expired_approval_is_rejected():
    register(expires_at=time.time() - 1)
    with pytest.raises(HTTPException) as exc:
        await gateway.execute(make_request("billing.issue_refund", REFUND_ARGS, approval_id="appr-1"))
    assert "EXPIRED" in exc.value.detail


async def test_lookup_is_exact_match_only():
    register(approval_id="appr-1234567890")
    with pytest.raises(HTTPException) as exc:
        await gateway.execute(make_request("billing.issue_refund", REFUND_ARGS, approval_id="appr-1"))
    assert "not found" in exc.value.detail


async def test_reviewer_edit_rebinds_hash_to_edited_args():
    register(status="pending")
    edited = {**REFUND_ARGS, "amount_cents": 2000}
    assert gateway.set_approval_status("appr-1", "approved", "lead", new_args=edited)
    # the originally proposed args no longer match ...
    with pytest.raises(HTTPException):
        await gateway.execute(make_request("billing.issue_refund", REFUND_ARGS, approval_id="appr-1"))
    # ... the edited ones do
    res = await gateway.execute(make_request("billing.issue_refund", edited, approval_id="appr-1"))
    assert res.result["amount_cents"] == 2000


def test_register_requires_binding_fields():
    with pytest.raises(ValueError):
        gateway.register_approval_record({"id": "x"})


# ── Other steps ────────────────────────────────────────────────────────────

async def test_forbidden_policy_is_blocked():
    args = {**REFUND_ARGS, "amount_cents": 60000, "idempotency_key": "k2"}
    with pytest.raises(HTTPException) as exc:
        await gateway.execute(make_request("billing.issue_refund", args))
    assert exc.value.status_code == 403 and "FORBIDDEN" in exc.value.detail


async def test_hallucinated_invoice_id_is_blocked_by_provenance():
    args = {**REFUND_ARGS, "invoice_id": "INV-NOPE"}
    with pytest.raises(HTTPException) as exc:
        await gateway.execute(make_request("billing.issue_refund", args))
    assert "PROVENANCE" in exc.value.detail


async def test_write_without_authorized_contacts_fails_closed():
    ctx = trusted_context()
    ctx["account"].pop("authorized_contacts")
    with pytest.raises(HTTPException) as exc:
        await gateway.execute(
            make_request("ticketing.add_internal_note", {"ticket_id": TICKET, "body": "note"}, context=ctx)
        )
    assert "STEP4" in exc.value.detail


async def test_requester_not_in_authorized_contacts_is_blocked():
    ctx = trusted_context()
    ctx["requester_email"] = "attacker@evil.example"
    with pytest.raises(HTTPException) as exc:
        await gateway.execute(
            make_request("ticketing.add_internal_note", {"ticket_id": TICKET, "body": "note"}, context=ctx)
        )
    assert "STEP4" in exc.value.detail


async def test_kill_switch_blocks_execution():
    gateway._kill_switch = True
    with pytest.raises(HTTPException) as exc:
        await gateway.execute(make_request("ticketing.add_internal_note", {"ticket_id": TICKET, "body": "note"}))
    assert exc.value.status_code == 503


async def test_invalid_token_is_rejected():
    req = make_request("ticketing.add_internal_note", {"ticket_id": TICKET, "body": "note"})
    req.token = "not-a-token"
    with pytest.raises(HTTPException) as exc:
        await gateway.execute(req)
    assert exc.value.status_code == 401
