"""
Mock Billing System — CRITICAL RELIABILITY BEHAVIORS

Key behaviors:
- Idempotency: same Idempotency-Key → same result, no duplicate
- Random 500s: BILLING_ERROR_RATE controls transient failures
- Timeout simulation: BILLING_TIMEOUT_SIMULATION commits then sleeps (timeout-after-commit)
- Refund limits: > $500 → 422
- Age window: invoice > 30 days → 422
"""
import asyncio
import hashlib
import os
import random
import time
from datetime import datetime, UTC, timedelta

from fastapi import FastAPI, HTTPException, Header, Request
from pydantic import BaseModel, Field
from typing import Literal
from seed_data import ACCOUNTS, INVOICES, SUBSCRIPTIONS

app = FastAPI(title="Mock Billing", version="1.0.0")

# In-memory idempotency store: key → result
_idempotency_store: dict[str, dict] = {}
# In-memory refund store (list of refund records)
_refunds: list[dict] = []
_credits: list[dict] = []


def _error_rate() -> float:
    return float(os.environ.get("BILLING_ERROR_RATE", "0.1"))

def _timeout_sim() -> bool:
    return os.environ.get("BILLING_TIMEOUT_SIMULATION", "false").lower() == "true"

def _maybe_error():
    """Randomly raise a 500 to simulate transient billing failures."""
    if random.random() < _error_rate():
        raise HTTPException(status_code=503, detail="Billing service transient error — please retry")

def _invoice_age_days(invoice_id: str) -> int:
    inv = INVOICES.get(invoice_id)
    if not inv:
        return 0
    inv_date = datetime.fromisoformat(inv["invoice_date"].replace("Z", "+00:00"))
    return (datetime.now(UTC) - inv_date).days


@app.get("/health")
def health():
    return {"status": "ok", "service": "mock-billing"}


@app.get("/customers/{account_id}/invoices")
def list_invoices(account_id: str):
    if account_id not in ACCOUNTS:
        raise HTTPException(status_code=404, detail="Account not found")
    invs = [i for i in INVOICES.values() if i["account_id"] == account_id]
    return {"account_id": account_id, "invoices": invs, "total": len(invs)}


@app.get("/invoices/{invoice_id}")
def get_invoice(invoice_id: str):
    if invoice_id not in INVOICES:
        raise HTTPException(status_code=404, detail="Invoice not found")
    inv = dict(INVOICES[invoice_id])
    inv["age_days"] = _invoice_age_days(invoice_id)
    return inv


@app.get("/subscriptions/{subscription_id}")
def get_subscription(subscription_id: str):
    if subscription_id not in SUBSCRIPTIONS:
        raise HTTPException(status_code=404, detail="Subscription not found")
    return SUBSCRIPTIONS[subscription_id]


class IssueRefundRequest(BaseModel):
    invoice_id: str
    amount_cents: int = Field(gt=0, le=50000)
    reason: Literal["duplicate_charge", "service_outage", "billing_error", "cancellation"]
    idempotency_key: str  # Required — must be provided by gateway


@app.post("/refunds", status_code=201)
async def issue_refund(
    payload: IssueRefundRequest,
    idempotency_key: str = Header(None, alias="Idempotency-Key"),
):
    """
    CRITICAL: Idempotency enforced.
    Same Idempotency-Key → return original result, no second refund.
    """
    key = idempotency_key or payload.idempotency_key

    # 1. Idempotency check — return cached result if key seen before
    if key and key in _idempotency_store:
        result = _idempotency_store[key]
        result["idempotent_replay"] = True
        return result

    # 2. Validate invoice exists
    if payload.invoice_id not in INVOICES:
        raise HTTPException(status_code=422, detail=f"Invoice {payload.invoice_id} not found")

    # 3. Validate refund window (30 days)
    age = _invoice_age_days(payload.invoice_id)
    if age > 30:
        raise HTTPException(
            status_code=422,
            detail=f"Invoice {payload.invoice_id} is {age} days old — outside 30-day refund window"
        )

    # 4. Validate amount <= invoice amount
    inv = INVOICES[payload.invoice_id]
    if payload.amount_cents > inv["amount_cents"]:
        raise HTTPException(
            status_code=422,
            detail=f"Refund amount {payload.amount_cents} exceeds invoice amount {inv['amount_cents']}"
        )

    # 5. Transient error simulation
    _maybe_error()

    # 6. TIMEOUT-AFTER-COMMIT simulation
    # Simulates: refund committed to billing DB, then network dies before response
    if _timeout_sim():
        # Commit the refund FIRST
        refund_id = f"REF-{len(_refunds)+1:06d}"
        result = {
            "refund_id": refund_id,
            "invoice_id": payload.invoice_id,
            "amount_cents": payload.amount_cents,
            "reason": payload.reason,
            "status": "completed",
            "created_at": datetime.now(UTC).isoformat(),
            "idempotency_key": key,
            "idempotent_replay": False,
        }
        _refunds.append(result)
        if key:
            _idempotency_store[key] = result
        # THEN simulate timeout (response never arrives to caller)
        await asyncio.sleep(29)  # caller's 30s timeout will fire first

    # 7. Normal path — create refund
    refund_id = f"REF-{len(_refunds)+1:06d}"
    result = {
        "refund_id": refund_id,
        "invoice_id": payload.invoice_id,
        "amount_cents": payload.amount_cents,
        "reason": payload.reason,
        "status": "completed",
        "created_at": datetime.now(UTC).isoformat(),
        "idempotency_key": key,
        "idempotent_replay": False,
    }
    _refunds.append(result)
    if key:
        _idempotency_store[key] = result

    return result


@app.get("/refunds")
def list_refunds(idempotency_key: str = None):
    """Read-back endpoint — find refund by idempotency key."""
    if idempotency_key and idempotency_key in _idempotency_store:
        return {"found": True, "refund": _idempotency_store[idempotency_key]}
    return {"found": False, "refund": None}


class IssueCreditRequest(BaseModel):
    account_id: str
    amount_cents: int = Field(gt=0, le=100000)
    reason: str
    idempotency_key: str


@app.post("/credits", status_code=201)
def issue_credit(payload: IssueCreditRequest):
    if payload.idempotency_key in _idempotency_store:
        return _idempotency_store[payload.idempotency_key]
    _maybe_error()
    credit_id = f"CRD-{len(_credits)+1:06d}"
    result = {
        "credit_id": credit_id,
        "account_id": payload.account_id,
        "amount_cents": payload.amount_cents,
        "reason": payload.reason,
        "status": "active",
        "created_at": datetime.now(UTC).isoformat(),
        "idempotency_key": payload.idempotency_key,
    }
    _credits.append(result)
    _idempotency_store[payload.idempotency_key] = result
    return result


class ChangePlanRequest(BaseModel):
    new_plan: Literal["starter", "pro", "enterprise", "enterprise_plus"]
    idempotency_key: str


@app.post("/subscriptions/{subscription_id}/change-plan", status_code=200)
def change_plan(subscription_id: str, payload: ChangePlanRequest):
    if subscription_id not in SUBSCRIPTIONS:
        raise HTTPException(status_code=404, detail="Subscription not found")
    _maybe_error()
    return {
        "subscription_id": subscription_id,
        "old_plan": SUBSCRIPTIONS[subscription_id]["plan"],
        "new_plan": payload.new_plan,
        "status": "changed",
        "idempotency_key": payload.idempotency_key,
    }


@app.post("/subscriptions/{subscription_id}/preview-plan-change")
def preview_plan_change(subscription_id: str, new_plan: str):
    if subscription_id not in SUBSCRIPTIONS:
        raise HTTPException(status_code=404, detail="Subscription not found")
    return {
        "subscription_id": subscription_id,
        "current_plan": SUBSCRIPTIONS[subscription_id]["plan"],
        "new_plan": new_plan,
        "proration_credit_cents": 5000,
        "next_invoice_cents": 8000,
        "effective_date": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
    }


@app.post("/subscriptions/{subscription_id}/pause")
def pause_subscription(subscription_id: str, reason: str = "customer_request"):
    if subscription_id not in SUBSCRIPTIONS:
        raise HTTPException(status_code=404, detail="Subscription not found")
    return {"subscription_id": subscription_id, "status": "paused", "reason": reason}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
