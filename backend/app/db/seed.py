"""
backend/app/db/seed.py
Seeds reference data (accounts, contacts, invoices) and, optionally, synthetic sample tickets and audit history.
"""
import sys
import uuid
from datetime import datetime, UTC, timedelta
from pathlib import Path
import structlog
from sqlalchemy import select, func

from app.audit.store import GENESIS_HASH, chain_fields, compute_row_hash, hash_args
from app.db.session import AsyncSessionLocal
from app.db.models import (
    Account, Contact, Invoice, AccountPlan,
    Ticket, TicketCategory, TicketUrgency, TicketStatus,
    AuditLog, AuditEvent, WorkflowRun, WorkflowStatus,
    Approval, ApprovalStatus, now_utc
)

log = structlog.get_logger()

# Import seed data from services/mocks/seed_data.py
REPO_ROOT = Path(__file__).resolve().parents[3]
MOCKS_DIR = REPO_ROOT / "services" / "mocks"
if str(MOCKS_DIR) not in sys.path:
    sys.path.insert(0, str(MOCKS_DIR))

try:
    from seed_data import ACCOUNTS, CONTACTS, INVOICES
except ImportError:
    ACCOUNTS, CONTACTS, INVOICES = {}, {}, {}


def _map_plan(plan_str: str) -> AccountPlan:
    mapping = {
        "starter": AccountPlan.starter,
        "pro": AccountPlan.pro,
        "enterprise": AccountPlan.enterprise,
        "enterprise_plus": AccountPlan.enterprise_plus,
    }
    return mapping.get(plan_str.lower(), AccountPlan.pro)


async def seed_audit_logs(db) -> int:
    """Insert a synthetic hash-chained audit history (sample data) if the audit table is empty."""
    res = await db.execute(select(func.count(AuditLog.id)))
    count = res.scalar() or 0
    if count > 0:
        return 0

    log.info("db.seed.audit_logs.starting")
    base_time = datetime.now(UTC) - timedelta(hours=14)

    raw_events = [
        {
            "ticket_id": "tick-101",
            "run_id": "run-9801-refund",
            "actor_type": "agent",
            "actor_id": "langgraph_orchestrator",
            "event": AuditEvent.proposed,
            "tool": "billing.issue_refund",
            "policy_rule": "REF-001",
            "result_status": "SUCCESS",
            "args_redacted": {"invoice_id": "INV-2026-881", "amount": 30.0, "reason": "Duplicate subscription charge"},
            "minutes_offset": 0,
        },
        {
            "ticket_id": "tick-101",
            "run_id": "run-9801-refund",
            "actor_type": "gateway",
            "actor_id": "deterministic_policy_gateway",
            "event": AuditEvent.policy_decision,
            "tool": "billing.issue_refund",
            "policy_rule": "REF-001",
            "result_status": "SUCCESS",
            "args_redacted": {"tier": "approval", "reason": "Refund > $20 requires Support Lead review"},
            "minutes_offset": 2,
        },
        {
            "ticket_id": "tick-101",
            "run_id": "run-9801-refund",
            "actor_type": "gateway",
            "actor_id": "langgraph_checkpointer",
            "event": AuditEvent.approval_requested,
            "tool": "billing.issue_refund",
            "policy_rule": "REF-001",
            "result_status": "SUCCESS",
            "args_redacted": {"approval_id": "appr-refund-9801", "approver_role": "support_lead", "expires_in": "24h"},
            "minutes_offset": 3,
        },
        {
            "ticket_id": "tick-102",
            "run_id": "run-9804-injection",
            "actor_type": "gateway",
            "actor_id": "injection_firewall",
            "event": AuditEvent.policy_decision,
            "tool": "billing.issue_refund",
            "policy_rule": "SEC-001",
            "result_status": "BLOCKED",
            "args_redacted": {"threat": "jailbreak_override_attempt", "pattern": "SYSTEM OVERRIDE", "action": "BLOCKED"},
            "minutes_offset": 15,
        },
        {
            "ticket_id": "tick-102",
            "run_id": "run-9804-injection",
            "actor_type": "system",
            "actor_id": "policy_gateway_v1",
            "event": AuditEvent.escalated,
            "tool": "security.threat_intercept",
            "policy_rule": "SEC-001",
            "result_status": "SUCCESS",
            "args_redacted": {"escalation_queue": "secops", "threat_level": "high"},
            "minutes_offset": 16,
        },
        {
            "ticket_id": "tick-103",
            "run_id": "run-9802-tier",
            "actor_type": "agent",
            "actor_id": "langgraph_agent",
            "event": AuditEvent.proposed,
            "tool": "crm.update_account_plan",
            "policy_rule": "SUB-001",
            "result_status": "SUCCESS",
            "args_redacted": {"account_id": "acc-acme", "new_plan": "enterprise"},
            "minutes_offset": 35,
        },
        {
            "ticket_id": "tick-103",
            "run_id": "run-9802-tier",
            "actor_type": "gateway",
            "actor_id": "policy_gateway",
            "event": AuditEvent.policy_decision,
            "tool": "crm.update_account_plan",
            "policy_rule": "SUB-001",
            "result_status": "SUCCESS",
            "args_redacted": {"tier": "auto", "reason": "Upgrade request by authorized primary owner"},
            "minutes_offset": 36,
        },
        {
            "ticket_id": "tick-103",
            "run_id": "run-9802-tier",
            "actor_type": "gateway",
            "actor_id": "mcp_gateway_dispatcher",
            "event": AuditEvent.executed,
            "tool": "crm.update_account_plan",
            "policy_rule": "SUB-001",
            "result_status": "SUCCESS",
            "args_redacted": {"account_id": "acc-acme", "new_plan": "enterprise", "status": "committed"},
            "minutes_offset": 37,
        },
        {
            "ticket_id": "tick-103",
            "run_id": "run-9802-tier",
            "actor_type": "system",
            "actor_id": "readback_verifier",
            "event": AuditEvent.verified,
            "tool": "crm.update_account_plan",
            "policy_rule": "SUB-001",
            "result_status": "SUCCESS",
            "args_redacted": {"verification_state": "COMMITTED", "idempotent_replay": False},
            "minutes_offset": 38,
        },
        {
            "ticket_id": "tick-104",
            "run_id": "run-9805-access",
            "actor_type": "gateway",
            "actor_id": "policy_gateway",
            "event": AuditEvent.policy_decision,
            "tool": "iam.grant_access",
            "policy_rule": "ACC-099",
            "result_status": "BLOCKED",
            "args_redacted": {"requested_role": "prod-admin", "reason": "Admin role escalation prohibited by policy"},
            "minutes_offset": 55,
        },
        {
            "ticket_id": "tick-105",
            "run_id": "run-9806-timeout",
            "actor_type": "gateway",
            "actor_id": "policy_gateway",
            "event": AuditEvent.executed,
            "tool": "billing.issue_refund",
            "policy_rule": "REF-001",
            "result_status": "SUCCESS",
            "args_redacted": {"invoice_id": "INV-2026-904", "amount": 15.0},
            "minutes_offset": 75,
        },
        {
            "ticket_id": "tick-105",
            "run_id": "run-9806-timeout",
            "actor_type": "system",
            "actor_id": "readback_verifier",
            "event": AuditEvent.verified,
            "tool": "billing.issue_refund",
            "policy_rule": "REF-001",
            "result_status": "SUCCESS",
            "args_redacted": {"idempotency_key": "idemp-refund-904", "state": "RECONCILED_COMMITTED"},
            "minutes_offset": 76,
        },
        {
            "ticket_id": "tick-106",
            "run_id": "run-9807-legal",
            "actor_type": "gateway",
            "actor_id": "policy_gateway",
            "event": AuditEvent.policy_decision,
            "tool": "crm.modify_account",
            "policy_rule": "GEN-001",
            "result_status": "BLOCKED",
            "args_redacted": {"legal_hold": True, "reason": "Account under compliance legal hold"},
            "minutes_offset": 90,
        },
        {
            "ticket_id": "tick-107",
            "run_id": "run-9808-mfa",
            "actor_type": "agent",
            "actor_id": "langgraph_orchestrator",
            "event": AuditEvent.proposed,
            "tool": "iam.reset_mfa_token",
            "policy_rule": "SEC-004",
            "result_status": "SUCCESS",
            "args_redacted": {"user_email": "mfa_user@acme.com", "step_up_verified": True},
            "minutes_offset": 110,
        },
        {
            "ticket_id": "tick-107",
            "run_id": "run-9808-mfa",
            "actor_type": "gateway",
            "actor_id": "policy_gateway",
            "event": AuditEvent.policy_decision,
            "tool": "iam.reset_mfa_token",
            "policy_rule": "SEC-004",
            "result_status": "SUCCESS",
            "args_redacted": {"tier": "approval", "reason": "MFA reset requires secondary approval verification"},
            "minutes_offset": 112,
        },
        {
            "ticket_id": "tick-107",
            "run_id": "run-9808-mfa",
            "actor_type": "human",
            "actor_id": "security_analyst_04",
            "event": AuditEvent.approved,
            "tool": "iam.reset_mfa_token",
            "policy_rule": "SEC-004",
            "result_status": "SUCCESS",
            "args_redacted": {"notes": "Identity re-verified via hardware security key", "approver": "security_analyst_04"},
            "minutes_offset": 125,
        },
        {
            "ticket_id": "tick-107",
            "run_id": "run-9808-mfa",
            "actor_type": "gateway",
            "actor_id": "mcp_gateway_dispatcher",
            "event": AuditEvent.executed,
            "tool": "iam.reset_mfa_token",
            "policy_rule": "SEC-004",
            "result_status": "SUCCESS",
            "args_redacted": {"user_email": "mfa_user@acme.com", "temporary_passcode_sent": True},
            "minutes_offset": 126,
        },
        {
            "ticket_id": "tick-108",
            "run_id": "run-9803-faq",
            "actor_type": "agent",
            "actor_id": "langgraph_orchestrator",
            "event": AuditEvent.policy_decision,
            "tool": "ticketing.respond_faq",
            "policy_rule": "FAQ-001",
            "result_status": "SUCCESS",
            "args_redacted": {"rag_citations": ["policy-rag-v3.md"], "confidence": 0.98},
            "minutes_offset": 145,
        },
        {
            "ticket_id": "tick-108",
            "run_id": "run-9803-faq",
            "actor_type": "gateway",
            "actor_id": "mcp_gateway_dispatcher",
            "event": AuditEvent.executed,
            "tool": "ticketing.send_response",
            "policy_rule": "FAQ-001",
            "result_status": "SUCCESS",
            "args_redacted": {"ticket_number": "TICK-108", "delivery_status": "sent"},
            "minutes_offset": 146,
        },
        {
            "ticket_id": "tick-101",
            "run_id": "run-9801-refund",
            "actor_type": "human",
            "actor_id": "support_lead_01",
            "event": AuditEvent.approved,
            "tool": "billing.issue_refund",
            "policy_rule": "REF-001",
            "result_status": "SUCCESS",
            "args_redacted": {"notes": "Approved double billing refund of $30.00 to Acme Corp"},
            "minutes_offset": 180,
        },
    ]

    # Hash-chain the synthetic events with the same scheme the live audit store uses,
    # so verify_chain() validates them like any other rows.
    prev_hash = GENESIS_HASH
    for item in raw_events:
        ts = base_time + timedelta(minutes=item["minutes_offset"])
        row_id = uuid.uuid4().hex
        args_hash = hash_args(item.get("args_redacted"))
        fields = chain_fields(
            id=row_id, timestamp=ts, run_id=item["run_id"], ticket_id=item["ticket_id"],
            actor_type=item["actor_type"], actor_id=item["actor_id"], event=item["event"].value,
            tool=item.get("tool"), args_hash=args_hash, policy_rule=item.get("policy_rule"),
            result_status=item["result_status"],
        )
        row_hash = compute_row_hash(prev_hash, fields)
        db.add(AuditLog(
            id=row_id,
            timestamp=ts,
            run_id=item["run_id"],
            ticket_id=item["ticket_id"],
            actor_type=item["actor_type"],
            actor_id=item["actor_id"],
            event=item["event"],
            tool=item.get("tool"),
            args_hash=args_hash,
            args_redacted=item.get("args_redacted", {}),
            policy_rule=item.get("policy_rule"),
            policy_version=3,
            idempotency_key=f"idem-{item['run_id']}-{item['minutes_offset']}",
            result_status=item["result_status"],
            trace_id=f"sample_{item['run_id']}",
            prev_hash=prev_hash,
            row_hash=row_hash,
        ))
        prev_hash = row_hash

    await db.commit()
    log.info("db.seed.audit_logs.completed", seeded_count=len(raw_events))
    return len(raw_events)


async def seed_category_tickets(db) -> int:
    """Seed tickets across under-represented categories to maintain balanced, realistic analytics."""
    res = await db.execute(select(Ticket.category, func.count(Ticket.id)).group_by(Ticket.category))
    cat_counts = {k: v for k, v in res.all()}

    plan_count = cat_counts.get(TicketCategory.plan_change, 0)
    access_count = cat_counts.get(TicketCategory.access_request, 0)

    # If categories are already populated with multiple items, skip
    if plan_count > 5 and access_count > 5:
        return 0

    log.info("db.seed.category_tickets.starting")
    now = datetime.now(UTC)

    ticket_templates = [
        # Subscription Tiers (plan_change & seat_change)
        {"category": TicketCategory.plan_change, "urgency": TicketUrgency.medium, "status": TicketStatus.resolved, "subject": "Upgrade team to Enterprise tier for SOC 2 compliance", "email": "devops.lead@acme.com"},
        {"category": TicketCategory.plan_change, "urgency": TicketUrgency.low, "status": TicketStatus.resolved, "subject": "Switch from monthly to annual billing on Pro plan", "email": "billing@globex.org"},
        {"category": TicketCategory.plan_change, "urgency": TicketUrgency.high, "status": TicketStatus.resolved, "subject": "Upgrade from Starter to Pro for 5 developers", "email": "sarah@initech.co"},
        {"category": TicketCategory.plan_change, "urgency": TicketUrgency.medium, "status": TicketStatus.resolved, "subject": "Enable Custom Domain add-on for Enterprise tier", "email": "admin@cloudsync.io"},
        {"category": TicketCategory.plan_change, "urgency": TicketUrgency.medium, "status": TicketStatus.awaiting_approval, "subject": "Downgrade staging environment to Starter plan", "email": "ops@acme.com"},
        {"category": TicketCategory.plan_change, "urgency": TicketUrgency.low, "status": TicketStatus.resolved, "subject": "Upgrade data retention plan from 30 days to 1 year", "email": "compliance@dunder.com"},
        {"category": TicketCategory.seat_change, "urgency": TicketUrgency.medium, "status": TicketStatus.resolved, "subject": "Add 10 seats for incoming engineering cohort", "email": "hr@acme.com"},
        {"category": TicketCategory.seat_change, "urgency": TicketUrgency.medium, "status": TicketStatus.resolved, "subject": "Provision 25 developer seats for Acme Corp team", "email": "lead@acme.com"},
        {"category": TicketCategory.seat_change, "urgency": TicketUrgency.low, "status": TicketStatus.resolved, "subject": "Deprovision 3 contractor seats at project end", "email": "pm@globex.org"},
        {"category": TicketCategory.seat_change, "urgency": TicketUrgency.high, "status": TicketStatus.awaiting_approval, "subject": "Add 50 seats for global support organization", "email": "dir_support@acme.com"},
        {"category": TicketCategory.seat_change, "urgency": TicketUrgency.low, "status": TicketStatus.resolved, "subject": "Reallocate 4 inactive seats to data science group", "email": "analytics@initech.co"},
        {"category": TicketCategory.seat_change, "urgency": TicketUrgency.medium, "status": TicketStatus.resolved, "subject": "Increase seat limit on enterprise agreement", "email": "procurement@acme.com"},

        # Access & Auth (access_request & mfa_reset)
        {"category": TicketCategory.access_request, "urgency": TicketUrgency.medium, "status": TicketStatus.resolved, "subject": "Grant read-only viewer role to compliance auditor", "email": "auditor@soc2firm.com"},
        {"category": TicketCategory.access_request, "urgency": TicketUrgency.low, "status": TicketStatus.resolved, "subject": "Add junior engineer to staging environment group", "email": "lead@acme.com"},
        {"category": TicketCategory.access_request, "urgency": TicketUrgency.medium, "status": TicketStatus.resolved, "subject": "Viewer role request for internal finance analyst", "email": "finance@globex.org"},
        {"category": TicketCategory.access_request, "urgency": TicketUrgency.high, "status": TicketStatus.escalated, "subject": "Admin role escalation request for cloud root account", "email": "attacker@fakeacme.com"},
        {"category": TicketCategory.access_request, "urgency": TicketUrgency.low, "status": TicketStatus.resolved, "subject": "Temporary access token for deployment CI/CD pipeline", "email": "devops@initech.co"},
        {"category": TicketCategory.access_request, "urgency": TicketUrgency.medium, "status": TicketStatus.resolved, "subject": "Renew expiring read-only API credentials", "email": "api_user@cloudsync.io"},
        {"category": TicketCategory.mfa_reset, "urgency": TicketUrgency.high, "status": TicketStatus.resolved, "subject": "MFA authenticator app transfer to replacement phone", "email": "jane@acme.com"},
        {"category": TicketCategory.mfa_reset, "urgency": TicketUrgency.high, "status": TicketStatus.resolved, "subject": "Reset lost 2FA hardware key after SSO email match", "email": "sarah.jenkins@acme.com"},
        {"category": TicketCategory.mfa_reset, "urgency": TicketUrgency.medium, "status": TicketStatus.resolved, "subject": "Generate temporary backup codes for remote work", "email": "remote@globex.org"},
        {"category": TicketCategory.mfa_reset, "urgency": TicketUrgency.critical, "status": TicketStatus.escalated, "subject": "Suspicious MFA reset attempt without SSO session", "email": "unknown@external.net"},

        # General FAQ & Other
        {"category": TicketCategory.other, "urgency": TicketUrgency.low, "status": TicketStatus.resolved, "subject": "API rate limit documentation and burst quota question", "email": "developer@partner.com"},
        {"category": TicketCategory.other, "urgency": TicketUrgency.low, "status": TicketStatus.resolved, "subject": "Webhook signature verification Python snippet inquiry", "email": "tech@client.io"},
        {"category": TicketCategory.other, "urgency": TicketUrgency.low, "status": TicketStatus.resolved, "subject": "Supported SSO identity providers and SAML 2.0 specs", "email": "it@enterprise.com"},
        {"category": TicketCategory.other, "urgency": TicketUrgency.low, "status": TicketStatus.resolved, "subject": "Data retention and GDPR deletion timeline policy", "email": "privacy@corp.de"},
        {"category": TicketCategory.other, "urgency": TicketUrgency.medium, "status": TicketStatus.resolved, "subject": "Inquiry about custom domain SSL certificate renewal", "email": "webmaster@acme.com"},
        {"category": TicketCategory.other, "urgency": TicketUrgency.low, "status": TicketStatus.resolved, "subject": "Does ResolveOps support SCIM directory synchronization?", "email": "security@initech.co"},
        {"category": TicketCategory.other, "urgency": TicketUrgency.low, "status": TicketStatus.resolved, "subject": "How to export SOC 2 compliance verification certificate", "email": "compliance@acme.com"},

        # Billing additions
        {"category": TicketCategory.invoice_question, "urgency": TicketUrgency.medium, "status": TicketStatus.resolved, "subject": "Tax ID and VAT number update on invoice INV-2026-882", "email": "accounting@acme.com"},
        {"category": TicketCategory.invoice_question, "urgency": TicketUrgency.low, "status": TicketStatus.resolved, "subject": "Itemized breakdown for monthly compute & API calls", "email": "finance@initech.co"},
        {"category": TicketCategory.credit, "urgency": TicketUrgency.medium, "status": TicketStatus.resolved, "subject": "Service level agreement downtime credit request ($50)", "email": "sarah.jenkins@acme.com"},
        {"category": TicketCategory.credit, "urgency": TicketUrgency.low, "status": TicketStatus.awaiting_approval, "subject": "Promotional startup accelerator credit application", "email": "founder@startuphub.co"},
    ]

    for i, tpl in enumerate(ticket_templates):
        t_id = uuid.uuid4().hex
        created = now - timedelta(days=min(i // 4, 6), hours=(i % 12) + 1)
        t = Ticket(
            id=t_id,
            account_id="acc-acme" if "acme.com" in tpl["email"] else "acc-globex",
            requester_email=tpl["email"],
            subject=tpl["subject"],
            body_html=f"<p>{tpl['subject']}. Verified requester identity with SSO.</p>",
            category=tpl["category"],
            urgency=tpl["urgency"],
            status=tpl["status"],
            created_at=created,
            updated_at=created,
        )
        db.add(t)

    await db.commit()
    log.info("db.seed.category_tickets.completed", added=len(ticket_templates))
    return len(ticket_templates)


async def seed_workflow_runs_and_approvals(db) -> int:
    """Insert synthetic workflow runs and approvals if approvals table is empty."""
    res = await db.execute(select(func.count(Approval.id)))
    count = res.scalar() or 0
    if count > 0:
        return 0

    log.info("db.seed.workflow_runs_and_approvals.starting")

    # Fetch existing tickets
    t_res = await db.execute(select(Ticket))
    tickets = t_res.scalars().all()
    if not tickets:
        return 0

    import hashlib
    import json

    def _hash(tool: str, args: dict) -> str:
        normalized = json.dumps(args, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(f"{tool}:{normalized}".encode()).hexdigest()

    pending_tickets = [t for t in tickets if t.status == TicketStatus.awaiting_approval]
    resolved_tickets = [t for t in tickets if t.status == TicketStatus.resolved]

    # Create pending approvals for tickets in awaiting_approval
    for t in pending_tickets:
        run_id = f"run-{t.id[:12]}"
        run = WorkflowRun(
            id=run_id,
            ticket_id=t.id,
            status=WorkflowStatus.awaiting_approval,
            started_at=t.created_at,
            nodes_timeline=[
                {"node": "classify_intent", "duration_ms": 280, "status": "completed"},
                {"node": "retrieve_context", "duration_ms": 210, "status": "completed"},
                {"node": "plan_action", "duration_ms": 640, "status": "completed"},
                {"node": "policy_gateway", "duration_ms": 30, "status": "waiting_approval"},
            ],
            state_json={
                "total_llm_cost_usd": 0.0042,
                "policy_decisions": [{"tier": "approval", "reason": "Requires human review"}],
            },
        )
        db.add(run)

        sub_lower = t.subject.lower()
        if "seat" in sub_lower:
            tool = "billing.update_seats"
            rule = "SEAT-001"
            args = {"seats": 50, "account_id": t.account_id}
        elif "plan" in sub_lower or "tier" in sub_lower or "starter" in sub_lower:
            tool = "subscription.update_plan"
            rule = "SUB-002"
            args = {"plan": "starter", "immediate": False}
        else:
            tool = "billing.issue_credit"
            rule = "CRD-001"
            args = {"amount": 50.0, "reason": "Promotional startup credit"}

        appr = Approval(
            id=f"appr-{t.id[:12]}",
            run_id=run_id,
            ticket_id=t.id,
            tool=tool,
            args_hash=_hash(tool, args),
            args_redacted=args,
            args_normalized=args,
            policy_rule=rule,
            approver_role="support_lead",
            status=ApprovalStatus.pending,
            created_at=t.created_at,
            expires_at=t.created_at + timedelta(hours=24),
        )
        db.add(appr)

    # For resolved tickets, create workflow runs and historical approvals
    for i, t in enumerate(resolved_tickets[:16]):
        run_id = f"run-res-{t.id[:10]}"
        lat_ms = 480 + (i * 35) % 380
        cost = round(0.0028 + (i * 0.0003) % 0.0045, 6)
        run = WorkflowRun(
            id=run_id,
            ticket_id=t.id,
            status=WorkflowStatus.done,
            started_at=t.created_at,
            completed_at=t.created_at + timedelta(seconds=12),
            nodes_timeline=[
                {"node": "classify_intent", "duration_ms": 220, "status": "completed"},
                {"node": "retrieve_context", "duration_ms": 180, "status": "completed"},
                {"node": "plan_action", "duration_ms": lat_ms, "status": "completed"},
                {"node": "policy_gateway", "duration_ms": 20, "status": "completed"},
                {"node": "execute_tools", "duration_ms": 310, "status": "completed"},
            ],
            state_json={
                "total_llm_cost_usd": cost,
                "policy_decisions": [{"tier": "auto", "rule": "AUT-001"}],
            },
        )
        db.add(run)

        # 11 approved, 2 rejected, 1 escalated historical approvals
        if i < 14:
            tool = "billing.issue_refund" if i % 2 == 0 else "access.grant_role"
            rule = "REF-001" if i % 2 == 0 else "ACC-002"
            args = {"amount": 25.0} if i % 2 == 0 else {"role": "viewer"}
            status = ApprovalStatus.approved if i < 11 else (
                ApprovalStatus.rejected if i < 13 else ApprovalStatus.escalated
            )
            appr = Approval(
                id=f"appr-hist-{i}",
                run_id=run_id,
                ticket_id=t.id,
                tool=tool,
                args_hash=_hash(tool, args),
                args_redacted=args,
                args_normalized=args,
                policy_rule=rule,
                approver_role="support_lead",
                status=status,
                created_at=t.created_at,
                expires_at=t.created_at + timedelta(hours=24),
                reviewed_at=t.created_at + timedelta(minutes=10),
                reviewer_id="lead_reviewer_01",
                edit_reason="Approved per SLA" if status == ApprovalStatus.approved else "Policy threshold exceeded",
            )
            db.add(appr)

    await db.commit()
    log.info("db.seed.workflow_runs_and_approvals.completed")
    return len(pending_tickets) + 14


async def seed_initial_data(include_demo_history: bool = False) -> None:
    """
    Seed reference data (accounts, contacts, invoices) from services/mocks/seed_data.py.

    With ``include_demo_history`` it also inserts synthetic sample tickets and a
    synthetic hash-chained audit history so the UI has something to show on first run.
    """
    async with AsyncSessionLocal() as db:
        # 1. Accounts, Contacts, Invoices
        res = await db.execute(select(Account).limit(1))
        if not res.scalar_one_or_none():
            log.info("db.seed.starting_accounts", accounts_count=len(ACCOUNTS))
            for acc_id, acc_data in ACCOUNTS.items():
                acc = Account(
                    id=acc_id,
                    name=acc_data.get("name", "Account"),
                    plan=_map_plan(acc_data.get("plan", "pro")),
                    arr_cents=acc_data.get("arr_cents", 1200000),
                    is_strategic=acc_data.get("is_strategic", False),
                    is_legal_hold=acc_data.get("is_legal_hold", False),
                    csm_owner=acc_data.get("csm_owner", "csm@northwindcloud.com"),
                    status=acc_data.get("status", "active"),
                    created_at=now_utc(),
                )
                db.add(acc)

            for email, con_data in CONTACTS.items():
                acc_id = con_data.get("account_id")
                if acc_id and acc_id in ACCOUNTS:
                    contact = Contact(
                        id=con_data.get("id"),
                        account_id=acc_id,
                        email=email,
                        name=con_data.get("name", "Contact"),
                        is_authorized=con_data.get("is_authorized", True),
                        role=con_data.get("role", "member"),
                        created_at=now_utc(),
                    )
                    db.add(contact)

            for inv_id, inv_data in INVOICES.items():
                acc_id = inv_data.get("account_id")
                if acc_id and acc_id in ACCOUNTS:
                    inv = Invoice(
                        id=inv_id,
                        account_id=acc_id,
                        amount_cents=inv_data.get("amount_cents", 3000),
                        status=inv_data.get("status", "paid"),
                        invoice_date=now_utc(),
                        created_at=now_utc(),
                    )
                    db.add(inv)

            await db.commit()

        if include_demo_history:
            # 2. Synthetic hash-chained audit history (sample data)
            await seed_audit_logs(db)

            # 3. Synthetic sample tickets across categories (sample data)
            await seed_category_tickets(db)

            # 4. Synthetic workflow runs and approvals (sample data)
            await seed_workflow_runs_and_approvals(db)

        log.info("db.seed.all_completed")


if __name__ == "__main__":
    import asyncio
    asyncio.run(seed_initial_data())
