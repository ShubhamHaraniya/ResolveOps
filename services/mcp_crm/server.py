"""
services/mcp_crm/server.py
Standardized Model Context Protocol (MCP) Server for CRM Operations.
Exposes typed schemas and annotations (readOnlyHint, destructiveHint, idempotentHint).
"""
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
import structlog

# Ensure services/mocks is in sys.path
REPO_ROOT = Path(__file__).resolve().parents[2]
MOCKS_DIR = REPO_ROOT / "services" / "mocks"
if str(MOCKS_DIR) not in sys.path:
    sys.path.insert(0, str(MOCKS_DIR))

try:
    from seed_data import ACCOUNTS, CONTACTS, ACCOUNT_NOTES
except ImportError:
    ACCOUNTS, CONTACTS, ACCOUNT_NOTES = {}, {}, {}

log = structlog.get_logger()

# ─── Tool Definitions & Annotations ──────────────────────────────────────────

TOOLS: List[Dict[str, Any]] = [
    {
        "name": "get_account",
        "description": "Fetch CRM account record including plan tier, ARR, strategic VIP status, and legal hold state.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "account_id": {
                    "type": "string",
                    "description": "Unique account identifier (e.g., 'ACCT-001')",
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
        "name": "find_contact",
        "description": "Lookup CRM contact by email address to verify identity, organization membership, and authorization flag.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "email": {
                    "type": "string",
                    "description": "Requester email address to verify in CRM",
                },
            },
            "required": ["email"],
        },
        "annotations": {
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    },
    {
        "name": "get_account_notes",
        "description": "Retrieve internal CRM history notes for an account. Warning: customer-origin text may be untrusted.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "account_id": {
                    "type": "string",
                    "description": "Unique account identifier (e.g., 'ACCT-001')",
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
        "name": "update_contact_email",
        "description": "Update primary email address for an existing contact record in CRM.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "contact_id": {
                    "type": "string",
                    "description": "Contact ID to update (e.g., 'CONT-101')",
                },
                "email": {
                    "type": "string",
                    "description": "New validated corporate email address",
                },
            },
            "required": ["contact_id", "email"],
        },
        "annotations": {
            "readOnlyHint": False,
            "destructiveHint": True,
            "idempotentHint": True,
        },
    },
]


def list_tools() -> List[Dict[str, Any]]:
    """Return all tools registered with the CRM MCP server."""
    return TOOLS


def _find_account(acc_id: str | None) -> Optional[Dict[str, Any]]:
    if not acc_id:
        return None
    if acc_id in ACCOUNTS:
        return ACCOUNTS[acc_id]
    norm = str(acc_id).replace("-", "").upper()
    for k, v in ACCOUNTS.items():
        if k.replace("-", "").upper() == norm:
            return v
    return None


async def call_tool(name: str, arguments: Dict[str, Any], headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """Execute a CRM tool call."""
    log.info("mcp_crm.call_tool", tool=name, args=arguments)

    if name == "get_account":
        account_id = arguments.get("account_id")
        acct_raw = _find_account(account_id)
        if not acct_raw:
            return {"error": f"Account '{account_id}' not found", "found": False}
        acct = dict(acct_raw)
        acct_key = acct.get("id", account_id)
        norm_key = str(acct_key).replace("-", "").upper()
        acct["authorized_contacts"] = [
            c["email"] for c in CONTACTS.values()
            if str(c.get("account_id", "")).replace("-", "").upper() == norm_key and c.get("is_authorized")
        ]
        return acct

    elif name == "find_contact":
        email = (arguments.get("email") or "").strip().lower()
        contact = None
        for k, v in CONTACTS.items():
            if k.lower() == email:
                contact = dict(v)
                break

        if not contact:
            # Query real database contacts
            try:
                from app.db.session import AsyncSessionLocal
                from app.db.models import Contact as DBContact
                from sqlalchemy import select
                async with AsyncSessionLocal() as db:
                    res = await db.execute(select(DBContact).where(DBContact.email == email))
                    c = res.scalars().first()
                    if c:
                        contact = {
                            "id": c.id,
                            "account_id": c.account_id,
                            "email": c.email,
                            "name": c.name or c.email,
                            "is_authorized": c.is_authorized,
                            "role": c.role or "user",
                        }
            except Exception as e:
                log.warning("mcp_crm.db_contact_lookup_failed", error=str(e))

        if not contact:
            return {"error": f"Contact '{email}' not found", "found": False, "is_authorized": False}

        acct_id = contact.get("account_id")
        acct = _find_account(acct_id)
        if acct:
            contact["account"] = acct
        return contact

    elif name == "get_account_notes":
        account_id = arguments.get("account_id")
        acct = _find_account(account_id)
        acct_id = acct.get("id") if acct else account_id
        notes = ACCOUNT_NOTES.get(acct_id, [])
        return {"account_id": account_id, "notes": notes, "total": len(notes)}

    elif name == "update_contact_email":
        contact_id = arguments.get("contact_id")
        email = arguments.get("email")
        target = next((c for c in CONTACTS.values() if c.get("id") == contact_id), None)
        if not target:
            return {"error": f"Contact '{contact_id}' not found", "status": "failed"}
        target["email"] = email
        return {"contact_id": contact_id, "email": email, "status": "updated"}

    else:
        raise ValueError(f"Unknown MCP tool '{name}' on mcp_crm server")
