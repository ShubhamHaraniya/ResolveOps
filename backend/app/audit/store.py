"""
backend/app/audit/store.py
Persistent, hash-chained audit trail stored in the ``audit_log`` table.

Each row stores ``prev_hash`` (the previous row's ``row_hash``, or 64 zeros for the
first row) and ``row_hash = SHA256(prev_hash + ":" + canonical_json(row fields))``.
``verify_chain`` walks the chain from the genesis hash and recomputes every hash, so
edited, removed or re-ordered rows are detected.

Limits: appends are serialised with an in-process lock, so the chain is only
consistent for a single backend process. Hash chaining is tamper-*evident*, not
tamper-proof: someone with full database write access can rewrite the entire chain.
"""
import asyncio
import hashlib
import json
import re
import uuid
from datetime import UTC, datetime
from typing import Any, Dict, Optional

import structlog
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import session as db_session
from app.db.models import AuditEvent, AuditLog

log = structlog.get_logger()

GENESIS_HASH = "0" * 64

_locks: Dict[int, asyncio.Lock] = {}


def _get_lock() -> asyncio.Lock:
    """One append lock per event loop (asyncio locks must not be shared across loops)."""
    loop_id = id(asyncio.get_running_loop())
    return _locks.setdefault(loop_id, asyncio.Lock())


def redact_pii(value: Any) -> Any:
    """Mask email addresses (j***@domain.com) and phone-like numbers before storage."""
    if isinstance(value, str):
        value = re.sub(
            r"([a-zA-Z0-9._%+-])[a-zA-Z0-9._%+-]*(@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})",
            lambda m: f"{m.group(1)}***{m.group(2)}",
            value,
        )
        value = re.sub(r"\+?[\d\s\-\(\)]{10,}", "[PHONE]", value)
        return value
    if isinstance(value, dict):
        return {k: redact_pii(v) for k, v in value.items()}
    if isinstance(value, list):
        return [redact_pii(item) for item in value]
    return value


def hash_args(args: Optional[dict]) -> Optional[str]:
    if not args:
        return None
    return hashlib.sha256(json.dumps(args, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def _iso(ts: datetime) -> str:
    if ts.tzinfo is None:  # SQLite returns naive datetimes; they are stored as UTC
        ts = ts.replace(tzinfo=UTC)
    return ts.astimezone(UTC).isoformat()


def chain_fields(
    *,
    id: str,
    timestamp: datetime,
    run_id: Optional[str],
    ticket_id: Optional[str],
    actor_type: Optional[str],
    actor_id: Optional[str],
    event: str,
    tool: Optional[str],
    args_hash: Optional[str],
    policy_rule: Optional[str],
    result_status: Optional[str],
) -> Dict[str, Any]:
    """The row fields covered by the hash."""
    return {
        "id": id,
        "timestamp": _iso(timestamp),
        "run_id": run_id,
        "ticket_id": ticket_id,
        "actor_type": actor_type,
        "actor_id": actor_id,
        "event": event,
        "tool": tool,
        "args_hash": args_hash,
        "policy_rule": policy_rule,
        "result_status": result_status,
    }


def compute_row_hash(prev_hash: str, fields: Dict[str, Any]) -> str:
    canonical = json.dumps(fields, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(f"{prev_hash}:{canonical}".encode()).hexdigest()


def _event_value(event: Any) -> str:
    return event.value if hasattr(event, "value") else str(event)


def row_to_fields(row: AuditLog) -> Dict[str, Any]:
    return chain_fields(
        id=row.id,
        timestamp=row.timestamp,
        run_id=row.run_id,
        ticket_id=row.ticket_id,
        actor_type=row.actor_type,
        actor_id=row.actor_id,
        event=_event_value(row.event),
        tool=row.tool,
        args_hash=row.args_hash,
        policy_rule=row.policy_rule,
        result_status=row.result_status,
    )


def row_to_dict(row: AuditLog) -> Dict[str, Any]:
    return {
        "id": row.id,
        "timestamp": _iso(row.timestamp) if row.timestamp else None,
        "run_id": row.run_id,
        "ticket_id": row.ticket_id,
        "actor_type": row.actor_type,
        "actor_id": row.actor_id,
        "event": _event_value(row.event),
        "tool": row.tool,
        "policy_rule": row.policy_rule,
        "policy_version": row.policy_version,
        "result_status": row.result_status,
        "idempotency_key": row.idempotency_key,
        "trace_id": row.trace_id,
        "args_redacted": row.args_redacted or {},
        "prev_hash": row.prev_hash,
        "row_hash": row.row_hash,
    }


async def append_audit_event(
    *,
    event: AuditEvent | str,
    ticket_id: Optional[str],
    run_id: Optional[str] = None,
    actor_type: str = "agent",
    actor_id: str = "agent@resolveops",
    tool: Optional[str] = None,
    args: Optional[dict] = None,
    policy_rule: Optional[str] = None,
    policy_version: Optional[int] = None,
    idempotency_key: Optional[str] = None,
    result_status: Optional[str] = None,
    trace_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Append one event to the chain (own session/transaction) and return the stored row."""
    event_enum = event if isinstance(event, AuditEvent) else AuditEvent(event)
    async with _get_lock():
        async with db_session.AsyncSessionLocal() as db:
            tip = (
                await db.execute(select(AuditLog).order_by(desc(AuditLog.timestamp)).limit(1))
            ).scalars().first()
            prev_hash = tip.row_hash if tip and tip.row_hash else GENESIS_HASH

            row_id = uuid.uuid4().hex
            ts = datetime.now(UTC)
            args_hash = hash_args(args)
            fields = chain_fields(
                id=row_id, timestamp=ts, run_id=run_id, ticket_id=ticket_id, actor_type=actor_type,
                actor_id=actor_id, event=event_enum.value, tool=tool, args_hash=args_hash,
                policy_rule=policy_rule, result_status=result_status,
            )
            row = AuditLog(
                id=row_id, timestamp=ts, run_id=run_id, ticket_id=ticket_id, actor_type=actor_type,
                actor_id=actor_id, event=event_enum, tool=tool, args_hash=args_hash,
                args_redacted=redact_pii(args or {}), policy_rule=policy_rule, policy_version=policy_version,
                idempotency_key=idempotency_key, result_status=result_status, trace_id=trace_id,
                prev_hash=prev_hash, row_hash=compute_row_hash(prev_hash, fields),
            )
            db.add(row)
            await db.commit()
            return row_to_dict(row)


async def safe_append(**kwargs: Any) -> None:
    """Append, logging (not raising) on failure so audit problems never crash a workflow step."""
    try:
        await append_audit_event(**kwargs)
    except Exception as e:  # noqa: BLE001
        log.error("audit.append_failed", error=str(e), event=str(kwargs.get("event")))


async def verify_chain(db: AsyncSession) -> Dict[str, Any]:
    """Walk the chain from the genesis hash and recompute every row hash."""
    rows = (await db.execute(select(AuditLog))).scalars().all()
    by_prev: Dict[str, AuditLog] = {}
    for r in rows:
        if r.prev_hash in by_prev:
            return {
                "valid": False, "total_events": len(rows), "verified_events": 0, "head_hash": None,
                "error": f"Chain forks: more than one row follows hash {str(r.prev_hash)[:12]}…",
            }
        by_prev[r.prev_hash] = r

    verified = 0
    cursor = GENESIS_HASH
    while cursor in by_prev and verified <= len(rows):
        row = by_prev[cursor]
        if compute_row_hash(cursor, row_to_fields(row)) != row.row_hash:
            return {
                "valid": False, "total_events": len(rows), "verified_events": verified,
                "head_hash": cursor if verified else None,
                "error": f"Row {row.id} does not match its stored hash (content was altered)",
            }
        verified += 1
        cursor = row.row_hash

    if verified != len(rows):
        return {
            "valid": False, "total_events": len(rows), "verified_events": verified,
            "head_hash": cursor if verified else None,
            "error": f"{len(rows) - verified} row(s) are not reachable from the genesis hash (rows removed or re-linked)",
        }
    return {
        "valid": True, "total_events": len(rows), "verified_events": verified,
        "head_hash": cursor if verified else None, "error": None,
    }
