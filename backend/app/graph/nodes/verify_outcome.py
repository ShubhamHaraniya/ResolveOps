"""
verify_outcome node — read-back verification after execution.
Handles timeout-after-commit: query billing by idempotency key to find result.
"""
import structlog

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

    verified_executed = []
    for action in executed:
        if action.get("outcome") == "unknown_timeout":
            # Read-back: check billing by idempotency key
            idem_key = action.get("args", {}).get("idempotency_key")
            if idem_key:
                try:
                    from app.reliability.readback import ReadBackVerifier, ReadBackState
                    reconcile_res = await ReadBackVerifier.reconcile_timeout(
                        tool=action["tool"],
                        args=action.get("args", {}),
                        idempotency_key=idem_key,
                    )
                    if reconcile_res.get("state") == ReadBackState.COMMITTED:
                        log.info(
                            "verify_outcome.readback_found",
                            ticket_id=ticket_id,
                            tool=action["tool"],
                            refund=reconcile_res.get("result"),
                        )
                        action = {**action, "result": reconcile_res.get("result"), "outcome": "confirmed_via_readback"}
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

    if not executed:
        return {}

    # Check if a financial refund was actually executed
    refund_executed = any(e.get("tool") == "billing.issue_refund" and not e.get("error") for e in executed)

    # Use draft from proposal as base
    draft = proposal.get("draft_reply", "")

    # False claim check: ONLY replace if the draft falsely claims a refund was already issued/processed
    falsely_claims_processed = (
        not refund_executed and draft and
        ("has been processed" in draft.lower() or "issued a refund" in draft.lower() or "refund has been sent" in draft.lower())
    )

    if falsely_claims_processed:
        if proposal.get("clarification_needed") and proposal.get("clarification_question"):
            draft = (
                f"Thank you for contacting Northwind Support. {proposal.get('clarification_question')} "
                "Please provide this information so our billing team can assist you."
            )
        else:
            draft = (
                "Thank you for reaching out to Northwind Support. We have reviewed your request, and our support team "
                "is currently investigating your account. Please let us know if you have any additional invoice details to share."
            )
    elif not draft:
        if refund_executed:
            draft = "Your refund request has been processed. Please allow 5-7 business days for the funds to appear on your original payment method."
        else:
            draft = "We have received and reviewed your request. Our support team is looking into this and will follow up shortly."

    # Strip any accidental internal tool names or code symbols from the public customer response
    for tool_name in ["ticketing.add_internal_note", "ticketing.send_public_reply", "ticketing.patch_ticket", "billing.issue_refund", "access.grant_access"]:
        draft = draft.replace(tool_name, "internal review")

    log.info("node.draft_reply.done", ticket_id=ticket_id, refund_executed=refund_executed)
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
