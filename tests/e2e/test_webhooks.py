"""
Webhook ingestion: signature schemes, development pass-through, de-duplication, identity safety.
"""
import base64
import hashlib
import hmac
import json
import time


from app.api.webhooks import verify_stripe_signature, verify_zendesk_signature
from app.config import settings
from services.mcp_billing import server as mcp_billing
from tests.e2e.conftest import refund_action


def stripe_header(body: bytes, secret: str, ts: int | None = None) -> str:
    ts = ts or int(time.time())
    sig = hmac.new(secret.encode(), f"{ts}.".encode() + body, hashlib.sha256).hexdigest()
    return f"t={ts},v1={sig}"


def zendesk_headers(body: bytes, secret: str, ts: str = "2026-10-22T10:00:00Z") -> dict:
    digest = hmac.new(secret.encode(), ts.encode() + body, hashlib.sha256).digest()
    return {
        "x-zendesk-webhook-signature": base64.b64encode(digest).decode(),
        "x-zendesk-webhook-signature-timestamp": ts,
    }


# ── Pure signature checks ──────────────────────────────────────────────────

def test_stripe_signature_roundtrip_and_tolerance():
    body = b'{"id":"evt_1"}'
    now = 1_800_000_000
    assert verify_stripe_signature(body, stripe_header(body, "s3cret", now), "s3cret", now=now)
    assert not verify_stripe_signature(body, stripe_header(body, "other", now), "s3cret", now=now)
    assert not verify_stripe_signature(body + b" ", stripe_header(body, "s3cret", now), "s3cret", now=now)
    assert not verify_stripe_signature(body, stripe_header(body, "s3cret", now), "s3cret", now=now + 3600)  # replay
    assert not verify_stripe_signature(body, None, "s3cret")
    assert not verify_stripe_signature(body, "garbage", "s3cret")


def test_zendesk_signature_roundtrip():
    body = b'{"ticket":{}}'
    h = zendesk_headers(body, "s3cret")
    assert verify_zendesk_signature(body, h["x-zendesk-webhook-signature"], h["x-zendesk-webhook-signature-timestamp"], "s3cret")
    assert not verify_zendesk_signature(body, h["x-zendesk-webhook-signature"], h["x-zendesk-webhook-signature-timestamp"], "wrong")
    assert not verify_zendesk_signature(body, None, None, "s3cret")


# ── Endpoint behaviour ─────────────────────────────────────────────────────

def zd_payload(email="john.smith@acme-corp.com", ticket_id=4242):
    return {"ticket": {
        "id": ticket_id, "subject": "Charged twice", "description": "Refund the duplicate $30 charge on INV-001",
        "requester": {"email": email}, "priority": "high",
    }}


async def test_unsigned_webhook_rejected_when_secret_configured(client_and_llm, monkeypatch):
    client, _ = client_and_llm
    monkeypatch.setattr(settings, "zendesk_webhook_secret", "s3cret")
    res = await client.post("/api/webhooks/zendesk", json=zd_payload())
    assert res.status_code == 401


async def test_signed_webhook_creates_ticket_and_deduplicates(client_and_llm, monkeypatch):
    client, llm = client_and_llm
    llm.actions = [refund_action()]
    monkeypatch.setattr(settings, "zendesk_webhook_secret", "s3cret")
    body = json.dumps(zd_payload()).encode()
    headers = {**zendesk_headers(body, "s3cret"), "content-type": "application/json"}

    first = await client.post("/api/webhooks/zendesk", content=body, headers=headers)
    assert first.status_code == 201 and first.json()["status"] == "accepted"

    retry = await client.post("/api/webhooks/zendesk", content=body, headers=headers)
    assert retry.json()["status"] == "duplicate"
    assert retry.json()["ticket_id"] == first.json()["ticket_id"]
    tickets = (await client.get("/api/tickets")).json()["tickets"]
    assert len(tickets) == 1


async def test_unsigned_webhook_accepted_only_in_development(client_and_llm, monkeypatch):
    client, _ = client_and_llm
    monkeypatch.setattr(settings, "environment", "production")
    res = await client.post("/api/webhooks/zendesk", json=zd_payload())
    assert res.status_code == 503  # no secret configured outside development

    monkeypatch.setattr(settings, "environment", "development")
    res = await client.post("/api/webhooks/zendesk", json=zd_payload(ticket_id=1))
    assert res.status_code == 201


async def test_webhook_sender_is_not_auto_authorized(client_and_llm):
    """Unknown senders must not be linked to Acme or registered as authorized contacts."""
    client, llm = client_and_llm
    llm.actions = [refund_action()]
    res = await client.post("/api/webhooks/zendesk", json=zd_payload(email="attacker@fake-acme.example", ticket_id=7))
    detail = (await client.get(f"/api/tickets/{res.json()['ticket_id']}")).json()
    assert detail["customer"]["id"] is None
    assert detail["identity"]["verified"] is False
    assert detail["status"] == "escalated"
    assert mcp_billing._refunds == []


async def test_stripe_webhook_requires_customer_email(client_and_llm):
    client, _ = client_and_llm
    res = await client.post("/api/webhooks/stripe", json={"id": "evt_1", "type": "charge.dispute.created", "data": {"object": {"amount": 5000}}})
    assert res.status_code == 422


async def test_stripe_webhook_signed_flow(client_and_llm, monkeypatch):
    client, llm = client_and_llm
    llm.actions = [refund_action()]
    monkeypatch.setattr(settings, "stripe_webhook_secret", "whsec")
    payload = {"id": "evt_9", "type": "charge.dispute.created",
               "data": {"object": {"customer_email": "john.smith@acme-corp.com", "amount": 3000}}}
    body = json.dumps(payload).encode()
    res = await client.post(
        "/api/webhooks/stripe", content=body,
        headers={"stripe-signature": stripe_header(body, "whsec"), "content-type": "application/json"},
    )
    assert res.status_code == 201
    detail = (await client.get(f"/api/tickets/{res.json()['ticket_id']}")).json()
    assert "stripe_inbound" in detail["risk_flags"]
    assert detail["customer"]["id"] == "ACC-001"
