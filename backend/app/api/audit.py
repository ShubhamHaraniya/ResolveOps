"""
Audit log API router.

Serves the persisted, hash-chained audit trail (table ``audit_log``) and a verifier that
recomputes the chain. See app/audit/store.py for the chain scheme and its limits.
"""
import csv
import io
from datetime import UTC, datetime
from typing import Optional

from fastapi import APIRouter, Depends, Response
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.store import row_to_dict, verify_chain
from app.db.models import AuditEvent, AuditLog
from app.db.session import get_db

router = APIRouter()

CSV_COLUMNS = [
    "id", "timestamp", "ticket_id", "run_id", "actor_type", "actor_id", "event",
    "tool", "policy_rule", "result_status", "prev_hash", "row_hash",
]


def _filters(ticket_id: Optional[str], actor: Optional[str], tool: Optional[str], event: Optional[str]):
    conditions = []
    if ticket_id:
        conditions.append(AuditLog.ticket_id == ticket_id)
    if actor and actor != "all":
        conditions.append(AuditLog.actor_type == actor)
    if tool and tool != "all":
        conditions.append(AuditLog.tool == tool)
    if event and event != "all":
        try:
            conditions.append(AuditLog.event == AuditEvent(event))
        except ValueError:
            conditions.append(AuditLog.id == "__no_such_event__")
    return conditions


@router.get("/audit")
async def list_audit_events(
    ticket_id: Optional[str] = None,
    actor: Optional[str] = None,
    tool: Optional[str] = None,
    event: Optional[str] = None,
    page: int = 1,
    page_size: int = 100,
    db: AsyncSession = Depends(get_db),
):
    """List audit events (newest first) with optional filters."""
    conditions = _filters(ticket_id, actor, tool, event)
    total = (await db.execute(select(func.count(AuditLog.id)).where(*conditions))).scalar() or 0
    rows = (
        await db.execute(
            select(AuditLog)
            .where(*conditions)
            .order_by(desc(AuditLog.timestamp))
            .offset(max(page - 1, 0) * page_size)
            .limit(page_size)
        )
    ).scalars().all()
    return {"events": [row_to_dict(r) for r in rows], "total": total, "page": page, "page_size": page_size}


@router.get("/audit/verify")
async def verify_audit_chain(db: AsyncSession = Depends(get_db)):
    """Recompute the whole hash chain and report whether it is intact."""
    result = await verify_chain(db)
    return {**result, "checked_at": datetime.now(UTC).isoformat(), "algorithm": "SHA-256 hash chain"}


@router.get("/audit/tickets/{ticket_id}")
async def get_ticket_audit(ticket_id: str, db: AsyncSession = Depends(get_db)):
    """All audit events for one ticket in chronological order, plus the global chain status."""
    rows = (
        await db.execute(select(AuditLog).where(AuditLog.ticket_id == ticket_id).order_by(AuditLog.timestamp))
    ).scalars().all()
    chain = await verify_chain(db)
    return {
        "ticket_id": ticket_id,
        "events": [row_to_dict(r) for r in rows],
        "chain_intact": chain["valid"],
        "total": len(rows),
    }


@router.get("/audit/export/{ticket_id}")
async def export_audit(ticket_id: str, fmt: str = "json", db: AsyncSession = Depends(get_db)):
    """Export a ticket's audit trail as JSON or CSV."""
    trail = await get_ticket_audit(ticket_id=ticket_id, db=db)
    events = trail["events"]

    if fmt == "csv":
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=CSV_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(events)
        return Response(
            content=buf.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=audit-{ticket_id}.csv"},
        )

    return {
        "ticket_id": ticket_id,
        "format": "json",
        "exported_at": datetime.now(UTC).isoformat(),
        "chain_intact": trail["chain_intact"],
        "events": events,
    }
