"""
verify_outcome node — read-back verification after execution.
Handles timeout-after-commit: query billing by idempotency key to find result.
"""
import structlog
import httpx
import os

from app.graph.state import TicketState

log = structlog.get_logger()


async def verify_outcome_node(state: TicketState) -> dict:
    """
    Verify execution outcomes.
    For timeout-after-commit: query billing by idempotency key.
    """
    ticket_id = state.get("ticket_id")
    executed = state.get("executed", [])
    flags = list(state.get("flags", []))

    billing_url = os.environ.get("MOCK_BILLING_URL", "http://localhost:8003")

    verified_executed = []
    for action in executed:
        if action.get("outcome") == "unknown_timeout":
            # Read-back: check billing by idempotency key
            idem_key = action.get("args", {}).get("idempotency_key")
            if idem_key:
                try:
                    async with httpx.AsyncClient(timeout=10.0) as client:
                        r = await client.get(
                            f"{billing_url}/refunds",
                            params={"idempotency_key": idem_key}
                        )
                        if r.status_code == 200:
                            data = r.json()
                            if data.get("found"):
                                log.info(
                                    "verify_outcome.readback_found",
                                    ticket_id=ticket_id,
                                    tool=action["tool"],
                                    refund_id=data["refund"].get("refund_id"),
                                )
                                action = {**action, "result": data["refund"], "outcome": "confirmed_via_readback"}
                                if "timeout_after_commit" in flags:
                                    flags.remove("timeout_after_commit")
                            else:
                                log.info("verify_outcome.readback_not_found", ticket_id=ticket_id)
                                action = {**action, "outcome": "not_found_after_timeout"}
                except Exception as e:
                    log.warning("verify_outcome.readback_failed", error=str(e))

        verified_executed.append(action)

    return {
        "executed": verified_executed,
        "flags": flags,
    }


async def draft_reply_node(state: TicketState) -> dict:
    """Draft final customer reply based on what was actually executed."""
    ticket_id = state.get("ticket_id")
    executed = state.get("executed", [])
    proposal = state.get("proposal", {})
    ticket = state.get("raw_ticket", {})

    if not executed:
        return {}

    # Use draft from proposal as base, or generate simple summary
    draft = proposal.get("draft_reply", "")
    if not draft:
        actions_summary = ", ".join(e["tool"] for e in executed if "error" not in e)
        draft = f"We have processed your request. Actions taken: {actions_summary}. Thank you for contacting support."

    log.info("node.draft_reply.done", ticket_id=ticket_id)
    return {"proposal": {**(proposal or {}), "draft_reply": draft}}


async def close_node(state: TicketState) -> dict:
    """Close the workflow run — set final status."""
    ticket_id = state.get("ticket_id")
    flags = state.get("flags", [])
    executed = state.get("executed", [])
    error = state.get("error")

    if "forbidden_action_proposed" in flags or "identity_mismatch" in flags:
        final_status = "escalated"
    elif error:
        final_status = "failed"
    elif executed:
        final_status = "done"
    else:
        final_status = "done"

    log.info("node.close", ticket_id=ticket_id, status=final_status, flags=flags)
    return {"status": final_status}
