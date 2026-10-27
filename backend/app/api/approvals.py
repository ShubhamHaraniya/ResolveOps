"""
backend/app/api/approvals.py
Real Approvals API router.
Supports: Approve & Execute, Edit, Reject, Escalate.
Validates hash & expiry, resumes LangGraph workflow execution, and persists to DB.
"""
import hashlib
import json
import time
from datetime import UTC, datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.store import safe_append
from app.db.models import Approval, ApprovalStatus, AuditEvent, Ticket, now_utc
from app.db.session import get_db
from app.graph.runner import run_workflow_for_ticket
from services.gateway import gateway

router = APIRouter()

# Only pending approvals can be acted on (escalation closes the run).
_ACTIONABLE = (ApprovalStatus.pending,)


def _ts(dt: Optional[datetime]) -> float:
    """Epoch seconds for a DB datetime (SQLite returns naive values; they are stored as UTC)."""
    if dt is None:
        return 0.0
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.timestamp()


def _args_hash(tool: str, args: Dict[str, Any]) -> str:
    """Same scheme as the gateway: SHA256(tool + ':' + sorted compact JSON of args)."""
    normalized = json.dumps(args, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(f"{tool}:{normalized}".encode()).hexdigest()


async def _audit(appr: Approval, event: AuditEvent, reviewer_id: Optional[str], result: str, args: Optional[Dict[str, Any]] = None) -> None:
    """Record a reviewer decision in the hash-chained audit trail."""
    await safe_append(
        event=event,
        ticket_id=appr.ticket_id,
        run_id=appr.run_id,
        actor_type="human",
        actor_id=reviewer_id or "unknown_reviewer",
        tool=appr.tool,
        args=args,
        policy_rule=appr.policy_rule,
        result_status=result,
    )


async def _get_actionable(db: AsyncSession, approval_id: str) -> Approval:
    """Load an approval that can still be acted on, else raise 404/409/403."""
    res = await db.execute(select(Approval).where(Approval.id == approval_id))
    appr = res.scalars().first()
    if not appr:
        raise HTTPException(status_code=404, detail="Approval not found")
    if appr.status not in _ACTIONABLE:
        status_val = appr.status.value if hasattr(appr.status, "value") else str(appr.status)
        raise HTTPException(status_code=409, detail=f"Approval already {status_val}")
    if appr.expires_at and _ts(appr.expires_at) < time.time():
        appr.status = ApprovalStatus.expired
        await db.commit()
        raise HTTPException(status_code=403, detail="Approval has expired (24h limit)")
    return appr


def _sync_gateway(appr: Approval, status: str, reviewer_id: Optional[str], new_args: Optional[Dict[str, Any]] = None) -> None:
    """Mirror a reviewer decision into the gateway's approval registry (re-registering after a restart)."""
    if gateway._get_approval(appr.id) is None:
        gateway.register_approval_record({
            "id": appr.id,
            "run_id": appr.run_id,
            "ticket_id": appr.ticket_id,
            "tool": appr.tool,
            "args_hash": appr.args_hash,
            "status": "pending",
            "expires_at": _ts(appr.expires_at),
        })
    gateway.set_approval_status(appr.id, status, reviewer_id, new_args=new_args)


class ApproveRequest(BaseModel):
    reviewer_id: Optional[str] = "support_lead_01"
    notes: Optional[str] = None


class RejectRequest(BaseModel):
    reviewer_id: Optional[str] = "support_lead_01"
    reason: str = Field(..., description="Reason for rejection")


class EditRequest(BaseModel):
    reviewer_id: Optional[str] = "support_lead_01"
    updated_args: Dict[str, Any] = Field(..., description="Edited tool arguments")
    reason: Optional[str] = "Adjusted arguments by reviewer"


class EscalateRequest(BaseModel):
    reviewer_id: Optional[str] = "support_lead_01"
    escalate_to: Optional[str] = "vp_support"
    reason: str = Field(..., description="Reason for escalation")


@router.get("/approvals")
async def list_approvals(
    status: str = "pending",
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """List real approvals awaiting review."""
    query = select(Approval).order_by(desc(Approval.created_at))
    res = await db.execute(query)
    approvals_db = res.scalars().all()

    items = []
    for a in approvals_db:
        status_val = a.status.value if hasattr(a.status, "value") else str(a.status)
        if status != "all" and status_val != status:
            continue

        # Fetch associated ticket
        t_res = await db.execute(select(Ticket).where(Ticket.id == a.ticket_id))
        t = t_res.scalars().first()

        items.append({
            "id": a.id,
            "ticket_id": a.ticket_id,
            "ticket_number": f"TCK-{a.ticket_id[:8].upper()}" if a.ticket_id else "TCK-UNKNOWN",
            "subject": t.subject if t else "Support Request",
            "requester_email": t.requester_email if t else "",
            "tool": a.tool,
            "args": a.args_redacted or {},
            "policy_rule": a.policy_rule,
            "approver_role": a.approver_role,
            "status": status_val,
            "created_at": a.created_at.isoformat() if a.created_at else None,
            "expires_at": a.expires_at.isoformat() if a.expires_at else None,
        })

    return {"approvals": items, "total": len(items)}


@router.post("/approvals/{approval_id}/approve")
async def approve_action(
    approval_id: str,
    body: ApproveRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Approve an action: record the decision, authorize it in the gateway, resume the workflow."""
    appr = await _get_actionable(db, approval_id)

    appr.status = ApprovalStatus.approved
    appr.reviewed_at = now_utc()
    appr.reviewer_id = body.reviewer_id
    await db.commit()
    _sync_gateway(appr, "approved", body.reviewer_id)
    await _audit(appr, AuditEvent.approved, body.reviewer_id, "approved")

    background_tasks.add_task(
        run_workflow_for_ticket,
        ticket_id=appr.ticket_id,
        run_id=appr.run_id,
        resume_approval=True,
        action_type="approve",
    )

    return {
        "status": "approved",
        "approval_id": approval_id,
        "ticket_id": appr.ticket_id,
        "run_id": appr.run_id,
        "message": "Action approved; workflow resumed for policy revalidation and gateway dispatch",
    }


@router.post("/approvals/{approval_id}/reject")
async def reject_action(
    approval_id: str,
    body: RejectRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Reject an action and close out the workflow."""
    appr = await _get_actionable(db, approval_id)

    appr.status = ApprovalStatus.rejected
    appr.reviewed_at = now_utc()
    appr.reviewer_id = body.reviewer_id
    appr.edit_reason = body.reason
    await db.commit()
    _sync_gateway(appr, "rejected", body.reviewer_id)
    await _audit(appr, AuditEvent.rejected, body.reviewer_id, "rejected")

    background_tasks.add_task(
        run_workflow_for_ticket,
        ticket_id=appr.ticket_id,
        run_id=appr.run_id,
        resume_approval=True,
        action_type="reject",
    )

    return {"status": "rejected", "approval_id": approval_id}


@router.post("/approvals/{approval_id}/edit")
async def edit_action(
    approval_id: str,
    body: EditRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Approve with edited arguments; the approval hash is re-bound to the edited args."""
    appr = await _get_actionable(db, approval_id)

    appr.status = ApprovalStatus.approved
    appr.reviewed_at = now_utc()
    appr.reviewer_id = body.reviewer_id
    appr.edit_reason = body.reason
    appr.args_normalized = body.updated_args
    appr.args_hash = _args_hash(appr.tool, body.updated_args)
    await db.commit()
    _sync_gateway(appr, "approved", body.reviewer_id, new_args=body.updated_args)
    await _audit(appr, AuditEvent.edited, body.reviewer_id, "approved_with_edits", args=body.updated_args)

    background_tasks.add_task(
        run_workflow_for_ticket,
        ticket_id=appr.ticket_id,
        run_id=appr.run_id,
        resume_approval=True,
        approved_args=body.updated_args,
        action_type="approve",
    )

    return {"status": "edited_and_approved", "approval_id": approval_id, "updated_args": body.updated_args}


@router.post("/approvals/{approval_id}/escalate")
async def escalate_action(
    approval_id: str,
    body: EscalateRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Escalate action to a higher authority; the action is not executed."""
    appr = await _get_actionable(db, approval_id)

    appr.status = ApprovalStatus.escalated
    appr.approver_role = body.escalate_to or "vp_support"
    appr.edit_reason = body.reason
    await db.commit()
    _sync_gateway(appr, "escalated", body.reviewer_id)
    await _audit(appr, AuditEvent.escalated, body.reviewer_id, f"escalated_to_{appr.approver_role}")

    background_tasks.add_task(
        run_workflow_for_ticket,
        ticket_id=appr.ticket_id,
        run_id=appr.run_id,
        resume_approval=True,
        action_type="escalate",
    )

    return {"status": "escalated", "approval_id": approval_id, "escalated_to": appr.approver_role}
