"""
backend/app/graph/runner.py
Live workflow execution runner for ResolveOps.
Executes the real LangGraph node chain, records live node durations,
manages human approval interrupts and resumes, and syncs real database state.
"""
from datetime import datetime, UTC
import time
import uuid
from typing import Dict, Any, Optional, List

import structlog
from sqlalchemy import select, update

from app.audit.store import safe_append
from app.db.session import AsyncSessionLocal
from app.db.models import (
    Approval, ApprovalStatus, AuditEvent, Ticket, TicketCategory, TicketMessage, TicketStatus, WorkflowRun, WorkflowStatus, now_utc
)
from app.graph.workflow import get_compiled_workflow
from app.mapping import map_category, map_urgency
from app.policy.engine import most_restrictive
from app.observability.langfuse_client import get_telemetry

log = structlog.get_logger()

# In-memory fast cache of active runs: run_id -> run_dict
_ACTIVE_RUNS: Dict[str, Dict[str, Any]] = {}

NODE_DEFINITIONS = [
    ("intake", "Intake"),
    ("classify", "Classification"),
    ("verify_identity", "Identity Verification"),
    ("gather_context", "Context Gathering"),
    ("plan_action", "Groq Planning"),
    ("policy_check", "Policy Check"),
    ("approval_interrupt", "Waiting for Approval"),
    ("execute", "Execution"),
    ("verify_outcome", "Verification"),
    ("draft_reply", "Draft Reply"),
    ("close", "Ticket Finalize"),
]


def init_nodes_timeline() -> List[Dict[str, Any]]:
    """Initialize fresh node timeline for live tracking."""
    return [
        {
            "node": node_key,
            "name": display_name,
            "status": "pending",
            "started_at": None,
            "completed_at": None,
            "duration_ms": None,
            "error": None,
        }
        for node_key, display_name in NODE_DEFINITIONS
    ]


def get_run(run_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve run state by run_id."""
    return _ACTIVE_RUNS.get(run_id)


def get_latest_run_for_ticket(ticket_id: str) -> Optional[Dict[str, Any]]:
    """Find most recent run for ticket_id."""
    matching = [r for r in _ACTIVE_RUNS.values() if r.get("ticket_id") == ticket_id]
    if matching:
        return sorted(matching, key=lambda x: x.get("started_at") or "", reverse=True)[0]
    return None


async def run_workflow_for_ticket(
    ticket_id: str,
    run_id: Optional[str] = None,
    resume_approval: bool = False,
    approved_args: Optional[Dict[str, Any]] = None,
    action_type: str = "approve",
) -> Dict[str, Any]:
    """
    Execute or resume the real workflow for a ticket via compiled LangGraph StateGraph.
    Updates in-memory timeline and database records step-by-step with Langfuse telemetry.
    """
    if not run_id:
        run_id = str(uuid.uuid4())

    log.info("workflow.runner.start", ticket_id=ticket_id, run_id=run_id, resume_approval=resume_approval)

    # Fetch real ticket from DB
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
        ticket_record = res.scalars().first()
        if not ticket_record:
            log.error("workflow.runner.ticket_not_found", ticket_id=ticket_id)
            return {"error": "Ticket not found", "status": "failed"}

        # Fetch conversation messages for multi-turn context
        msg_res = await db.execute(
            select(TicketMessage).where(TicketMessage.ticket_id == ticket_id).order_by(TicketMessage.created_at)
        )
        db_messages = msg_res.scalars().all()
        conversation_history = [
            {
                "id": m.id,
                "sender_type": getattr(m, "author", "customer") or "customer",
                "body": m.body,
                "is_internal": m.is_internal,
                "created_at": m.created_at.isoformat() if m.created_at else "",
            }
            for m in db_messages
        ]

        raw_ticket = {
            "id": ticket_record.id,
            "subject": ticket_record.subject,
            "body": ticket_record.body_html or "",
            "body_html": ticket_record.body_html or "",
            "requester_email": ticket_record.requester_email,
            "account_id": ticket_record.account_id,
            "category": getattr(ticket_record.category, "value", str(ticket_record.category or "other")),
            "urgency": getattr(ticket_record.urgency, "value", str(ticket_record.urgency or "medium")),
            "risk_flags": ticket_record.risk_flags or [],
            "messages": conversation_history,
        }

    telemetry = get_telemetry()
    if resume_approval:
        if run_id in _ACTIVE_RUNS:
            run_info = _ACTIVE_RUNS[run_id]
            state: Dict[str, Any] = run_info["state"]
            timeline: List[Dict[str, Any]] = run_info["nodes"]
            trace_id = state.get("langfuse_trace_id") or run_id
        else:
            async with AsyncSessionLocal() as db:
                run_res = await db.execute(select(WorkflowRun).where(WorkflowRun.id == run_id))
                run_record = run_res.scalars().first()
                state = run_record.state_json if run_record and run_record.state_json else {}
                timeline = run_record.nodes_timeline if run_record and run_record.nodes_timeline else init_nodes_timeline()
                trace_id = (run_record.langfuse_trace_id if run_record else None) or state.get("langfuse_trace_id") or run_id
                run_info = {
                    "run_id": run_id,
                    "ticket_id": ticket_id,
                    "status": "running",
                    "started_at": datetime.now(UTC).isoformat(),
                    "completed_at": None,
                    "error": None,
                    "nodes": timeline,
                    "state": state,
                }
                _ACTIVE_RUNS[run_id] = run_info

        state["resume_approval"] = True
        state["action_type"] = action_type
        if approved_args and state.get("proposal", {}).get("actions"):
            state["proposal"]["actions"][0]["args"] = approved_args
            state["proposal"]["actions"][0]["arguments"] = approved_args
    else:
        timeline = init_nodes_timeline()
        trace_id = telemetry.create_trace(
            name="ticket_resolution_flow",
            ticket_id=ticket_id,
            run_id=run_id,
            metadata={
                "requester": raw_ticket.get("requester_email"),
                "category": raw_ticket.get("category"),
                "urgency": raw_ticket.get("urgency"),
            },
            tags=[str(raw_ticket.get("category", "support")), str(raw_ticket.get("urgency", "medium"))],
        )

        state = {
            "ticket_id": ticket_id,
            "run_id": run_id,
            "raw_ticket": raw_ticket,
            "status": "running",
            "flags": list(raw_ticket.get("risk_flags", [])),
            "executed": [],
            "policy_decisions": [],
            "total_tool_calls": 0,
            "total_llm_cost_usd": 0.0,
            "langfuse_trace_id": trace_id,
            "resume_approval": False,
        }
        run_info = {
            "run_id": run_id,
            "ticket_id": ticket_id,
            "status": "running",
            "started_at": datetime.now(UTC).isoformat(),
            "completed_at": None,
            "error": None,
            "nodes": timeline,
            "state": state,
        }
        _ACTIVE_RUNS[run_id] = run_info

        # Persist initial WorkflowRun in DB with trace_id
        async with AsyncSessionLocal() as db:
            run_db = WorkflowRun(
                id=run_id,
                ticket_id=ticket_id,
                status=WorkflowStatus.running,
                started_at=now_utc(),
                nodes_timeline=timeline,
                state_json=state,
                langfuse_trace_id=trace_id,
            )
            db.add(run_db)
            await db.commit()

    def get_timeline_node(key: str) -> Dict[str, Any]:
        for n in timeline:
            if n["node"] == key:
                return n
        return {}

    # Update approval_interrupt timeline node when resuming
    if resume_approval:
        node_appr = get_timeline_node("approval_interrupt")
        if action_type == "reject":
            node_appr["status"] = "failed"
            node_appr["error"] = "Rejected by human reviewer"
        elif action_type == "escalate":
            node_appr["status"] = "completed"
            node_appr["notes"] = "Escalated to senior management"
        else:
            node_appr["status"] = "completed"

    # Compile and execute via LangGraph engine
    app_graph = get_compiled_workflow()
    langfuse_cb = telemetry.get_langchain_callback(trace_id=trace_id)
    callbacks = [langfuse_cb] if langfuse_cb else []
    thread_suffix = "resume" if resume_approval else "initial"
    config = {
        "configurable": {"thread_id": f"{ticket_id}:{thread_suffix}"},
        "callbacks": callbacks,
    }

    active_node = "intake" if not resume_approval else "execute"
    run_info["status"] = "running"
    step_t0 = time.perf_counter()

    try:
        async for event in app_graph.astream(state, config=config, stream_mode="updates"):
            for node_key, node_output in event.items():
                active_node = node_key
                n = get_timeline_node(node_key)
                duration_ms = node_output.pop("_node_duration_ms", None) if isinstance(node_output, dict) else None
                if duration_ms is None:
                    duration_ms = round((time.perf_counter() - step_t0) * 1000, 2)
                step_t0 = time.perf_counter()

                if isinstance(node_output, dict):
                    node_output.pop("_last_node", None)
                    state.update(node_output)

                n["status"] = "completed"
                n["completed_at"] = datetime.now(UTC).isoformat()
                n["duration_ms"] = duration_ms

                # Special node post-processing
                if node_key == "classify":
                    # Refine the stored category/urgency with the model's classification when it is specific.
                    cls = state.get("classification", {})
                    new_category = map_category(cls.get("category"))
                    values: Dict[str, Any] = {"urgency": map_urgency(cls.get("urgency"))}
                    if new_category != TicketCategory.other:
                        values["category"] = new_category
                    async with AsyncSessionLocal() as db:
                        await db.execute(update(Ticket).where(Ticket.id == ticket_id).values(**values))
                        await db.commit()

                elif node_key == "verify_identity":
                    identity = state.get("identity", {})
                    if not identity.get("verified", False):
                        log.warning("workflow.identity_unverified_escalating", ticket_id=ticket_id)
                        for skip_key in [
                            "gather_context", "plan_action", "policy_check",
                            "approval_interrupt", "execute", "verify_outcome", "draft_reply"
                        ]:
                            get_timeline_node(skip_key)["status"] = "skipped"

                elif node_key == "plan_action":
                    proposal_actions = state.get("proposal", {}).get("actions", [])
                    await safe_append(
                        event=AuditEvent.proposed, ticket_id=ticket_id, run_id=run_id, actor_type="agent",
                        actor_id="langgraph_orchestrator", result_status=f"{len(proposal_actions)} action(s) proposed",
                        trace_id=trace_id,
                    )

                elif node_key == "policy_check":
                    for decision in state.get("policy_decisions", []):
                        await safe_append(
                            event=AuditEvent.policy_decision, ticket_id=ticket_id, run_id=run_id, actor_type="system",
                            actor_id="policy_engine", tool=decision.get("tool"), policy_rule=decision.get("rule_id"),
                            policy_version=decision.get("policy_version"), result_status=decision.get("tier"),
                            trace_id=trace_id,
                        )
                    strictest = most_restrictive(state.get("policy_decisions", []))
                    tier = strictest.get("tier", "forbidden") if strictest else "forbidden"
                    if tier == "auto":
                        get_timeline_node("approval_interrupt")["status"] = "skipped"
                    elif tier == "forbidden":
                        for skip_key in ["approval_interrupt", "execute", "verify_outcome", "draft_reply"]:
                            get_timeline_node(skip_key)["status"] = "skipped"

                elif node_key == "approval_interrupt":
                    n["status"] = "paused"
                    run_info["status"] = "awaiting_approval"
                    state["status"] = "awaiting_approval"

                    # Persist Approval record in DB
                    approval_data = state.get("approval", {})
                    async with AsyncSessionLocal() as db:
                        await db.execute(
                            update(Ticket).where(Ticket.id == ticket_id).values(
                                status=TicketStatus.awaiting_approval,
                                risk_flags=list(state.get("flags", [])),
                            )
                        )
                        await db.execute(
                            update(WorkflowRun).where(WorkflowRun.id == run_id).values(
                                status=WorkflowStatus.awaiting_approval,
                                nodes_timeline=timeline,
                                state_json=state,
                            )
                        )
                        if approval_data:
                            appr_db = Approval(
                                id=approval_data.get("id", str(uuid.uuid4())[:12]),
                                run_id=run_id,
                                ticket_id=ticket_id,
                                tool=approval_data.get("tool", "billing.issue_refund"),
                                args_hash=approval_data.get("args_hash", ""),
                                args_redacted=approval_data.get("args_redacted", {}),
                                args_normalized=approval_data.get("args_full", {}),
                                policy_rule=approval_data.get("policy_rule", "REF-002"),
                                approver_role=approval_data.get("approver_role", "support_lead"),
                                status=ApprovalStatus.pending,
                                expires_at=datetime.fromtimestamp(approval_data.get("expires_at", time.time() + 86400), tz=UTC),
                            )
                            db.add(appr_db)
                        await db.commit()

                    await safe_append(
                        event=AuditEvent.approval_requested, ticket_id=ticket_id, run_id=run_id, actor_type="system",
                        actor_id="langgraph_orchestrator", tool=approval_data.get("tool"),
                        policy_rule=approval_data.get("policy_rule"), result_status="pending", trace_id=trace_id,
                    )
                    log.info("workflow.paused_for_approval", ticket_id=ticket_id, approval_id=approval_data.get("id"))
                    return run_info

                elif node_key == "close":
                    if resume_approval and action_type in ("reject", "escalate"):
                        for skip_key in ["execute", "verify_outcome", "draft_reply"]:
                            get_timeline_node(skip_key)["status"] = "skipped"

    except Exception as e:
        err_msg = str(e)
        n = get_timeline_node(active_node)
        n["status"] = "failed"
        n["error"] = err_msg
        n["completed_at"] = datetime.now(UTC).isoformat()
        run_info["status"] = "failed"
        run_info["completed_at"] = datetime.now(UTC).isoformat()
        run_info["error"] = err_msg
        state["status"] = "failed"
        state["error"] = err_msg

        async with AsyncSessionLocal() as db:
            await db.execute(
                update(WorkflowRun).where(WorkflowRun.id == run_id).values(
                    status=WorkflowStatus.failed,
                    completed_at=now_utc(),
                    nodes_timeline=timeline,
                    state_json=state,
                    error=err_msg,
                )
            )
            await db.commit()
        await safe_append(
            event=AuditEvent.failed, ticket_id=ticket_id, run_id=run_id, actor_type="system",
            actor_id="langgraph_orchestrator", result_status=f"failed at {active_node}"[:50], trace_id=trace_id,
        )
        log.error("workflow.runner.failed", ticket_id=ticket_id, step=active_node, error=err_msg)
        return run_info

    # Finalize completed or escalated execution state
    is_escalated = (
        state.get("status") == "escalated"
        or not state.get("identity", {}).get("verified", True)
        or any(d.get("tier") == "forbidden" for d in state.get("policy_decisions", []))
        or (resume_approval and action_type in ("reject", "escalate"))
    )

    if is_escalated:
        run_info["status"] = "escalated"
        run_info["completed_at"] = datetime.now(UTC).isoformat()
        state["status"] = "escalated"

        async with AsyncSessionLocal() as db:
            await db.execute(
                update(Ticket).where(Ticket.id == ticket_id).values(
                    status=TicketStatus.escalated,
                    risk_flags=list(state.get("flags", [])),
                )
            )
            await db.execute(
                update(WorkflowRun).where(WorkflowRun.id == run_id).values(
                    status=WorkflowStatus.escalated,
                    completed_at=now_utc(),
                    nodes_timeline=timeline,
                    state_json=state,
                )
            )
            if not state.get("identity", {}).get("verified", True):
                reason_detail = state.get("identity", {}).get("reason", "Requester is not recognized as an authorized account contact")
                msg = TicketMessage(
                    ticket_id=ticket_id,
                    author="ResolveOps Agent",
                    body=(
                        f"⚠️ Identity Verification Failed: The email '{raw_ticket.get('requester_email')}' "
                        f"could not be verified as an authorized contact for this account.\n"
                        f"Reason: {reason_detail}.\n\n"
                        "Automated Execution Halted: No refund or modification has been made. "
                        "This ticket has been escalated to human support for customer identity verification."
                    ),
                    is_internal=False,
                )
                db.add(msg)
            await db.commit()

        await safe_append(
            event=AuditEvent.escalated, ticket_id=ticket_id, run_id=run_id, actor_type="system",
            actor_id="langgraph_orchestrator", result_status=action_type if resume_approval else "escalated",
            trace_id=trace_id,
        )
        log.info("workflow.runner.escalated", ticket_id=ticket_id, run_id=run_id)
        return run_info

    # Happy path: workflow completed
    run_info["status"] = "done"
    run_info["completed_at"] = datetime.now(UTC).isoformat()
    state["status"] = "done"

    reply_text = state.get("proposal", {}).get("draft_reply") or "Ticket processed successfully."
    async with AsyncSessionLocal() as db:
        await db.execute(
            update(Ticket).where(Ticket.id == ticket_id).values(
                status=TicketStatus.resolved,
                risk_flags=list(state.get("flags", [])),
            )
        )
        await db.execute(
            update(WorkflowRun).where(WorkflowRun.id == run_id).values(
                status=WorkflowStatus.done,
                completed_at=now_utc(),
                nodes_timeline=timeline,
                state_json=state,
            )
        )
        has_public_reply = any(e.get("tool") == "ticketing.send_public_reply" for e in state.get("executed", []))
        if not has_public_reply:
            msg = TicketMessage(
                ticket_id=ticket_id,
                author="ResolveOps Agent",
                body=reply_text,
                is_internal=False,
            )
            db.add(msg)
        await db.commit()

    log.info("workflow.runner.completed", ticket_id=ticket_id, run_id=run_id, status=run_info["status"])
    return run_info
