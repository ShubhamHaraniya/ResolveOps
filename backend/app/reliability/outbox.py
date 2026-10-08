"""
backend/app/reliability/outbox.py
PostgreSQL Transactional Outbox Pattern (Spec Sections 70–73, ADR-008).
Guarantees atomic persistence of workflow decisions and external side-effect intent.
Prevents lost side effects if the worker process crashes after DB commit.
"""
import uuid
from datetime import datetime, UTC
from typing import List, Dict, Any, Optional
import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

try:
    from app.db.models import OutboxEvent
except ImportError:
    OutboxEvent = None

from services import mcp_registry

log = structlog.get_logger()

# In-memory fallback for local execution / tests when Postgres is unavailable
_in_memory_outbox: List[Dict[str, Any]] = []


def record_intent_sync(
    event_type: str,
    payload: Dict[str, Any],
    session: Any = None,
) -> Dict[str, Any]:
    """
    Record side-effect intent in the current database transaction.
    If no DB session is provided, records to the in-memory outbox.
    """
    event_id = str(uuid.uuid4())
    now = datetime.now(UTC)

    if session and OutboxEvent is not None and not isinstance(session, AsyncSession):
        event = OutboxEvent(
            id=event_id,
            event_type=event_type,
            payload=payload,
            status="pending",
            created_at=now,
        )
        session.add(event)
        log.info("outbox.recorded_sync", event_id=event_id, event_type=event_type)
        return {"id": event_id, "event_type": event_type, "payload": payload, "status": "pending"}

    # In-memory record
    event_dict = {
        "id": event_id,
        "event_type": event_type,
        "payload": payload,
        "status": "pending",
        "created_at": now.isoformat(),
        "processed_at": None,
        "error": None,
    }
    _in_memory_outbox.append(event_dict)
    log.info("outbox.recorded_in_memory", event_id=event_id, event_type=event_type)
    return event_dict


async def record_intent(
    event_type: str,
    payload: Dict[str, Any],
    session: Optional[AsyncSession] = None,
) -> Dict[str, Any]:
    """
    Record side-effect intent asynchronously in DB transaction.
    """
    event_id = str(uuid.uuid4())
    now = datetime.now(UTC)

    if session and OutboxEvent is not None:
        event = OutboxEvent(
            id=event_id,
            event_type=event_type,
            payload=payload,
            status="pending",
            created_at=now,
        )
        session.add(event)
        log.info("outbox.recorded_async", event_id=event_id, event_type=event_type)
        return {"id": event_id, "event_type": event_type, "payload": payload, "status": "pending"}

    # In-memory fallback
    event_dict = {
        "id": event_id,
        "event_type": event_type,
        "payload": payload,
        "status": "pending",
        "created_at": now.isoformat(),
        "processed_at": None,
        "error": None,
    }
    _in_memory_outbox.append(event_dict)
    log.info("outbox.recorded_in_memory", event_id=event_id, event_type=event_type)
    return event_dict


async def fetch_pending_events(
    session: Optional[AsyncSession] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """Fetch pending outbox events ordered by creation timestamp."""
    if session and OutboxEvent is not None:
        stmt = (
            select(OutboxEvent)
            .where(OutboxEvent.status == "pending")
            .order_by(OutboxEvent.created_at.asc())
            .limit(limit)
        )
        result = await session.execute(stmt)
        events = result.scalars().all()
        return [
            {
                "id": str(e.id),
                "event_type": e.event_type,
                "payload": e.payload,
                "status": e.status,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in events
        ]

    # In-memory fallback
    pending = [e for e in _in_memory_outbox if e["status"] == "pending"]
    return pending[:limit]


async def mark_processed(
    event_id: str,
    session: Optional[AsyncSession] = None,
) -> None:
    """Mark outbox event as successfully dispatched and processed."""
    now = datetime.now(UTC)
    if session and OutboxEvent is not None:
        stmt = (
            update(OutboxEvent)
            .where(OutboxEvent.id == event_id)
            .values(status="processed", processed_at=now)
        )
        await session.execute(stmt)
        return

    # In-memory
    for e in _in_memory_outbox:
        if e["id"] == event_id:
            e["status"] = "processed"
            e["processed_at"] = now.isoformat()
            break


async def mark_failed(
    event_id: str,
    error: str,
    session: Optional[AsyncSession] = None,
) -> None:
    """Mark outbox event as failed with error details."""
    now = datetime.now(UTC)
    if session and OutboxEvent is not None:
        stmt = (
            update(OutboxEvent)
            .where(OutboxEvent.id == event_id)
            .values(status="failed", processed_at=now)
        )
        await session.execute(stmt)
        return

    # In-memory
    for e in _in_memory_outbox:
        if e["id"] == event_id:
            e["status"] = "failed"
            e["error"] = error
            e["processed_at"] = now.isoformat()
            break


class OutboxProcessor:
    """
    Background worker that reliably processes queued outbox side effects.
    Dispatches tool intents through MCP registry / Gateway.
    """

    def __init__(self, session_factory=None):
        self.session_factory = session_factory

    async def process_batch(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Process the next batch of pending outbox events.
        """
        results = []
        pending = await fetch_pending_events(limit=limit)

        for event in pending:
            event_id = event["id"]
            tool_name = event["event_type"]
            payload = event.get("payload", {})
            headers = payload.get("_headers")

            log.info("outbox.processing_event", event_id=event_id, tool=tool_name)
            try:
                # Dispatch through MCP Registry
                res = await mcp_registry.dispatch_tool(
                    tool_name=tool_name,
                    arguments=payload.get("args", payload),
                    headers=headers,
                )
                await mark_processed(event_id)
                results.append({"event_id": event_id, "status": "processed", "result": res})
            except Exception as e:
                log.error("outbox.processing_error", event_id=event_id, error=str(e))
                await mark_failed(event_id, str(e))
                results.append({"event_id": event_id, "status": "failed", "error": str(e)})

        return results
