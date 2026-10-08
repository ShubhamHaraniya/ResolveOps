"""
services/mcp_access/server.py
Standardized Model Context Protocol (MCP) Server for IAM / Access Management Operations.
Exposes typed schemas and annotations (readOnlyHint, destructiveHint, idempotentHint).
Strictly prevents privilege escalation: only 'viewer' and 'member' roles are permitted; 'admin' is forbidden.
"""
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
    from seed_data import IAM_USERS, IAM_GRANTS
except ImportError:
    IAM_USERS, IAM_GRANTS = {}, {}

log = structlog.get_logger()

ALLOWED_ROLES = {"viewer", "member"}
FORBIDDEN_ROLES = {"admin", "prod-admin", "owner", "superuser", "root", "administrator"}

_grants_store = dict(IAM_GRANTS)
_mfa_resets: List[Dict[str, Any]] = []

# ─── Tool Definitions & Annotations ──────────────────────────────────────────

TOOLS: List[Dict[str, Any]] = [
    {
        "name": "get_user",
        "description": "Fetch IAM identity record, role assignment, and MFA status by user email.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "email": {
                    "type": "string",
                    "description": "User email address",
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
        "name": "list_grants",
        "description": "List all active and historical temporary access grants for an account.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "account_id": {
                    "type": "string",
                    "description": "Account ID to list access grants for",
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
        "name": "grant_access",
        "description": "Grant bounded, time-limited access (viewer or member role only) to an authorized user.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "account_id": {
                    "type": "string",
                    "description": "Account ID granting access",
                },
                "user_email": {
                    "type": "string",
                    "description": "Target user email receiving access grant",
                },
                "role": {
                    "type": "string",
                    "enum": ["viewer", "member"],
                    "description": "Role to grant. Strictly limited to 'viewer' or 'member'. 'admin' is prohibited.",
                },
                "expiry_days": {
                    "type": "integer",
                    "description": "Validity period in days (1 to 30 days maximum)",
                },
                "reason": {
                    "type": "string",
                    "description": "Business justification for access grant",
                },
            },
            "required": ["account_id", "user_email", "role", "reason"],
        },
        "annotations": {
            "readOnlyHint": False,
            "destructiveHint": True,
            "idempotentHint": True,
        },
    },
    {
        "name": "reset_mfa",
        "description": "Trigger an MFA factor reset for a verified user requiring multi-factor authentication re-enrollment.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "email": {
                    "type": "string",
                    "description": "User email address requiring MFA reset",
                },
                "account_id": {
                    "type": "string",
                    "description": "Associated account ID",
                },
                "reason": {
                    "type": "string",
                    "description": "Verification justification",
                },
            },
            "required": ["email", "account_id", "reason"],
        },
        "annotations": {
            "readOnlyHint": False,
            "destructiveHint": True,
            "idempotentHint": True,
        },
    },
]


def list_tools() -> List[Dict[str, Any]]:
    """Return all tools registered with the IAM / Access MCP server."""
    return TOOLS


async def call_tool(name: str, arguments: Dict[str, Any], headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """Execute an IAM / Access tool call."""
    log.info("mcp_access.call_tool", tool=name, args=arguments)

    if name == "get_user":
        email = arguments.get("email")
        if not email or email not in IAM_USERS:
            return {"error": f"User '{email}' not found", "found": False}
        return dict(IAM_USERS[email])

    elif name == "list_grants":
        account_id = arguments.get("account_id")
        grants = _grants_store.get(account_id, [])
        return {"account_id": account_id, "grants": grants, "total": len(grants)}

    elif name == "grant_access":
        role = arguments.get("role", "").lower()
        account_id = arguments.get("account_id")
        user_email = arguments.get("user_email")
        expiry_days = min(max(int(arguments.get("expiry_days", 30)), 1), 30)
        reason = arguments.get("reason", "")

        # Strict security validation
        if role in FORBIDDEN_ROLES:
            raise ValueError(
                f"FORBIDDEN: Role '{role}' is strictly prohibited. "
                "Administrative and privileged roles cannot be granted via agent."
            )
        if role not in ALLOWED_ROLES:
            raise ValueError(f"Role '{role}' is invalid. Allowed roles: {list(ALLOWED_ROLES)}")

        grant = {
            "id": f"GRANT-{str(uuid.uuid4())[:8]}",
            "account_id": account_id,
            "user_email": user_email,
            "role": role,
            "expiry_days": expiry_days,
            "expires_at": (datetime.now(UTC) + timedelta(days=expiry_days)).isoformat(),
            "status": "active",
            "reason": reason,
        }
        if account_id not in _grants_store:
            _grants_store[account_id] = []
        _grants_store[account_id].append(grant)
        return grant

    elif name == "reset_mfa":
        email = arguments.get("email")
        account_id = arguments.get("account_id")
        reason = arguments.get("reason", "")

        reset_event = {
            "reset_id": f"MFA-{str(uuid.uuid4())[:8]}",
            "email": email,
            "account_id": account_id,
            "reason": reason,
            "status": "pending_re_enrollment",
            "initiated_at": datetime.now(UTC).isoformat(),
        }
        _mfa_resets.append(reset_event)
        return reset_event

    else:
        raise ValueError(f"Unknown MCP tool '{name}' on mcp_access server")
