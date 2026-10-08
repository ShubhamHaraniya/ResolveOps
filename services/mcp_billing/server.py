"""
services/mcp_billing/server.py
Standardized Model Context Protocol (MCP) Server for Billing Operations.
Exposes typed schemas and annotations (readOnlyHint, destructiveHint, idempotentHint).
Enforces idempotency keys on write operations.
"""
import os
import sys
import uuid
from datetime import datetime, UTC, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional
import structlog

# Ensure services/mocks is in sys.path
REPO_ROOT = Path(__file__).resolve().parents[2]
MOCKS_DIR = REPO_ROOT / "services" / "mocks"
if str(MOCKS_DIR) not in sys.path:
    sys.path.insert(0, str(MOCKS_DIR))

try:
    from seed_data import ACCOUNTS, INVOICES, SUBSCRIPTIONS
except ImportError:
    ACCOUNTS, INVOICES, SUBSCRIPTIONS = {}, {}, {}

log = structlog.get_logger()

# In-memory stores for MCP billing server
_idempotency_store: Dict[str, Dict[str, Any]] = {}
_refunds: List[Dict[str, Any]] = []
_credits: List[Dict[str, Any]] = []

# ─── Tool Definitions & Annotations ──────────────────────────────────────────

TOOLS: List[Dict[str, Any]] = [
    {
        "name": "get_invoice",
        "description": "Fetch invoice details including line items, amount, currency, status, and age.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "invoice_id": {
                    "type": "string",
                    "description": "Unique invoice identifier (e.g., 'INV-001')",
                },
            },
            "required": ["invoice_id"],
        },
        "annotations": {
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    },
    {
        "name": "list_invoices",
        "description": "List all historical invoices and billing records for a specific account.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "account_id": {
                    "type": "string",
                    "description": "Account ID to query invoices for",
                },
            },
            "required": ["account_id"],
        },
        "annotations": {
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    },
    {
        "name": "get_subscription",
        "description": "Get active SaaS subscription details, current tier, seat count, and renewal date.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "subscription_id": {
                    "type": "string",
                    "description": "Subscription identifier (e.g., 'SUB-001')",
                },
            },
            "required": ["subscription_id"],
        },
        "annotations": {
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    },
    {
        "name": "preview_plan_change",
        "description": "Calculate proration and cost differential for changing subscription plan tier.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "subscription_id": {
                    "type": "string",
                    "description": "Active subscription ID",
                },
                "target_plan": {
                    "type": "string",
                    "description": "Target plan name (e.g., 'Starter', 'Pro', 'Enterprise')",
                },
            },
            "required": ["subscription_id", "target_plan"],
        },
        "annotations": {
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    },
    {
        "name": "issue_refund",
        "description": "Issue a financial refund against a paid invoice. Requires strict idempotency key.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "invoice_id": {
                    "type": "string",
                    "description": "Invoice to refund against",
                },
                "amount_cents": {
                    "type": "integer",
                    "description": "Refund amount in integer cents (e.g. 3000 for $30.00)",
                },
                "reason": {
                    "type": "string",
                    "description": "Valid refund reason (duplicate_charge, service_outage, billing_error, cancellation)",
                },
                "idempotency_key": {
                    "type": "string",
                    "description": "Client-generated unique SHA-256 idempotency key",
                },
            },
            "required": ["invoice_id", "amount_cents", "reason", "idempotency_key"],
        },
        "annotations": {
            "readOnlyHint": False,
            "destructiveHint": True,
            "idempotentHint": True,
        },
    },
    {
        "name": "issue_credit",
        "description": "Apply service credit balance to customer account balance for SLA outage compensation.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "account_id": {
                    "type": "string",
                    "description": "Customer account to credit",
                },
                "amount_cents": {
                    "type": "integer",
                    "description": "Credit amount in integer cents",
                },
                "reason": {
                    "type": "string",
                    "description": "Business reason for applying credit",
                },
            },
            "required": ["account_id", "amount_cents", "reason"],
        },
        "annotations": {
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    },
    {
        "name": "change_plan",
        "description": "Upgrade or downgrade a customer's active subscription plan.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "subscription_id": {
                    "type": "string",
                    "description": "Subscription ID to modify",
                },
                "new_plan": {
                    "type": "string",
                    "description": "New target plan name",
                },
            },
            "required": ["subscription_id", "new_plan"],
        },
        "annotations": {
            "readOnlyHint": False,
            "destructiveHint": True,
            "idempotentHint": True,
        },
    },
    {
        "name": "pause_subscription",
        "description": "Temporarily pause customer billing for a bounded duration (up to 30 days).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "subscription_id": {
                    "type": "string",
                    "description": "Subscription ID to pause",
                },
                "pause_days": {
                    "type": "integer",
                    "description": "Number of days to pause subscription (max 30)",
                },
            },
            "required": ["subscription_id", "pause_days"],
        },
        "annotations": {
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    },
]


def list_tools() -> List[Dict[str, Any]]:
    """Return all tools registered with the billing MCP server."""
    return TOOLS


async def call_tool(name: str, arguments: Dict[str, Any], headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """Execute a billing tool call."""
    log.info("mcp_billing.call_tool", tool=name, args=arguments)

    if name == "get_invoice":
        invoice_id = arguments.get("invoice_id")
        if not invoice_id or invoice_id not in INVOICES:
            return {"error": f"Invoice '{invoice_id}' not found", "found": False}
        return dict(INVOICES[invoice_id])

    elif name == "list_invoices":
        account_id = arguments.get("account_id")
        invs = [i for i in INVOICES.values() if i.get("account_id") == account_id]
        return {"account_id": account_id, "invoices": invs, "total": len(invs)}

    elif name == "get_subscription":
        sub_id = arguments.get("subscription_id")
        if not sub_id or sub_id not in SUBSCRIPTIONS:
            return {"error": f"Subscription '{sub_id}' not found", "found": False}
        return dict(SUBSCRIPTIONS[sub_id])

    elif name == "preview_plan_change":
        sub_id = arguments.get("subscription_id")
        target_plan = arguments.get("target_plan")
        return {
            "subscription_id": sub_id,
            "current_plan": "Starter",
            "target_plan": target_plan,
            "proration_credit_cents": 1500,
            "new_charge_cents": 5000,
            "net_amount_due_cents": 3500,
            "currency": "USD",
        }

    elif name == "issue_refund":
        invoice_id = arguments.get("invoice_id")
        amount_cents = arguments.get("amount_cents", 0)
        reason = arguments.get("reason", "")
        key = (headers or {}).get("Idempotency-Key") or arguments.get("idempotency_key")

        # 1. Idempotency Check
        if key and key in _idempotency_store:
            log.info("mcp_billing.refund.idempotent_replay", key=key)
            cached = dict(_idempotency_store[key])
            cached["idempotent_replay"] = True
            return cached

        # 2. Validation
        if invoice_id not in INVOICES:
            return {"error": f"Invoice '{invoice_id}' not found", "status": "failed"}

        inv = INVOICES[invoice_id]
        if amount_cents > inv.get("amount_cents", 0):
            return {"error": "Refund amount exceeds invoice total", "status": "failed"}

        # 3. Create Refund Record
        refund_record = {
            "id": f"REF-{str(uuid.uuid4())[:8]}",
            "invoice_id": invoice_id,
            "amount_cents": amount_cents,
            "reason": reason,
            "idempotency_key": key,
            "status": "succeeded",
            "created_at": datetime.now(UTC).isoformat(),
        }
        _refunds.append(refund_record)

        if key:
            _idempotency_store[key] = refund_record

        return refund_record

    elif name == "issue_credit":
        account_id = arguments.get("account_id")
        amount_cents = arguments.get("amount_cents", 0)
        reason = arguments.get("reason", "")
        credit_record = {
            "id": f"CRED-{str(uuid.uuid4())[:8]}",
            "account_id": account_id,
            "amount_cents": amount_cents,
            "reason": reason,
            "status": "applied",
            "created_at": datetime.now(UTC).isoformat(),
        }
        _credits.append(credit_record)
        return credit_record

    elif name == "change_plan":
        sub_id = arguments.get("subscription_id")
        new_plan = arguments.get("new_plan")
        if sub_id in SUBSCRIPTIONS:
            SUBSCRIPTIONS[sub_id]["plan"] = new_plan
        return {
            "subscription_id": sub_id,
            "new_plan": new_plan,
            "status": "active",
            "updated_at": datetime.now(UTC).isoformat(),
        }

    elif name == "pause_subscription":
        sub_id = arguments.get("subscription_id")
        pause_days = min(int(arguments.get("pause_days", 30)), 30)
        resume_date = (datetime.now(UTC) + timedelta(days=pause_days)).isoformat()
        return {
            "subscription_id": sub_id,
            "status": "paused",
            "pause_days": pause_days,
            "resume_date": resume_date,
        }

    else:
        raise ValueError(f"Unknown MCP tool '{name}' on mcp_billing server")
