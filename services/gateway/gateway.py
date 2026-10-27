"""
services/gateway/gateway.py
The Policy Gateway — the ONLY authorized path from the agent to any backend.

12 sequential enforcement steps. ALL must pass or execution is blocked.
No step can be skipped, bypassed, or reordered.

CRITICAL: This is NOT a suggestion layer. It is the enforcement boundary.
The LangGraph workflow MUST call the gateway for every tool execution.
No direct backend calls are permitted from node code.
"""
import os
import time
import uuid
from datetime import datetime, UTC
from typing import Any

import httpx
import structlog
from dateutil.parser import parse as parse_date
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

import sys
from pathlib import Path
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services import mcp_registry
from services.gateway.tokens import ScopedJWT, make_args_hash
from app.policy.engine import PolicyContext, get_policy_engine
from app.reliability.circuit_breaker import get_circuit_breaker, CircuitOpenError
from app.reliability.readback import ReadBackVerifier, ReadBackState

log = structlog.get_logger()

# ─── Config from environment ───────────────────────────────────────────────
GATEWAY_JWT_SECRET = os.environ.get("GATEWAY_JWT_SECRET", "dev-secret-change-in-production")
MAX_TOOL_CALLS_PER_RUN = int(os.environ.get("MAX_TOOL_CALLS_PER_RUN", "20"))

app = FastAPI(title="ResolveOps Policy Gateway", version="1.0.0")

# In-memory kill switch (in production: Redis)
_kill_switch: bool = False
# In-memory idempotency store (in production: Postgres + Redis)
_idempotency_store: dict[str, dict] = {}
# In-memory tool-call counter per run: {run_id: {tool_calls: N}}
_run_budgets: dict[str, dict] = {}
# In-memory audit log. The backend registers a sink (set_audit_sink) that also persists
# each event to the hash-chained audit_log table.
_audit_log: list[dict] = []
_audit_sink = None


def set_audit_sink(sink) -> None:
    """Register a callable invoked with every audit event dict (None to disable)."""
    global _audit_sink
    _audit_sink = sink


def _emit_audit(event: dict) -> None:
    _audit_log.append(event)
    if _audit_sink is not None:
        try:
            _audit_sink(event)
        except Exception as e:  # noqa: BLE001 - audit sink problems must not break execution
            log.error("gateway.audit_sink_failed", error=str(e))

_DEFAULT_JWT_SECRET = "dev-secret-change-in-production"
if os.environ.get("ENVIRONMENT", "development").lower() == "production" and GATEWAY_JWT_SECRET == _DEFAULT_JWT_SECRET:
    raise RuntimeError("GATEWAY_JWT_SECRET must be set to a non-default value when ENVIRONMENT=production")

jwt_validator = ScopedJWT(secret=GATEWAY_JWT_SECRET)


# ─── Request / Response Models ─────────────────────────────────────────────

class GatewayRequest(BaseModel):
    run_id: str
    ticket_id: str
    tool: str = Field(description="Exact tool name: e.g. billing.issue_refund")
    args: dict[str, Any] = Field(default_factory=dict)
    token: str = Field(description="Scoped JWT for this specific tool call")
    approval_id: str | None = None  # Required for approval-tier actions
    # Context for provenance validation
    trusted_context: dict[str, Any] = Field(
        default_factory=dict,
        description="Verified context from prior tool results (invoice IDs, account IDs, etc.)"
    )


class GatewayResponse(BaseModel):
    success: bool
    result: Any = None
    idempotent_replay: bool = False
    audit_event_id: str
    error: str | None = None
    blocked_reason: str | None = None


# ─── Step Implementations ───────────────────────────────────────────────────

def step1_authenticate_run(req: GatewayRequest) -> None:
    """Step 1: Validate scoped JWT."""
    args_hash = make_args_hash(req.tool, req.args)
    try:
        jwt_validator.validate(
            token=req.token,
            expected_run_id=req.run_id,
            expected_ticket_id=req.ticket_id,
            expected_tool=req.tool,
            expected_args_hash=args_hash,
        )
    except ValueError as e:
        raise HTTPException(status_code=401, detail=f"STEP1 AUTH FAILED: {e}")


# Arguments the gateway requires on top of each MCP tool's own input schema.
_EXTRA_REQUIRED: dict[str, list[str]] = {
    "billing.issue_refund": ["idempotency_key"],
    "billing.issue_credit": ["idempotency_key"],
    "billing.change_plan": ["idempotency_key"],
    "access.grant_access": ["expiry_days"],
}


def _required_args(tool: str) -> list[str] | None:
    """Required args for `tool`, or None if the tool is not in the MCP registry."""
    meta = mcp_registry.get_tool_metadata(tool)
    if meta is None:
        return None
    required = list(meta.get("inputSchema", {}).get("required", []))
    for extra in _EXTRA_REQUIRED.get(tool, []):
        if extra not in required:
            required.append(extra)
    return required


def step2_validate_schema(req: GatewayRequest) -> None:
    """Step 2: Validate args against the tool's registered schema (allowlist = MCP registry)."""
    required = _required_args(req.tool)
    if required is None:
        raise HTTPException(
            status_code=403,
            detail=f"STEP2 SCHEMA FAIL: Unknown tool '{req.tool}' — not in approved tool registry"
        )
    missing = [f for f in required if f not in req.args]
    if missing:
        raise HTTPException(
            status_code=422,
            detail=f"STEP2 SCHEMA FAIL: Missing required args: {missing}"
        )


def step3_validate_provenance(req: GatewayRequest) -> None:
    """
    Step 3: All IDs in args must originate from trusted_context.
    Prevents the agent from inventing or hallucinating IDs.

    Any ID-like arg (ending in _id, or named 'email') must appear
    in the trusted context gathered from real tool results.
    """
    if not req.trusted_context:
        # If no context provided, skip provenance for read-only tools
        meta = mcp_registry.get_tool_metadata(req.tool)
        if meta and meta.get("annotations", {}).get("readOnlyHint") is True:
            return
        # Write tools without context → fail
        raise HTTPException(
            status_code=403,
            detail="STEP3 PROVENANCE FAIL: Trusted context is required for write operations"
        )

    # Build flat set of all trusted values from context
    trusted_values: set[str] = set()
    _flatten_values(req.trusted_context, trusted_values)

    # Check ID fields
    id_fields = [k for k in req.args if k.endswith("_id") or k in ("email", "user_email")]
    for field in id_fields:
        value = str(req.args[field])
        if value not in trusted_values:
            raise HTTPException(
                status_code=403,
                detail=f"STEP3 PROVENANCE FAIL: '{field}={value}' not found in trusted context — "
                       f"possible hallucinated or injected identifier"
            )


def _flatten_values(obj: Any, result: set, depth: int = 0):
    """Recursively extract all string/numeric values from a nested dict."""
    if depth > 5:
        return
    if isinstance(obj, dict):
        for v in obj.values():
            _flatten_values(v, result, depth + 1)
    elif isinstance(obj, (list, tuple)):
        for item in obj:
            _flatten_values(item, result, depth + 1)
    elif isinstance(obj, (str, int, float)) and obj:
        result.add(str(obj))


def step4_bind_identity(req: GatewayRequest) -> None:
    """
    Step 4: Verify requester is an authorized contact for the target account.
    Prevents wrong-requester attacks (attacker@gmail.com targeting Acme Corp).
    """
    ctx = req.trusted_context
    requester_email = ctx.get("requester_email", "")
    account_id = ctx.get("account_id") or req.args.get("account_id", "")

    # Skip identity check for non-account-specific reads
    if req.tool in ("kb.search_policy",):
        return

    if not requester_email:
        raise HTTPException(status_code=403, detail="STEP4 IDENTITY FAIL: No requester email in context")

    authorized_contacts = ctx.get("account", {}).get("authorized_contacts", [])
    if not authorized_contacts:
        meta = mcp_registry.get_tool_metadata(req.tool)
        read_only = bool(meta and meta.get("annotations", {}).get("readOnlyHint") is True)
        if read_only:
            return
        # Fail closed: a write needs a known list of authorized contacts to check against.
        raise HTTPException(
            status_code=403,
            detail="STEP4 IDENTITY FAIL: No authorized-contact list in trusted context for a write operation",
        )

    if requester_email not in authorized_contacts:
        raise HTTPException(
            status_code=403,
            detail=f"STEP4 IDENTITY FAIL: '{requester_email}' is not an authorized contact "
                   f"for account '{account_id}'"
        )


def step5_evaluate_policy(req: GatewayRequest) -> dict:
    """
    Step 5: Evaluate policy rules.
    Returns policy decision dict. Raises 403 if forbidden.
    """
    engine = get_policy_engine()
    ctx_data = req.trusted_context or {}

    invoice_ctx = ctx_data.get("invoice")
    if not invoice_ctx and "invoice_id" in req.args:
        invoice_ctx = ctx_data.get(req.args["invoice_id"])
    if not invoice_ctx and ctx_data.get("invoices"):
        invoices_list = ctx_data.get("invoices")
        if isinstance(invoices_list, list) and invoices_list:
            first_inv = invoices_list[0]
            invoice_ctx = ctx_data.get(first_inv) if isinstance(first_inv, str) else first_inv
    if invoice_ctx and "age_days" not in invoice_ctx:
        try:
            inv_date = parse_date(invoice_ctx.get("invoice_date", ""))
            if inv_date.tzinfo is None:
                inv_date = inv_date.replace(tzinfo=UTC)
            age_days = (datetime.now(UTC) - inv_date).days
        except Exception:
            # Unparseable date: assume old so age-limited auto rules do not apply.
            age_days = 10_000
        invoice_ctx = {**invoice_ctx, "age_days": age_days}

    policy_ctx = PolicyContext(
        tool=req.tool,
        args=req.args,
        account=ctx_data.get("account", {}),
        requester=ctx_data.get("requester", {}),
        invoice=invoice_ctx,
    )
    decision = engine.evaluate(policy_ctx)

    if decision.tier == "forbidden":
        raise HTTPException(
            status_code=403,
            detail=f"STEP5 POLICY FORBIDDEN: Rule {decision.rule_id} — {decision.reason}"
        )

    return {"tier": decision.tier, "rule_id": decision.rule_id, "approver_role": decision.approver_role}


def step6_validate_approval(req: GatewayRequest, policy_decision: dict) -> None:
    """
    Step 6: If approval-tier, validate approval exists, not expired, hash matches.
    The hash MUST match exactly — any arg modification invalidates the approval.
    """
    if policy_decision["tier"] != "approval":
        return

    if not req.approval_id:
        raise HTTPException(
            status_code=403,
            detail="STEP6 APPROVAL REQUIRED: This action requires human approval. "
                   "Submit for approval via POST /api/approvals first."
        )

    # Look up approval record (in-memory registry, populated by the approval flow)
    approval_record = _get_approval(req.approval_id)
    if not approval_record:
        raise HTTPException(status_code=403, detail=f"STEP6 APPROVAL FAIL: Approval {req.approval_id} not found")

    # The approval must belong to this exact run + ticket (no cross-ticket reuse).
    if approval_record.get("run_id") != req.run_id or approval_record.get("ticket_id") != req.ticket_id:
        raise HTTPException(
            status_code=403,
            detail="STEP6 APPROVAL FAIL: Approval was issued for a different run or ticket",
        )
    if approval_record.get("tool") != req.tool:
        raise HTTPException(
            status_code=403,
            detail="STEP6 APPROVAL FAIL: Approval was issued for a different tool",
        )

    if approval_record.get("status") != "approved":
        raise HTTPException(
            status_code=403,
            detail=f"STEP6 APPROVAL FAIL: Approval status is '{approval_record.get('status')}', not 'approved'"
        )

    # Expiry check
    expires_at = approval_record.get("expires_at") or 0
    if time.time() > expires_at:
        raise HTTPException(status_code=403, detail="STEP6 APPROVAL EXPIRED: Approval has expired (24h limit)")

    # Hash match — accepts with or without idempotency key
    expected_hash = make_args_hash(req.tool, req.args)
    expected_hash_no_idem = make_args_hash(req.tool, {k: v for k, v in req.args.items() if k != "idempotency_key"})
    stored_hash = approval_record.get("args_hash")
    if not stored_hash or (stored_hash != expected_hash and stored_hash != expected_hash_no_idem):
        raise HTTPException(
            status_code=403,
            detail="STEP6 APPROVAL HASH MISMATCH: Approved args don't match submitted args. "
                   "Possible tampering or edit. Create a new approval request."
        )


def step7_check_idempotency(req: GatewayRequest) -> dict | None:
    """
    Step 7: Check idempotency store. Return cached result if exists.
    Key = SHA256(run_id + tool + sorted_args)
    """
    idem_key = make_args_hash(f"{req.run_id}:{req.ticket_id}", req.args)
    if idem_key in _idempotency_store:
        cached = _idempotency_store[idem_key]
        log.info("gateway.idempotency.replay", run_id=req.run_id, tool=req.tool)
        return cached
    return None


def step8_check_limits(req: GatewayRequest) -> None:
    """Step 8: Enforce per-run budget limits."""
    budgets = _run_budgets.setdefault(req.run_id, {"tool_calls": 0})
    if budgets["tool_calls"] >= MAX_TOOL_CALLS_PER_RUN:
        raise HTTPException(
            status_code=429,
            detail=f"STEP8 BUDGET EXCEEDED: max_tool_calls={MAX_TOOL_CALLS_PER_RUN} reached for run {req.run_id}"
        )


def step9_audit_start(req: GatewayRequest, audit_event_id: str) -> None:
    """Step 9: Write audit event BEFORE execution."""
    event = {
        "id": audit_event_id,
        "timestamp": datetime.now(UTC).isoformat(),
        "event": "tool_call_start",
        "run_id": req.run_id,
        "ticket_id": req.ticket_id,
        "tool": req.tool,
        "args_hash": make_args_hash(req.tool, req.args),
        "args_redacted": _redact_pii(req.args),
        "actor_type": "agent",
        "status": "executing",
    }
    _emit_audit(event)
    log.info("gateway.audit.start", audit_type=event.get("event"), tool=event.get("tool"), run_id=event.get("run_id"))


def step10_check_kill_switch(req: GatewayRequest) -> None:
    """Step 10: Check global kill switch."""
    if _kill_switch:
        raise HTTPException(
            status_code=503,
            detail="STEP10 KILL SWITCH ACTIVE: All agent tool execution is suspended. "
                   "Contact support-ops@northwindcloud.com"
        )


async def step11_execute(req: GatewayRequest) -> Any:
    """
    Step 11: Dispatch to standardized MCP tool server or backend.
    Enforces per-service circuit breaker and commit-timeout read-back verification.
    """
    tool = req.tool
    args = dict(req.args)
    service = tool.split(".")[0] if "." in tool else tool
    breaker = get_circuit_breaker(service)

    # 1. Circuit breaker guard
    try:
        breaker.can_execute()
    except CircuitOpenError as e:
        log.error("gateway.circuit_open_blocked", tool=tool, service=service)
        raise HTTPException(status_code=503, detail=str(e))

    # 2. Dispatch via standardized MCP registry
    try:
        idemp_key = args.get("idempotency_key") or make_args_hash(tool, args)
        headers = {"Idempotency-Key": idemp_key}
        result = await mcp_registry.dispatch_tool(tool, args, headers=headers)
        breaker.record_success()

        return result

    except httpx.TimeoutException:
        breaker.record_failure()
        log.warning("gateway.dispatch_timeout", tool=tool)
        # Attempt read-back verification
        idemp_key = args.get("idempotency_key")
        readback_res = await ReadBackVerifier.reconcile_timeout(tool, args, idemp_key)
        if readback_res.get("state") == ReadBackState.COMMITTED:
            breaker.record_success()
            return readback_res.get("result", {"status": "reconciled_committed"})
        elif readback_res.get("state") == ReadBackState.INDETERMINATE:
            raise HTTPException(
                status_code=502,
                detail=f"TIMEOUT RECONCILIATION INDETERMINATE: Mutation '{tool}' timed out and state cannot be confirmed. Manual reconciliation required."
            )
        else:
            raise HTTPException(status_code=504, detail=f"Backend timeout executing '{tool}'")

    except ValueError as e:
        # Schema / domain constraint violation (e.g. forbidden admin role)
        breaker.record_success()
        raise HTTPException(status_code=403, detail=str(e))

    except Exception as e:
        breaker.record_failure()
        log.error("gateway.dispatch_error", tool=tool, error=str(e))
        raise HTTPException(status_code=502, detail=f"Backend execution failure: {str(e)}")


def step12_audit_result(
    req: GatewayRequest,
    audit_event_id: str,
    result: Any,
    idempotent_replay: bool,
) -> None:
    """Step 12: Write execution result to audit log."""
    event = {
        "id": f"{audit_event_id}-result",
        "timestamp": datetime.now(UTC).isoformat(),
        "event": "tool_call_result",
        "run_id": req.run_id,
        "ticket_id": req.ticket_id,
        "tool": req.tool,
        "args_hash": make_args_hash(req.tool, req.args),
        "result_status": "success",
        "idempotent_replay": idempotent_replay,
        "actor_type": "agent",
    }
    _emit_audit(event)
    log.info("gateway.audit.result", audit_event=event.get("event"), tool=event.get("tool"), result_status=event.get("result_status"))


# ─── Helpers ───────────────────────────────────────────────────────────────

def _redact_pii(args: dict) -> dict:
    """Redact PII fields before logging."""
    PII_FIELDS = {"email", "user_email", "phone", "card_number", "billing_address", "body"}
    redacted = {}
    for k, v in args.items():
        if k in PII_FIELDS:
            if isinstance(v, str) and "@" in v:
                parts = v.split("@")
                redacted[k] = f"{parts[0][:1]}***@{parts[1]}"
            else:
                redacted[k] = "[REDACTED]"
        else:
            redacted[k] = v
    return redacted


# In-memory approval registry: approval_id -> record. Entries are written by the
# approval flow (see register_approval_record / set_approval_status). It is not
# persisted by the gateway: after a restart the approvals API re-registers a record
# from its database row when a reviewer approves (fail closed otherwise).
_approvals: dict[str, dict] = {}


def _get_approval(approval_id: str) -> dict | None:
    """Exact-match lookup in the in-memory approval registry."""
    return _approvals.get(approval_id)


def register_approval_record(record: dict) -> None:
    """Register (or replace) an approval record. Requires id/run_id/ticket_id/tool/args_hash."""
    required = ("id", "run_id", "ticket_id", "tool", "args_hash")
    missing = [k for k in required if not record.get(k)]
    if missing:
        raise ValueError(f"approval record missing fields: {missing}")
    _approvals[record["id"]] = dict(record)


def set_approval_status(
    approval_id: str,
    status: str,
    reviewer_id: str | None = None,
    new_args: dict | None = None,
) -> bool:
    """
    Update a registered approval. If `new_args` is given (reviewer edit), the stored
    hash is re-bound to the edited arguments so only those exact args can execute.
    Returns False if the approval is not registered.
    """
    rec = _approvals.get(approval_id)
    if rec is None:
        return False
    rec["status"] = status
    rec["reviewed_at"] = datetime.now(UTC).isoformat()
    rec["reviewer_id"] = reviewer_id
    if new_args is not None:
        rec["args_hash"] = make_args_hash(rec["tool"], new_args)
    return True


# ─── Gateway Endpoint ───────────────────────────────────────────────────────

@app.post("/execute", response_model=GatewayResponse)
async def execute(req: GatewayRequest) -> GatewayResponse:
    """
    The ONE AND ONLY path from the agent to any backend.
    All 12 steps must pass. Any failure → HTTP error, no execution.
    """
    audit_event_id = str(uuid.uuid4())[:8]

    log.info(
        "gateway.execute.start",
        run_id=req.run_id,
        ticket_id=req.ticket_id,
        tool=req.tool,
        audit_event_id=audit_event_id,
    )

    # ── Sequential 12-step enforcement ────────────────────────────────────
    try:
        step1_authenticate_run(req)
        step2_validate_schema(req)
        step3_validate_provenance(req)
        step4_bind_identity(req)
        policy_decision = step5_evaluate_policy(req)
        step6_validate_approval(req, policy_decision)

        # Idempotency — return cached if exists
        cached = step7_check_idempotency(req)
        if cached:
            return GatewayResponse(
                success=True,
                result=cached["result"],
                idempotent_replay=True,
                audit_event_id=audit_event_id,
            )

        step8_check_limits(req)
        step9_audit_start(req, audit_event_id)
        step10_check_kill_switch(req)

        # Execute
        result = await step11_execute(req)
    except HTTPException as exc:
        _emit_audit({
            "id": f"{audit_event_id}-denied",
            "timestamp": datetime.now(UTC).isoformat(),
            "event": "tool_call_denied",
            "run_id": req.run_id,
            "ticket_id": req.ticket_id,
            "tool": req.tool,
            "status_code": exc.status_code,
            "reason": str(exc.detail),
            "actor_type": "agent",
        })
        raise

    # Post-execution accounting
    budgets = _run_budgets.setdefault(req.run_id, {"tool_calls": 0})
    budgets["tool_calls"] += 1

    # Cache result for idempotency
    idem_key = make_args_hash(f"{req.run_id}:{req.ticket_id}", req.args)
    _idempotency_store[idem_key] = {"result": result, "timestamp": time.time()}

    step12_audit_result(req, audit_event_id, result, idempotent_replay=False)

    return GatewayResponse(
        success=True,
        result=result,
        idempotent_replay=False,
        audit_event_id=audit_event_id,
    )


# ─── Management Endpoints ───────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "kill_switch": _kill_switch, "service": "gateway"}


def kill_switch_active() -> bool:
    """Whether the global kill switch is currently engaged (in-memory, per process)."""
    return _kill_switch


def set_kill_switch(active: bool) -> bool:
    """Engage or release the global kill switch. Returns the new state."""
    global _kill_switch
    _kill_switch = bool(active)
    if _kill_switch:
        log.warning("gateway.kill_switch.ACTIVATED")
    else:
        log.warning("gateway.kill_switch.DEACTIVATED")
    return _kill_switch


@app.post("/admin/kill-switch/activate")
def activate_kill_switch():
    set_kill_switch(True)
    return {"kill_switch": True, "message": "All agent execution suspended"}


@app.post("/admin/kill-switch/deactivate")
def deactivate_kill_switch():
    set_kill_switch(False)
    return {"kill_switch": False, "message": "Agent execution resumed"}


@app.get("/audit")
def get_audit_log(run_id: str = None, ticket_id: str = None, limit: int = 100):
    events = _audit_log
    if run_id:
        events = [e for e in events if e.get("run_id") == run_id]
    if ticket_id:
        events = [e for e in events if e.get("ticket_id") == ticket_id]
    return {"events": events[-limit:], "total": len(events)}


@app.post("/approvals/{approval_id}/register")
def register_approval(approval_id: str, record: dict):
    """Register an approved action (called by the approval API after human approval)."""
    try:
        register_approval_record({**record, "id": approval_id})
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return {"registered": True, "approval_id": approval_id}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
