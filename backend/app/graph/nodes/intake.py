"""
intake node — validate ticket, fetch from ticketing system, initialize run state.
"""
import uuid

import httpx
import structlog

from app.graph.state import TicketState
from app.config import settings

log = structlog.get_logger()


async def intake_node(state: TicketState) -> dict:
    """
    Step 1: Validate ticket_id exists and is actionable.
    Fetch raw ticket from ticketing mock.
    Initialize run state.
    """
    ticket_id = state.get("ticket_id")
    run_id = state.get("run_id") or str(uuid.uuid4())[:8]

    log.info("node.intake.start", ticket_id=ticket_id, run_id=run_id)

    # Check if raw_ticket is already provided in state
    raw_ticket = state.get("raw_ticket") or {}

    if not raw_ticket:
        # Fetch raw ticket from ticketing mock or MCP registry
        ticketing_url = getattr(settings, "mock_ticketing_url", "http://localhost:8001")
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{ticketing_url}/tickets/{ticket_id}")
                if resp.status_code == 200:
                    raw_ticket = resp.json()
                elif resp.status_code == 404:
                    raw_ticket = {}
        except Exception:
            pass

        if not raw_ticket:
            try:
                from services import mcp_registry
                res = await mcp_registry.dispatch_tool("ticketing.get_ticket", {"ticket_id": ticket_id})
                if res and res.get("found") is not False and "error" not in res:
                    raw_ticket = res
            except Exception:
                pass

    if not raw_ticket:
        log.error("node.intake.ticket_not_found", ticket_id=ticket_id)
        return {
            "run_id": run_id,
            "status": "failed",
            "error": f"Ticket {ticket_id} not found",
            "flags": ["ticket_not_found"],
            "total_llm_cost_usd": 0.0,
            "total_tool_calls": 0,
            "total_llm_calls": 0,
            "replans": 0,
        }

    # Validate ticket is actionable
    status = raw_ticket.get("status", "open")
    if status in ("closed", "resolved", "spam"):
        return {
            "run_id": run_id,
            "raw_ticket": raw_ticket,
            "status": "failed",
            "error": f"Ticket is already {status} — no action needed",
            "flags": ["ticket_not_actionable"],
            "total_llm_cost_usd": 0.0,
            "total_tool_calls": 1,
            "total_llm_calls": 0,
            "replans": 0,
        }

    log.info(
        "node.intake.done",
        ticket_id=ticket_id,
        run_id=run_id,
        requester=raw_ticket.get("requester_email"),
        status=status,
    )

    return {
        "run_id": run_id,
        "raw_ticket": raw_ticket,
        "status": "running",
        "flags": list(state.get("flags", [])),  # keep risk flags stored on the ticket
        "policy_decisions": [],
        "executed": [],
        "attempts": {},
        "total_llm_cost_usd": 0.0,
        "total_tool_calls": 1,
        "total_llm_calls": 0,
        "replans": 0,
        "approval_id": None,
        "approval": None,
        "error": None,
        "escalation_reason": None,
    }
