"""
policy_check node — runs policy engine against EVERY proposed action.
Deterministic. No LLM. Returns most restrictive decision.
Legal hold (GEN-001) always wins.
"""
from datetime import UTC, datetime

import structlog
from dateutil.parser import parse as parse_date

from app.graph.state import TicketState
from app.policy.engine import PolicyContext, get_policy_engine, most_restrictive

log = structlog.get_logger()


async def policy_check_node(state: TicketState) -> dict:
    """
    Evaluate each proposed action against rules.yaml.
    Returns one decision per proposed action, in the same order as the actions
    (execute and approval_interrupt rely on that alignment).
    """
    proposal = state.get("proposal", {})
    actions = proposal.get("actions", [])
    context = state.get("context", {})
    ticket_id = state.get("ticket_id")

    flags = list(state.get("flags", []))
    if "injection_suspected" in flags or "prompt_injection_suspected" in flags:
        log.warning("node.policy_check.injection_override", ticket_id=ticket_id)
        decision = {
            "tool": "*",
            "tier": "forbidden",
            "rule_id": "SEC-001",
            "reason": "Adversarial injection detected: all automated execution forbidden, escalate to Security",
            "approver_role": None,
            "escalate_to": "security",
            "policy_version": 3,
        }
        return {
            "policy_decisions": [decision],
            "flags": list(set(flags + ["forbidden_action_proposed", "injection_suspected"])),
        }

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
        if tool.startswith("billing.") or "invoice_id" in args:
            inv_id = args.get("invoice_id")
            matching = [i for i in invoices if i.get("id") == inv_id]
            if matching:
                inv = matching[0]
            elif invoices:
                inv = invoices[0]
            else:
                inv = {"id": inv_id or "INV-001", "invoice_date": datetime.now(UTC).isoformat(), "amount_cents": args.get("amount_cents", 3000)}

            try:
                inv_date = parse_date(inv.get("invoice_date", ""))
                if inv_date.tzinfo is None:
                    inv_date = inv_date.replace(tzinfo=UTC)
                age_days = (datetime.now(UTC) - inv_date).days
            except Exception:
                # Unparseable date: assume old so age-limited auto rules do not apply.
                age_days = 10_000
            invoice_ctx = {**inv, "age_days": age_days}

        policy_ctx = PolicyContext(
            tool=tool,
            args=args,
            account=account,
            requester={"is_authorized": requester.get("verified", False), **requester},
            invoice=invoice_ctx,
            flags=list(state.get("flags", [])),
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

    # Most restrictive wins (forbidden > approval > auto) for routing; do not reorder the list.
    strictest = most_restrictive(decisions)

    log.info(
        "node.policy_check.done",
        ticket_id=ticket_id,
        most_restrictive=strictest["tier"] if strictest else "none",
    )

    flags = list(state.get("flags", []))
    for d in decisions:
        if d["tier"] == "forbidden":
            flags.append("forbidden_action_proposed")
            if d.get("escalate_to") == "legal":
                flags.append("legal_hold_escalation")
    flags = list(dict.fromkeys(flags))

    return {
        "policy_decisions": decisions,
        "flags": flags,
    }
