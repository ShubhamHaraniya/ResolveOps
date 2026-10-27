"""
backend/app/api/webhooks.py
Inbound webhook ingestion for Zendesk-style ticket events and Stripe-style billing events.

Each accepted event creates a ticket, records a ``received`` audit event and starts the
workflow in the background. Requests are authenticated with a signature when the matching
secret is configured; with no secret they are accepted only when ENVIRONMENT=development.
Events are de-duplicated on (source, external event id).
"""
import base64
import hashlib
import hmac
import time
import uuid
from typing import Any, Dict, List, Optional

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.store import safe_append
from app.config import settings
from app.db.models import AuditEvent, AuditLog, Contact, Ticket, TicketCategory, TicketStatus, TicketUrgency, now_utc
from app.db.session import get_db
from app.graph.runner import run_workflow_for_ticket
from app.mapping import map_urgency

log = structlog.get_logger()
router = APIRouter()

STRIPE_TOLERANCE_SECONDS = 300


# ── Signature verification ──────────────────────────────────────────────────

def verify_stripe_signature(body: bytes, header: Optional[str], secret: str, now: Optional[float] = None) -> bool:
    """Stripe scheme: header ``t=<unix>,v1=<hex>``; v1 = HMAC-SHA256(secret, f"{t}.{body}")."""
    if not header:
        return False
    parts = [p.strip().split("=", 1) for p in header.split(",") if "=" in p]
    timestamps = [v for k, v in parts if k == "t"]
    signatures = [v for k, v in parts if k == "v1"]
    if not timestamps or not signatures:
        return False
    try:
        ts = int(timestamps[0])
    except ValueError:
        return False
    if abs((now if now is not None else time.time()) - ts) > STRIPE_TOLERANCE_SECONDS:
        return False
    expected = hmac.new(secret.encode(), f"{ts}.".encode() + body, hashlib.sha256).hexdigest()
    return any(hmac.compare_digest(expected, sig) for sig in signatures)


def verify_zendesk_signature(body: bytes, signature: Optional[str], timestamp: Optional[str], secret: str) -> bool:
    """Zendesk scheme: base64(HMAC-SHA256(secret, timestamp + body)) in X-Zendesk-Webhook-Signature."""
    if not signature or not timestamp:
        return False
    digest = hmac.new(secret.encode(), timestamp.encode() + body, hashlib.sha256).digest()
    return hmac.compare_digest(base64.b64encode(digest).decode(), signature.strip())


def _require_signature(valid: Optional[bool], secret: str, source: str) -> None:
    """`valid` is None when no signature check was possible (no secret configured)."""
    if not secret:
        if settings.is_development:
            log.warning("webhook.unsigned_accepted", source=source, note="no secret configured (development only)")
            return
        raise HTTPException(status_code=503, detail=f"{source} webhook secret is not configured")
    if not valid:
        raise HTTPException(status_code=401, detail=f"Invalid {source} webhook signature")


# ── Payload models ──────────────────────────────────────────────────────────

class ZendeskRequester(BaseModel):
    name: Optional[str] = None
    email: str = Field(..., description="Customer email address")


class ZendeskTicketPayload(BaseModel):
    id: Optional[Any] = None
    subject: str = Field(..., description="Ticket subject line")
    description: Optional[str] = None
    body: Optional[str] = None
    requester: ZendeskRequester
    priority: Optional[str] = "normal"
    tags: List[str] = Field(default_factory=list)


class ZendeskWebhookEnvelope(BaseModel):
    ticket: ZendeskTicketPayload


class StripeWebhookEnvelope(BaseModel):
    id: str = Field(..., description="Stripe event ID")
    type: str = Field(..., description="Stripe event type")
    data: Dict[str, Any] = Field(default_factory=dict)


# ── Helpers ─────────────────────────────────────────────────────────────────

async def _find_duplicate(db: AsyncSession, source: str, external_id: str) -> Optional[AuditLog]:
    res = await db.execute(
        select(AuditLog).where(
            AuditLog.event == AuditEvent.received,
            AuditLog.idempotency_key == f"{source}:{external_id}",
        )
    )
    return res.scalars().first()


async def _account_for(db: AsyncSession, email: str) -> Optional[str]:
    """Account of an existing contact with this email (no guessing from the email domain)."""
    res = await db.execute(select(Contact).where(Contact.email == email))
    contact = res.scalars().first()
    return contact.account_id if contact else None


def _guess_category(text: str) -> TicketCategory:
    """Rough keyword hint for the initial category; the classify node refines it during the run."""
    text = text.lower()
    if "refund" in text or "charged twice" in text or "duplicate" in text:
        return TicketCategory.refund
    if "credit" in text or "outage" in text:
        return TicketCategory.credit
    if "plan" in text or "tier" in text:
        return TicketCategory.plan_change
    if "access" in text or "role" in text:
        return TicketCategory.access_request
    return TicketCategory.other


async def _create_and_launch(
    db: AsyncSession,
    background_tasks: BackgroundTasks,
    *,
    source: str,
    external_id: str,
    email: str,
    subject: str,
    body_text: str,
    category: TicketCategory,
    urgency: TicketUrgency,
    risk_flags: List[str],
    audit_extra: Dict[str, Any],
) -> Dict[str, Any]:
    ticket_id = str(uuid.uuid4())
    run_id = str(uuid.uuid4())
    db.add(Ticket(
        id=ticket_id,
        account_id=await _account_for(db, email),
        requester_email=email,
        subject=subject,
        body_html=body_text,
        category=category,
        urgency=urgency,
        status=TicketStatus.open,
        risk_flags=risk_flags,
        created_at=now_utc(),
    ))
    await db.commit()

    await safe_append(
        event=AuditEvent.received,
        ticket_id=ticket_id,
        run_id=run_id,
        actor_type="system",
        actor_id=f"webhook:{source}",
        args={"source": source, "external_id": external_id, **audit_extra},
        idempotency_key=f"{source}:{external_id}",
        result_status="accepted",
    )
    background_tasks.add_task(run_workflow_for_ticket, ticket_id, run_id)
    log.info("webhook.processed", source=source, ticket_id=ticket_id, run_id=run_id)
    return {
        "status": "accepted",
        "source": source,
        "ticket_id": ticket_id,
        "run_id": run_id,
        "ticket_number": f"TCK-{ticket_id[:8].upper()}",
    }


# ── Endpoints ───────────────────────────────────────────────────────────────

@router.post("/webhooks/zendesk", status_code=201)
async def receive_zendesk_webhook(
    envelope: ZendeskWebhookEnvelope,
    background_tasks: BackgroundTasks,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Create a ticket from a Zendesk-style ticket event and start the workflow."""
    secret = settings.zendesk_webhook_secret
    valid = verify_zendesk_signature(
        await request.body(),
        request.headers.get("x-zendesk-webhook-signature"),
        request.headers.get("x-zendesk-webhook-signature-timestamp"),
        secret,
    ) if secret else None
    _require_signature(valid, secret, "Zendesk")

    t = envelope.ticket
    external_id = str(t.id) if t.id is not None else ""
    if external_id:
        dup = await _find_duplicate(db, "zendesk", external_id)
        if dup:
            return {"status": "duplicate", "source": "zendesk", "ticket_id": dup.ticket_id}

    body_text = t.description or t.body or t.subject
    return await _create_and_launch(
        db, background_tasks,
        source="zendesk",
        external_id=external_id or f"no-id-{uuid.uuid4().hex[:8]}",
        email=t.requester.email.strip(),
        subject=t.subject,
        body_text=body_text,
        category=_guess_category(f"{t.subject} {body_text}"),
        urgency=map_urgency(t.priority),
        risk_flags=[],
        audit_extra={"tags": t.tags},
    )


@router.post("/webhooks/stripe", status_code=201)
async def receive_stripe_webhook(
    envelope: StripeWebhookEnvelope,
    background_tasks: BackgroundTasks,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Create a refund-review ticket from a Stripe-style billing event and start the workflow."""
    secret = settings.stripe_webhook_secret
    valid = verify_stripe_signature(
        await request.body(), request.headers.get("stripe-signature"), secret
    ) if secret else None
    _require_signature(valid, secret, "Stripe")

    obj = envelope.data.get("object", {}) or {}
    email = (obj.get("customer_email") or "").strip()
    if not email:
        raise HTTPException(status_code=422, detail="data.object.customer_email is required to open a ticket")

    dup = await _find_duplicate(db, "stripe", envelope.id)
    if dup:
        return {"status": "duplicate", "source": "stripe", "ticket_id": dup.ticket_id}

    amount_cents = obj.get("amount")
    amount_text = f"${amount_cents / 100:.2f}" if isinstance(amount_cents, int) else "amount not provided"
    reason = obj.get("reason") or "not provided"
    details = obj.get("description") or "none"
    return await _create_and_launch(
        db, background_tasks,
        source="stripe",
        external_id=envelope.id,
        email=email,
        subject=f"Stripe billing event: {envelope.type} ({amount_text})",
        body_text=(
            f"Automated billing webhook from Stripe.\nEvent type: {envelope.type}\n"
            f"Amount: {amount_text}\nReason: {reason}\nDetails: {details}"
        ),
        category=TicketCategory.refund,
        urgency=TicketUrgency.high,
        risk_flags=["stripe_inbound"],
        audit_extra={"stripe_type": envelope.type, "amount_cents": amount_cents},
    )
