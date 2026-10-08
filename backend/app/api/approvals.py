"""Approvals API router."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db

router = APIRouter()


class ApproveRequest(BaseModel):
    reviewer_id: str
    notes: str | None = None


class RejectRequest(BaseModel):
    reviewer_id: str
    reason: str


class EditRequest(BaseModel):
    reviewer_id: str
    updated_args: dict
    reason: str


class EscalateRequest(BaseModel):
    reviewer_id: str
    escalate_to: str
    reason: str


@router.get("/approvals")
async def list_approvals(
    status: str = "pending",
    category: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """List approvals awaiting review."""
    return {"approvals": [], "total": 0}


@router.post("/approvals/{approval_id}/approve")
async def approve_action(
    approval_id: str,
    body: ApproveRequest,
    db: AsyncSession = Depends(get_db),
):
    """Approve an action — gateway validates hash before executing."""
    # TODO: validate approval exists, not expired, not invalidated
    # TODO: call gateway with approval token → execute
    raise HTTPException(status_code=404, detail="Approval not found")


@router.post("/approvals/{approval_id}/reject")
async def reject_action(
    approval_id: str,
    body: RejectRequest,
    db: AsyncSession = Depends(get_db),
):
    """Reject an action."""
    raise HTTPException(status_code=404, detail="Approval not found")


@router.post("/approvals/{approval_id}/edit")
async def edit_action(
    approval_id: str,
    body: EditRequest,
    db: AsyncSession = Depends(get_db),
):
    """Edit action args — creates new approval record requiring fresh approval."""
    raise HTTPException(status_code=404, detail="Approval not found")


@router.post("/approvals/{approval_id}/escalate")
async def escalate_action(
    approval_id: str,
    body: EscalateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Escalate action to higher approval role."""
    raise HTTPException(status_code=404, detail="Approval not found")
