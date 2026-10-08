"""Audit log API router."""
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db

router = APIRouter()


@router.get("/audit")
async def list_audit_events(
    ticket_id: str | None = None,
    actor: str | None = None,
    tool: str | None = None,
    event: str | None = None,
    page: int = 1,
    page_size: int = 100,
    db: AsyncSession = Depends(get_db),
):
    return {"events": [], "total": 0, "page": page}


@router.get("/audit/tickets/{ticket_id}")
async def get_ticket_audit(ticket_id: str, db: AsyncSession = Depends(get_db)):
    """Full audit trail for a single ticket — all events in order."""
    return {"ticket_id": ticket_id, "events": [], "chain_intact": True}


@router.get("/audit/export/{ticket_id}")
async def export_audit(ticket_id: str, fmt: str = "json"):
    """Export audit trail as JSON or CSV."""
    # TODO: implement export streaming
    return {"ticket_id": ticket_id, "format": fmt, "events": []}
