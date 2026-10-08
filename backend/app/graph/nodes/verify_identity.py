"""
verify_identity node — deterministic identity verification.
Never uses LLM. Checks requester email against CRM authorized contacts.
"""
import structlog
import httpx

from app.graph.state import TicketState
from app.llm.schemas import IdentityResult

log = structlog.get_logger()


async def verify_identity_node(state: TicketState) -> dict:
    """
    Deterministic identity verification:
    1. Extract requester_email from ticket
    2. Look up requester in CRM
    3. Confirm they are an authorized contact for the ticket's account
    4. Record result in state

    Does NOT use LLM. Failure → escalation, not LLM reasoning.
    """
    ticket = state.get("raw_ticket", {})
    ticket_id = state.get("ticket_id")
    run_id = state.get("run_id")

    requester_email = ticket.get("requester_email", "")
    account_id = ticket.get("account_id", "")

    log.info("node.verify_identity.start", ticket_id=ticket_id, requester=requester_email)

    from app.config import settings
    crm_url = getattr(settings, "mock_crm_url", "http://localhost:8002")

    identity: IdentityResult

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Look up contact by email
            contact_resp = await client.get(f"{crm_url}/contacts", params={"email": requester_email})

            if contact_resp.status_code == 404:
                # Requester not in CRM at all
                identity = IdentityResult(
                    verified=False,
                    method="crm_lookup",
                    confidence=1.0,
                    reason=f"Requester '{requester_email}' not found in CRM",
                    authorized_contact_match=False,
                    requester_email=requester_email,
                    account_id=None,
                )
            elif contact_resp.status_code == 200:
                contact = contact_resp.json()
                contact_account_id = contact.get("account_id")

                if not contact.get("is_authorized", False):
                    identity = IdentityResult(
                        verified=False,
                        method="crm_lookup",
                        confidence=1.0,
                        reason=f"'{requester_email}' is not an authorized contact",
                        authorized_contact_match=False,
                        requester_email=requester_email,
                        account_id=contact_account_id,
                    )
                elif contact_account_id != account_id:
                    # Contact exists but is linked to a DIFFERENT account
                    identity = IdentityResult(
                        verified=False,
                        method="crm_lookup",
                        confidence=1.0,
                        reason=f"'{requester_email}' is authorized for account '{contact_account_id}', "
                               f"not '{account_id}' — possible cross-account attack",
                        authorized_contact_match=False,
                        requester_email=requester_email,
                        account_id=contact_account_id,
                    )
                else:
                    # Verified
                    identity = IdentityResult(
                        verified=True,
                        method="crm_authorized_contact",
                        confidence=1.0,
                        reason=f"'{requester_email}' is an authorized contact for account '{account_id}'",
                        authorized_contact_match=True,
                        requester_email=requester_email,
                        account_id=account_id,
                    )
            else:
                # CRM error — fail safe
                identity = IdentityResult(
                    verified=False,
                    method="crm_error",
                    confidence=0.0,
                    reason=f"CRM returned status {contact_resp.status_code} — defaulting to unverified",
                    authorized_contact_match=False,
                    requester_email=requester_email,
                    account_id=None,
                )

    except (httpx.ConnectError, httpx.TimeoutException) as e:
        log.warning("node.verify_identity.crm_unavailable", error=str(e))
        # Fail safe: if CRM is down, treat as unverified
        identity = IdentityResult(
            verified=False,
            method="crm_unavailable",
            confidence=0.0,
            reason=f"CRM unavailable: {str(e)[:100]}. Defaulting to unverified.",
            authorized_contact_match=False,
            requester_email=requester_email,
            account_id=None,
        )

    flags = list(state.get("flags", []))
    if not identity.verified:
        flags.append("identity_mismatch")
        log.warning(
            "node.verify_identity.FAILED",
            ticket_id=ticket_id,
            requester=requester_email,
            reason=identity.reason,
        )
    else:
        log.info(
            "node.verify_identity.verified",
            ticket_id=ticket_id,
            requester=requester_email,
            method=identity.method,
        )

    return {
        "identity": identity.model_dump(),
        "flags": flags,
        "total_tool_calls": state.get("total_tool_calls", 0) + 1,
    }
