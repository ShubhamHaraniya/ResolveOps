"""
backend/app/audit/gateway_sink.py
Persists policy-gateway audit events into the hash-chained ``audit_log`` table.

Registered at startup via ``services.gateway.gateway.set_audit_sink``. The gateway calls
the sink synchronously from inside a running event loop; the write is scheduled as a task.
"""
import asyncio
from typing import Any, Dict, Set

import structlog

from app.audit.store import safe_append
from app.db.models import AuditEvent

log = structlog.get_logger()

_pending: Set[asyncio.Task] = set()

_EVENT_MAP = {
    "tool_call_start": AuditEvent.tool_call_start,
    "tool_call_result": AuditEvent.tool_call_result,
    "tool_call_denied": AuditEvent.tool_call_denied,
}


def persist_gateway_event(event: Dict[str, Any]) -> None:
    mapped = _EVENT_MAP.get(event.get("event", ""))
    if mapped is None:
        return

    if mapped is AuditEvent.tool_call_denied:
        status = f"denied:{event.get('status_code')}"
        args: Dict[str, Any] = {"reason": str(event.get("reason", ""))[:300]}
    else:
        status = event.get("result_status") or event.get("status")
        args = event.get("args_redacted") or {}

    coro = safe_append(
        event=mapped,
        ticket_id=event.get("ticket_id"),
        run_id=event.get("run_id"),
        actor_type=event.get("actor_type", "agent"),
        actor_id="policy_gateway",
        tool=event.get("tool"),
        args=args,
        result_status=status,
    )
    task = asyncio.get_running_loop().create_task(coro)
    _pending.add(task)
    task.add_done_callback(_pending.discard)


async def flush_pending() -> None:
    """Wait for scheduled audit writes (used on shutdown and in tests)."""
    if _pending:
        await asyncio.gather(*list(_pending), return_exceptions=True)
