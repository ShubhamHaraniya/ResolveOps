"""
policy_check node — runs policy engine against EVERY proposed action.
Deterministic. No LLM. Returns most restrictive decision.
Legal hold (GEN-001) always wins.
"""
import structlog

from app.graph.state import TicketState
from app.policy.engine import get_policy_engine, PolicyContext

log = structlog.get_logger()


async def policy_check_node(state: TicketState) -> dict:
    """
    Evaluate each proposed action against rules.yaml.
    Returns the most restrictive decision across all actions.
    """
    proposal = state.get("proposal", {})
    actions = proposal.get("actions", [])
    context = state.get("context", {})
    ticket_id = state.get("ticket_id")

    if not actions:
        log.info("node.policy_check.no_actions", ticket_id=ticket_id)
        return {
            "policy_decisions": [{
                "tier": "auto",
                "rule_id": "NO-ACTION",
                "reason": "No actions proposed",
                "approver_role": None,
                "escalate_to": None,
                "policy_version": 3,
            }],
        }

    engine = get_policy_engine()
    account = context.get("account", {})
    requester = context.get("requester", {})

    # Build invoice context if refund is in args
    invoices = context.get("invoices", [])

    decisions = []
    log.info("node.policy_check.start", ticket_id=ticket_id, action_count=len(actions))

    for action in actions:
        tool = action.get("tool", "")
        args = action.get("args", action.get("arguments", {}))

        # Enrich invoice context if applicable
        invoice_ctx = None
        if "invoice_id" in args:
            inv_id = args["invoice_id"]
            matching = [i for i in invoices if i.get("id") == inv_id]
            if matching:
                inv = matching[0]
                from datetime import datetime, UTC
                from dateutil.parser import parse as parse_date
                try:
                    inv_date = parse_date(inv.get("invoice_date", ""))
                    age_days = (datetime.now(UTC) - inv_date).days
                except Exception:
                    age_days = 0
                invoice_ctx = {**inv, "age_days": age_days}

        policy_ctx = PolicyContext(
            tool=tool,
            args=args,
            account=account,
            requester={"is_authorized": requester.get("verified", False), **requester},
            invoice=invoice_ctx,
        )

        decision = engine.evaluate(policy_ctx)
        decisions.append({
            "tool": tool,
            "tier": decision.tier,
            "rule_id": decision.rule_id,
            "reason": decision.reason,
            "approver_role": decision.approver_role,
            "escalate_to": decision.escalate_to,
            "policy_version": decision.policy_version,
        })

        log.info(
            "node.policy_check.decision",
            ticket_id=ticket_id,
            tool=tool,
            tier=decision.tier,
            rule_id=decision.rule_id,
        )

    # Most restrictive wins: forbidden > approval > auto
    TIER_ORDER = {"forbidden": 0, "approval": 1, "auto": 2}
    decisions.sort(key=lambda d: TIER_ORDER.get(d["tier"], 99))

    log.info(
        "node.policy_check.done",
        ticket_id=ticket_id,
        most_restrictive=decisions[0]["tier"] if decisions else "none",
    )

    flags = list(state.get("flags", []))
    if decisions and decisions[0]["tier"] == "forbidden":
        flags.append("forbidden_action_proposed")
        if decisions[0].get("escalate_to") == "legal":
            flags.append("legal_hold_escalation")

    return {
        "policy_decisions": decisions,
        "flags": flags,
    }
