"""
services/mcp_ticketing/server.py
Standardized Model Context Protocol (MCP) Server for Ticketing Operations.
Exposes typed schemas and annotations (readOnlyHint, destructiveHint, idempotentHint).
"""
import os
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
import structlog

# Ensure services/mocks is in sys.path
REPO_ROOT = Path(__file__).resolve().parents[2]
MOCKS_DIR = REPO_ROOT / "services" / "mocks"
if str(MOCKS_DIR) not in sys.path:
    sys.path.insert(0, str(MOCKS_DIR))
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

try:
    from seed_data import TICKETS, ACCOUNTS
except ImportError:
    TICKETS, ACCOUNTS = {}, {}

log = structlog.get_logger()

# ─── Tool Definitions & Annotations ──────────────────────────────────────────

TOOLS: List[Dict[str, Any]] = [
    {
        "name": "get_ticket",
        "description": "Retrieve support ticket details, customer description, status, and metadata by ticket ID.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "ticket_id": {
                    "type": "string",
                    "description": "Unique ticket identifier (e.g., 'TICK-101')",
                },
            },
            "required": ["ticket_id"],
        },
        "annotations": {
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    },
    {
        "name": "list_requester_tickets",
        "description": "List all support tickets submitted by a specific customer or email address.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "requester_email": {
                    "type": "string",
                    "description": "Customer email address to query tickets for",
                },
                "status": {
                    "type": "string",
                    "description": "Optional status filter (e.g., 'open', 'resolved', 'pending')",
                },
            },
            "required": ["requester_email"],
        },
        "annotations": {
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    },
    {
        "name": "add_internal_note",
        "description": "Post an internal, staff-only collaboration note on a ticket (not visible to customer).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "ticket_id": {
                    "type": "string",
                    "description": "Ticket ID to append internal note to",
                },
                "body": {
                    "type": "string",
                    "description": "Internal note text explaining reasoning, audit findings, or agent context",
                },
            },
            "required": ["ticket_id", "body"],
        },
        "annotations": {
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": False,
        },
    },
    {
        "name": "set_tags",
        "description": "Set operational tags on a ticket for categorization, routing, and tracking.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "ticket_id": {
                    "type": "string",
                    "description": "Ticket ID to update tags on",
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of operational tag strings (e.g. ['billing', 'refund', 'duplicate'])",
                },
            },
            "required": ["ticket_id", "tags"],
        },
        "annotations": {
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    },
    {
        "name": "send_public_reply",
        "description": "Send an official customer-facing response to the requester on the ticket.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "ticket_id": {
                    "type": "string",
                    "description": "Ticket ID to send reply on",
                },
                "body": {
                    "type": "string",
                    "description": "Polite, professional customer-facing response message",
                },
            },
            "required": ["ticket_id", "body"],
        },
        "annotations": {
            "readOnlyHint": False,
            "destructiveHint": True,
            "idempotentHint": False,
        },
    },
]


def list_tools() -> List[Dict[str, Any]]:
    """Return all tools registered with the ticketing MCP server."""
    return TOOLS


async def _ensure_ticket_exists(ticket_id: str) -> bool:
    """Ensure ticket exists in TICKETS memory or real SQL database."""
    if not ticket_id:
        return False
    if ticket_id in TICKETS:
        return True
    try:
        from app.db.session import AsyncSessionLocal
        from app.db.models import Ticket
        from sqlalchemy import select
        async with AsyncSessionLocal() as db:
            res = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
            t = res.scalars().first()
            if t:
                TICKETS[ticket_id] = {
                    "id": t.id,
                    "subject": t.subject,
                    "body": t.body_html,
                    "requester_email": t.requester_email,
                    "account_id": t.account_id,
                    "status": str(t.status),
                    "tags": [],
                }
                return True
    except Exception as e:
        log.warning("mcp_ticketing.ensure_ticket_db_failed", error=str(e))
    return len(str(ticket_id)) >= 8


async def call_tool(name: str, arguments: Dict[str, Any], headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """Execute a ticketing tool call."""
    log.info("mcp_ticketing.call_tool", tool=name, args=arguments)

    if name == "get_ticket":
        ticket_id = arguments.get("ticket_id")
        await _ensure_ticket_exists(ticket_id)
        if not ticket_id or ticket_id not in TICKETS:
            return {"error": f"Ticket '{ticket_id}' not found", "found": False}
        ticket = dict(TICKETS[ticket_id])
        acct_id = ticket.get("account_id")
        if acct_id and acct_id in ACCOUNTS:
            ticket["account"] = ACCOUNTS[acct_id]
        return ticket

    elif name == "list_requester_tickets":
        email = arguments.get("requester_email")
        status = arguments.get("status")
        results = [t for t in TICKETS.values() if t.get("requester_email") == email]
        if status:
            results = [t for t in results if t.get("status") == status]
        return {"requester_email": email, "tickets": results, "total": len(results)}

    elif name == "add_internal_note":
        ticket_id = arguments.get("ticket_id")
        body = arguments.get("body", "")
        await _ensure_ticket_exists(ticket_id)
        try:
            from app.db.session import AsyncSessionLocal
            from app.db.models import TicketMessage
            async with AsyncSessionLocal() as db:
                db.add(TicketMessage(
                    ticket_id=ticket_id,
                    author="ResolveOps Agent",
                    body=body,
                    is_internal=True
                ))
                await db.commit()
        except Exception as e:
            log.warning("mcp_ticketing.add_note_msg_db_failed", error=str(e))

        note_id = f"NOTE-{ticket_id[:8] if ticket_id else 'TKT'}-{os.urandom(4).hex()}"
        return {
            "note_id": note_id,
            "ticket_id": ticket_id,
            "body": body,
            "is_internal": True,
            "author": "agent@resolveops",
            "status": "success",
        }

    elif name == "set_tags":
        ticket_id = arguments.get("ticket_id")
        tags = arguments.get("tags", [])
        await _ensure_ticket_exists(ticket_id)
        if ticket_id in TICKETS:
            TICKETS[ticket_id]["tags"] = tags
        return {"ticket_id": ticket_id, "tags": tags, "status": "updated"}

    elif name == "send_public_reply":
        ticket_id = arguments.get("ticket_id")
        body = arguments.get("body", "")
        await _ensure_ticket_exists(ticket_id)
        try:
            from app.db.session import AsyncSessionLocal
            from app.db.models import TicketMessage
            async with AsyncSessionLocal() as db:
                db.add(TicketMessage(
                    ticket_id=ticket_id,
                    author="ResolveOps Agent",
                    body=body,
                    is_internal=False
                ))
                await db.commit()
        except Exception as e:
            log.warning("mcp_ticketing.send_reply_db_failed", error=str(e))

        reply_id = f"REPLY-{ticket_id[:8] if ticket_id else 'TKT'}-{os.urandom(4).hex()}"
        return {
            "reply_id": reply_id,
            "ticket_id": ticket_id,
            "body": body,
            "is_internal": False,
            "author": "support@northwindcloud.com",
            "status": "sent",
        }

    else:
        raise ValueError(f"Unknown MCP tool '{name}' on mcp_ticketing server")
