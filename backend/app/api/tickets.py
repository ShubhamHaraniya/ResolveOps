"""
backend/app/api/tickets.py
Real ticket management and live agent execution API routes.
Backed by database persistence and the LangGraph workflow engine.
"""
import uuid
from typing import Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.session import get_db
from app.db.models import (
    Ticket, Account, Contact, TicketMessage, WorkflowRun, Approval, TicketStatus, now_utc
)
from app.mapping import map_category, map_urgency
from app.graph.runner import run_workflow_for_ticket, get_latest_run_for_ticket
from app.policy.engine import most_restrictive

router = APIRouter()


class CreateTicketRequest(BaseModel):
    requester_email: str = Field(..., description="Customer requester email")
    subject: str = Field(..., description="Ticket subject line")
    body: str = Field(..., description="Ticket message body")
    category: Optional[str] = Field("other", description="Optional ticket category")
    priority: Optional[str] = Field("medium", description="Optional ticket priority (low, medium, high, urgent)")
    account_id: Optional[str] = Field(None, description="Optional target account ID or name")
    is_authorized_contact: Optional[bool] = Field(None, description="Development-only: register the requester as an authorized admin contact (ignored in other environments)")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    scenario: Optional[str] = Field(None, description="Scenario template used if any")


@router.get("/tickets")
async def list_tickets(
    status: Optional[str] = None,
    category: Optional[str] = None,
    tier: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """List tickets with real database query and customer metadata."""
    query = select(Ticket).order_by(desc(Ticket.created_at))

    res = await db.execute(query)
    tickets = res.scalars().all()

    items = []
    for t in tickets:
        # Determine latest run
        latest_run = get_latest_run_for_ticket(t.id)
        run_state = (latest_run or {}).get("state", {})
        classification = run_state.get("classification", {})

        # Customer account
        account_name = "Unregistered / Unknown"
        is_strategic = False
        is_legal_hold = False
        if t.account_id:
            acc_res = await db.execute(select(Account).where(Account.id == t.account_id))
            acc = acc_res.scalars().first()
            if acc:
                account_name = acc.name
                is_strategic = acc.is_strategic
                is_legal_hold = acc.is_legal_hold

        status_val = t.status.value if hasattr(t.status, "value") else str(t.status)
        category_val = t.category.value if hasattr(t.category, "value") else str(t.category or "other")
        urgency_val = t.urgency.value if hasattr(t.urgency, "value") else str(t.urgency or "medium")

        # Determine tier
        policy_decisions = run_state.get("policy_decisions", [])
        strictest = most_restrictive(policy_decisions)
        tier_val = strictest.get("tier") if strictest else (
            "approval" if status_val == "awaiting_approval" else None
        )

        item = {
            "id": t.id,
            "ticket_number": f"TCK-{t.id[:8].upper()}",
            "subject": t.subject,
            "body": t.body_html or "",
            "requester_email": t.requester_email,
            "category": category_val,
            "priority": urgency_val,
            "tier": tier_val,
            "status": status_val,
            "confidence": classification.get("confidence"),
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "customer": {
                "id": t.account_id or "acc_guest",
                "name": account_name,
                "is_strategic": is_strategic,
                "is_legal_hold": is_legal_hold,
            },
        }

        # Apply filters
        if status and status != "all" and item["status"] != status:
            continue
        if category and category != "all" and item["category"] != category:
            continue
        if tier and tier != "all" and item["tier"] != tier:
            continue
        if search:
            s = search.lower()
            if not (s in item["subject"].lower() or s in item["requester_email"].lower() or s in item["customer"]["name"].lower()):
                continue

        items.append(item)

    return {
        "tickets": items,
        "total": len(items),
        "page": page,
        "page_size": page_size,
    }


@router.get("/tickets/{ticket_id}")
async def get_ticket(ticket_id: str, db: AsyncSession = Depends(get_db)):
    """Get full ticket detail with real LangGraph workflow state and audit history."""
    res = await db.execute(select(Ticket).where(
        (Ticket.id == ticket_id) |
        (Ticket.id == ticket_id.replace("-", ""))
    ))
    ticket = res.scalars().first()

    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    # Fetch messages
    msg_res = await db.execute(select(TicketMessage).where(TicketMessage.ticket_id == ticket_id).order_by(TicketMessage.created_at))
    db_messages = msg_res.scalars().all()

    # Customer info
    account = None
    if ticket.account_id:
        acc_res = await db.execute(select(Account).where(Account.id == ticket.account_id))
        account = acc_res.scalars().first()

    # Latest workflow run
    run = get_latest_run_for_ticket(ticket_id)
    if not run:
        # Check database
        run_res = await db.execute(
            select(WorkflowRun).where(WorkflowRun.ticket_id == ticket_id).order_by(desc(WorkflowRun.started_at))
        )
        r_db = run_res.scalars().first()
        if r_db:
            run = {
                "run_id": r_db.id,
                "ticket_id": r_db.ticket_id,
                "status": r_db.status.value if hasattr(r_db.status, "value") else str(r_db.status),
                "started_at": r_db.started_at.isoformat() if r_db.started_at else None,
                "completed_at": r_db.completed_at.isoformat() if r_db.completed_at else None,
                "error": r_db.error,
                "nodes": r_db.nodes_timeline or [],
                "state": r_db.state_json or {},
            }

    state = (run or {}).get("state", {})
    proposal = state.get("proposal", {})
    identity = state.get("identity", {})
    context = state.get("context", {})
    classification = state.get("classification", {})
    policy_decisions = state.get("policy_decisions", [])
    executed = state.get("executed", [])
    approval_data = state.get("approval", {})

    # Active approval from DB if not in state
    if not approval_data and ticket.status == TicketStatus.awaiting_approval:
        appr_res = await db.execute(
            select(Approval).where(Approval.ticket_id == ticket_id).order_by(desc(Approval.created_at))
        )
        a_db = appr_res.scalars().first()
        if a_db:
            approval_data = {
                "id": a_db.id,
                "ticket_id": a_db.ticket_id,
                "tool": a_db.tool,
                "args_hash": a_db.args_hash,
                "args_redacted": a_db.args_redacted,
                "args_full": a_db.args_normalized,
                "policy_rule": a_db.policy_rule,
                "approver_role": a_db.approver_role,
                "status": a_db.status.value if hasattr(a_db.status, "value") else str(a_db.status),
                "reasoning": proposal.get("reasoning_summary", "Approval required under company policy"),
                "draft_reply": proposal.get("draft_reply", ""),
            }

    # Format customer object (only what is stored; unknown requesters have no account)
    customer_payload = {
        "id": account.id if account else None,
        "name": account.name if account else "Unregistered / Unknown",
        "plan": (account.plan.value if hasattr(account.plan, "value") else str(account.plan)) if account else None,
        "arr_cents": account.arr_cents if account else None,
        "is_strategic": account.is_strategic if account else False,
        "is_legal_hold": account.is_legal_hold if account else False,
        "csm_owner": account.csm_owner if account else None,
    }

    # Messages
    messages = [
        {
            "id": f"msg_req_{ticket.id[:6]}",
            "author": ticket.requester_email,
            "role": "customer",
            "body": ticket.body_html or "",
            "is_internal": False,
            "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
        }
    ]
    for m in db_messages:
        messages.append({
            "id": m.id,
            "author": m.author,
            "role": "agent" if "Agent" in (m.author or "") else "customer",
            "body": m.body,
            "is_internal": m.is_internal,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        })

    strictest = most_restrictive(policy_decisions)
    tier_val = strictest.get("tier") if strictest else (
        "approval" if ticket.status == TicketStatus.awaiting_approval else None
    )

    return {
        "id": ticket.id,
        "ticket_number": f"TCK-{ticket.id[:8].upper()}",
        "subject": ticket.subject,
        "body": ticket.body_html or "",
        "requester_email": ticket.requester_email,
        "category": ticket.category.value if hasattr(ticket.category, "value") else str(ticket.category or "other"),
        "priority": ticket.urgency.value if hasattr(ticket.urgency, "value") else str(ticket.urgency or "medium"),
        "status": ticket.status.value if hasattr(ticket.status, "value") else str(ticket.status),
        "tier": tier_val,
        "confidence": classification.get("confidence"),
        "sentiment": classification.get("sentiment"),
        "risk_flags": list(set(list(ticket.risk_flags or []) + list(state.get("flags", [])))),
        "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
        "customer": customer_payload,
        "messages": messages,
        "run": run,
        "workflow_progress": (run or {}).get("nodes", []),
        "ai_analysis": {
            "classification": classification,
            "reasoning_summary": proposal.get("reasoning_summary", ""),
            "draft_reply": proposal.get("draft_reply", ""),
        },
        "identity": identity,
        "context": context,
        "retrieved_knowledge": context.get("rag_results") or proposal.get("rag_citations", []),
        "policy_decision": strictest,
        "policy_decisions": policy_decisions,
        "proposed_actions": proposal.get("actions", []),
        "approval": approval_data,
        "execution_result": executed,
    }


@router.post("/tickets", status_code=201)
async def create_ticket(
    body: CreateTicketRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Create a real support ticket in the database and trigger the LangGraph workflow.
    Validates request with Pydantic, saves ticket, and starts live execution.
    """
    ticket_id = str(uuid.uuid4())
    run_id = str(uuid.uuid4())

    # Associate with a customer account: explicit account_id/name, else the account of a known contact.
    account_id = None
    if body.account_id:
        acc_res = await db.execute(
            select(Account).where(Account.id == body.account_id)
        )
        acc = acc_res.scalars().first()
        if acc:
            account_id = acc.id
    else:
        c_res = await db.execute(select(Contact).where(Contact.email == body.requester_email))
        c_existing = c_res.scalars().first()
        if c_existing and c_existing.account_id:
            account_id = c_existing.account_id

    # Development-only simulation flag: register the requester as an authorized admin contact so the
    # happy path can be exercised with arbitrary emails. Ignored outside ENVIRONMENT=development.
    if body.is_authorized_contact is True and account_id and settings.is_development:
        c_res = await db.execute(select(Contact).where(Contact.email == body.requester_email))
        if not c_res.scalars().first():
            db.add(Contact(
                account_id=account_id,
                email=body.requester_email,
                name=body.requester_email.split("@")[0].capitalize(),
                is_authorized=True,
                role="admin"
            ))
            await db.flush()

    ticket = Ticket(
        id=ticket_id,
        account_id=account_id,
        requester_email=body.requester_email,
        subject=body.subject,
        body_html=body.body,
        category=map_category(body.category),
        urgency=map_urgency(body.priority),
        status=TicketStatus.open,
        risk_flags=[],
        created_at=now_utc(),
    )
    db.add(ticket)
    await db.commit()

    # Launch real workflow runner asynchronously
    background_tasks.add_task(run_workflow_for_ticket, ticket_id, run_id)

    return {
        "ticket_id": ticket_id,
        "run_id": run_id,
        "status": "running",
        "message": "Ticket created and LangGraph agent workflow launched",
    }


@router.post("/tickets/{ticket_id}/run")
async def run_ticket(
    ticket_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Start or rerun LangGraph workflow for an existing ticket."""
    res = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
    ticket = res.scalars().first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    run_id = str(uuid.uuid4())
    background_tasks.add_task(run_workflow_for_ticket, ticket_id, run_id)

    return {
        "run_id": run_id,
        "ticket_id": ticket_id,
        "status": "running",
    }


class TicketReplyRequest(BaseModel):
    sender_type: str = Field("customer", description="'customer' or 'agent'")
    body: str = Field(..., description="Message text body")
    is_internal: bool = Field(False, description="Whether message is internal agent note")


@router.post("/tickets/{ticket_id}/reply", status_code=201)
async def reply_to_ticket(
    ticket_id: str,
    req: TicketReplyRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Append a customer or agent reply to an existing ticket conversation thread.
    If the message is from a customer, automatically re-activates the LangGraph
    agent workflow with full conversational memory and historical state.
    """
    res = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
    ticket = res.scalars().first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    message_id = str(uuid.uuid4())
    msg = TicketMessage(
        id=message_id,
        ticket_id=ticket_id,
        author=req.sender_type,
        body=req.body,
        is_internal=req.is_internal,
        created_at=now_utc(),
    )
    db.add(msg)

    run_id = None
    if req.sender_type == "customer" and not req.is_internal:
        # Re-activate ticket
        ticket.status = TicketStatus.in_progress
        run_id = str(uuid.uuid4())
        background_tasks.add_task(run_workflow_for_ticket, ticket_id, run_id)

    await db.commit()

    return {
        "message_id": message_id,
        "ticket_id": ticket_id,
        "sender_type": req.sender_type,
        "run_id": run_id,
        "status": "running" if run_id else "saved",
    }

