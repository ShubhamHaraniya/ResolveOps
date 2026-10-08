"""
classify node — call Groq to classify ticket category, urgency, sentiment.
Uses fast model (gpt-oss-20b). Returns Classification schema.
Injection scan runs first — informs classification but doesn't block here.
"""
import structlog

from app.graph.state import TicketState
from app.llm.groq_client import get_groq_client
from app.llm.schemas import Classification
from app.llm.prompts import CLASSIFICATION_SYSTEM, CLASSIFICATION_USER

log = structlog.get_logger()

# Import injection scanner lazily (services/ dir)
def _scan_for_injection(subject: str, body: str) -> dict:
    try:
        import sys, os
        mocks_parent = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "services", "gateway")
        if mocks_parent not in sys.path:
            sys.path.insert(0, mocks_parent)
        from injection import scan_all_context
        result = scan_all_context(ticket_subject=subject, ticket_body=body)
        return {
            "suspected": result.suspected,
            "confidence": result.confidence,
            "patterns": result.patterns_matched,
        }
    except Exception as e:
        log.warning("classify.injection_scan_failed", error=str(e))
        return {"suspected": False, "confidence": 0.0, "patterns": []}


async def classify_node(state: TicketState) -> dict:
    """
    Call Groq fast model to classify ticket.
    Also runs deterministic injection scan.
    """
    ticket = state.get("raw_ticket", {})
    ticket_id = state.get("ticket_id")
    run_id = state.get("run_id")

    subject = ticket.get("subject", "")
    body = ticket.get("body_html") or ticket.get("body", "")
    # Strip basic HTML tags for LLM
    import re
    body_text = re.sub(r"<[^>]+>", " ", body).strip()

    log.info("node.classify.start", ticket_id=ticket_id, run_id=run_id)

    # Run injection scan (deterministic — always before LLM)
    injection = _scan_for_injection(subject=subject, body=body_text)
    flags = list(state.get("flags", []))
    if injection["suspected"]:
        flags.append("injection_suspected")
        log.warning(
            "node.classify.injection_suspected",
            ticket_id=ticket_id,
            confidence=injection["confidence"],
            patterns=injection["patterns"],
        )

    # Call Groq for classification
    from app.config import settings
    groq = get_groq_client()
    
    try:
        call_result = await groq.complete_structured(
            model=settings.groq_model_fast,
            messages=[
                {"role": "system", "content": CLASSIFICATION_SYSTEM},
                {"role": "user", "content": CLASSIFICATION_USER.format(
                    subject=subject,
                    body=body_text[:3000],  # Cap to avoid token overflow
                )},
            ],
            response_model=Classification,
            temperature=0.05,
            call_label="classify",
        )
        classification = call_result.result
        cost = call_result.usage.estimated_cost_usd or 0.0

        # If injection detected, override human_review_required
        if injection["suspected"]:
            classification = classification.model_copy(update={"human_review_required": True})

        log.info(
            "node.classify.done",
            ticket_id=ticket_id,
            category=classification.category,
            urgency=classification.urgency,
            confidence=classification.confidence,
            injection_suspected=injection["suspected"],
        )

        return {
            "classification": classification.model_dump(),
            "flags": flags,
            "total_llm_cost_usd": state.get("total_llm_cost_usd", 0.0) + cost,
            "total_llm_calls": state.get("total_llm_calls", 0) + 1,
        }

    except Exception as e:
        log.error("node.classify.llm_failed", error=str(e), ticket_id=ticket_id)
        # Fallback classification — flag for human review
        return {
            "classification": {
                "category": "other",
                "urgency": "medium",
                "sentiment": "neutral",
                "confidence": 0.0,
                "human_review_required": True,
                "brief_reason": f"Classification failed: {str(e)[:100]}",
            },
            "flags": flags + ["classification_failed"],
            "total_llm_cost_usd": state.get("total_llm_cost_usd", 0.0),
            "total_llm_calls": state.get("total_llm_calls", 0) + 1,
        }
