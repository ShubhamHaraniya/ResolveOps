"""Tickets API router."""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db

router = APIRouter()


@router.get("/tickets")
async def list_tickets(
    status: str | None = None,
    category: str | None = None,
    tier: str | None = None,
    customer: str | None = None,
    page: int = 1,
    page_size: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """List tickets with optional filters."""
    # TODO: implement full filtering with SQLAlchemy query
    return {"tickets": [], "total": 0, "page": page, "page_size": page_size}


@router.get("/tickets/{ticket_id}")
async def get_ticket(ticket_id: str, db: AsyncSession = Depends(get_db)):
    """Get full ticket detail with context."""
    # TODO: fetch ticket + account + runs + audit
    raise HTTPException(status_code=404, detail="Ticket not found")


@router.post("/tickets", status_code=201)
async def create_ticket(
    payload: dict,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Create a new ticket and optionally trigger agent run."""
    # TODO: create ticket, optionally start workflow run
    return {"ticket_id": "stub", "status": "created"}


@router.post("/tickets/{ticket_id}/run")
async def run_ticket(
    ticket_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Start or resume an AI workflow run for a ticket."""
    # TODO: start LangGraph workflow run
    return {"run_id": "stub", "status": "started"}
