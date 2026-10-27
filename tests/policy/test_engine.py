"""
Policy Engine Tests — 8 mandatory scenarios from M1-P3 verification.
All must pass before M1 is marked complete.
"""
import sys
from pathlib import Path

# Add backend to path so app.policy.engine can be imported
sys.path.insert(0, str(Path(__file__).parents[2] / "backend"))

import pytest
from app.policy.engine import PolicyEngine, PolicyContext

# Absolute path — repo root is 2 levels above tests/
POLICY_FILE = Path(__file__).parents[2] / "policy" / "rules.yaml"


@pytest.fixture(scope="module")
def engine():
    return PolicyEngine(POLICY_FILE)


def ctx(tool: str, args: dict = None, account: dict = None, requester: dict = None,
        invoice: dict = None, subscription: dict = None) -> PolicyContext:
    return PolicyContext(
        tool=tool,
        args=args or {},
        account=account or {"is_strategic": False, "is_legal_hold": False, "plan": "pro"},
        requester=requester or {"email": "user@example.com", "is_authorized": True},
        invoice=invoice,
        subscription=subscription,
    )


# ─── 8 Mandatory Verification Scenarios ────────────────────────────────────

def test_refund_30_non_strategic_approval(engine):
    """Refund $30, non-strategic → approval:support_agent (REF-001)"""
    decision = engine.evaluate(ctx(
        tool="billing.issue_refund",
        args={"amount_cents": 3000},
        account={"is_strategic": False, "is_legal_hold": False},
        invoice={"age_days": 5},
    ))
    assert decision.tier == "approval"
    assert decision.rule_id == "REF-001"
    assert decision.approver_role == "support_agent"


def test_refund_300_approval_support_lead(engine):
    """Refund $300 (30000 cents, in REF-002 range $50-$500) → approval:support_lead"""
    decision = engine.evaluate(ctx(
        tool="billing.issue_refund",
        args={"amount_cents": 30000},
        account={"is_strategic": False, "is_legal_hold": False},
    ))
    assert decision.tier == "approval"
    assert decision.rule_id == "REF-002"
    assert decision.approver_role == "support_lead"


def test_refund_300_strategic_approval_support_lead(engine):
    """Refund $300, strategic account → approval:support_lead (REF-002 or GEN-002)"""
    decision = engine.evaluate(ctx(
        tool="billing.issue_refund",
        args={"amount_cents": 30000},
        account={"is_strategic": True, "is_legal_hold": False},
    ))
    # GEN-002 (strategic billing → support_lead) and REF-002 both match
    assert decision.tier == "approval"
    assert decision.approver_role == "support_lead"


def test_refund_50001_forbidden(engine):
    """Refund $50,001 → forbidden (REF-099)"""
    decision = engine.evaluate(ctx(
        tool="billing.issue_refund",
        args={"amount_cents": 50001},
        account={"is_strategic": False, "is_legal_hold": False},
    ))
    assert decision.tier == "forbidden"
    assert decision.rule_id == "REF-099"


def test_grant_viewer_authorized_contact(engine):
    """Grant viewer, authorized contact → approval:security_reviewer (ACC-001)"""
    decision = engine.evaluate(ctx(
        tool="access.grant_access",
        args={"role": "viewer", "expiry_days": 7},
        requester={"email": "user@example.com", "is_authorized": True},
    ))
    assert decision.tier == "approval"
    assert decision.rule_id == "ACC-001"
    assert decision.approver_role == "security_reviewer"


def test_grant_admin_forbidden(engine):
    """Grant admin → forbidden (ACC-099)"""
    decision = engine.evaluate(ctx(
        tool="access.grant_access",
        args={"role": "admin", "expiry_days": 7},
    ))
    assert decision.tier == "forbidden"
    assert decision.rule_id == "ACC-099"


def test_legal_hold_account_forbidden(engine):
    """Any action, legal_hold=true → forbidden (GEN-001)"""
    decision = engine.evaluate(ctx(
        tool="billing.issue_refund",
        args={"amount_cents": 100},
        account={"is_strategic": False, "is_legal_hold": True},
    ))
    assert decision.tier == "forbidden"
    assert decision.rule_id == "GEN-001"


def test_unknown_tool_default_deny(engine):
    """Unknown tool → forbidden (DEFAULT-DENY)"""
    decision = engine.evaluate(ctx(
        tool="admin.delete_account",
        args={},
    ))
    assert decision.tier == "forbidden"
    assert decision.rule_id == "DEFAULT-DENY"


# ─── Additional Scenarios ───────────────────────────────────────────────────

def test_internal_note_auto(engine):
    """Internal note → auto (TKT-001)"""
    decision = engine.evaluate(ctx(tool="ticketing.add_internal_note"))
    assert decision.tier == "auto"
    assert decision.rule_id == "TKT-001"


def test_legal_hold_overrides_auto_tool(engine):
    """Legal hold account: even auto tools → forbidden (GEN-001 priority)"""
    decision = engine.evaluate(ctx(
        tool="ticketing.add_internal_note",
        account={"is_strategic": False, "is_legal_hold": True},
    ))
    assert decision.tier == "forbidden"
    assert decision.rule_id == "GEN-001"


def test_prod_admin_forbidden(engine):
    """Grant prod-admin → forbidden (ACC-099)"""
    decision = engine.evaluate(ctx(
        tool="access.grant_access",
        args={"role": "prod-admin", "expiry_days": 7},
    ))
    assert decision.tier == "forbidden"
    assert decision.rule_id == "ACC-099"


def test_read_only_invoice_auto(engine):
    """Invoice lookup → auto (RD-001)"""
    decision = engine.evaluate(ctx(tool="billing.get_invoice"))
    assert decision.tier == "auto"
    assert decision.rule_id == "RD-001"
