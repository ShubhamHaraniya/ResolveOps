"""
intake node — validate ticket, fetch from ticketing system, initialize run state.
"""
import uuid
from datetime import datetime, UTC

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

    # Fetch raw ticket from ticketing mock
    ticketing_url = getattr(settings, "mock_ticketing_url", "http://localhost:8001")
    raw_ticket = {}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{ticketing_url}/tickets/{ticket_id}")
            if resp.status_code == 200:
                raw_ticket = resp.json()
            elif resp.status_code == 404:
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
    except (httpx.ConnectError, httpx.TimeoutException) as e:
        log.warning("node.intake.ticketing_unavailable", error=str(e))
        # Use ticket_id to create minimal stub
        raw_ticket = {"id": ticket_id, "status": "open", "requester_email": "unknown"}

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
        "flags": [],
        "policy_decisions": [],
        "executed": [],
        "compensations": [],
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
