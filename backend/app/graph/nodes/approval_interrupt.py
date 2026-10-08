"""
approval_interrupt node — create approval record and pause workflow.
The workflow resumes when the human reviewer POSTs to /api/approvals/{id}/approve.
"""
import hashlib
import json
import time
import uuid
from datetime import datetime, UTC, timedelta
import structlog

from app.graph.state import TicketState

log = structlog.get_logger()


def _make_args_hash(tool: str, args: dict) -> str:
    normalized = json.dumps(args, sort_keys=True, separators=(",", ":"))
    content = f"{tool}:{normalized}"
    return hashlib.sha256(content.encode()).hexdigest()


def _redact_args(args: dict) -> dict:
    PII_KEYS = {"email", "user_email", "phone", "body", "note"}
    return {
        k: f"[REDACTED:{k}]" if k in PII_KEYS else v
        for k, v in args.items()
    }


async def approval_interrupt_node(state: TicketState) -> dict:
    """
    Create approval record and interrupt workflow.
    Workflow will resume when reviewer approves/rejects.
    
    Approval record stored in DB (stub: returned in state for M2).
    The LangGraph interrupt mechanism suspends execution here.
    """
    ticket_id = state.get("ticket_id")
    run_id = state.get("run_id")
    proposal = state.get("proposal", {})
    decisions = state.get("policy_decisions", [])

    # Find the first approval-required action
    actions = proposal.get("actions", [])
    if not actions:
        return {"status": "failed", "error": "No actions to approve"}

    # Find approval-required actions from policy decisions
    approval_actions = [
        (a, d) for a, d in zip(actions, decisions[:len(actions)])
        if d.get("tier") == "approval"
    ]

    if not approval_actions:
        # All actions are auto — shouldn't be here, but handle gracefully
        return {"status": "running"}

    # Create approval records for each required action
    approval_records = []
    for action, decision in approval_actions:
        tool = action.get("tool", "")
        args = action.get("args", action.get("arguments", {}))
        args_hash = _make_args_hash(tool, args)

        approval_id = str(uuid.uuid4())[:12]
        expires_at = (datetime.now(UTC) + timedelta(hours=24)).timestamp()

        record = {
            "id": approval_id,
            "ticket_id": ticket_id,
            "run_id": run_id,
            "tool": tool,
            "args_hash": args_hash,
            "args_redacted": _redact_args(args),
            "args_full": args,  # Full args stored securely in DB (never sent to frontend)
            "policy_rule": decision.get("rule_id"),
            "approver_role": decision.get("approver_role"),
            "status": "pending",
            "created_at": datetime.now(UTC).isoformat(),
            "expires_at": expires_at,
            "expires_at_human": (datetime.now(UTC) + timedelta(hours=24)).isoformat(),
            "reviewed_at": None,
            "reviewer_id": None,
            "edit_reason": None,
            "draft_reply": proposal.get("draft_reply", ""),
            "reasoning": decision.get("reason", ""),
        }
        approval_records.append(record)

    # Primary approval (first one)
    primary = approval_records[0]

    log.info(
        "node.approval_interrupt.created",
        ticket_id=ticket_id,
        run_id=run_id,
        approval_id=primary["id"],
        tool=primary["tool"],
        approver_role=primary["approver_role"],
        expires_at=primary["expires_at_human"],
    )

    return {
        "approval_id": primary["id"],
        "approval": primary,
        "status": "awaiting_approval",
    }
