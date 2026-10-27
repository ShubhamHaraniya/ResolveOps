"""
Analytics API router.

Every figure is computed from live database state or from run state held by this
process (`_ACTIVE_RUNS`, gateway audit log). When there is no data for a metric the
API returns ``null`` instead of a placeholder value.
"""
import json
import statistics
from pathlib import Path
from typing import Dict, List, Optional

import structlog
from fastapi import APIRouter, Depends
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Approval, ApprovalStatus, Ticket, TicketStatus, WorkflowRun
from app.db.session import get_db
from app.graph.runner import _ACTIVE_RUNS

log = structlog.get_logger()
router = APIRouter()

REPO_ROOT = Path(__file__).resolve().parents[3]

CATEGORY_LABELS = {
    "refund": "Billing / Invoices",
    "credit": "Billing / Invoices",
    "invoice_question": "Billing / Invoices",
    "billing_contact": "Billing / Invoices",
    "plan_change": "Subscription Tiers",
    "seat_change": "Subscription Tiers",
    "access_request": "Access & Auth",
    "mfa_reset": "Access & Auth",
    "other": "Other",
}

INJECTION_FLAGS = {"prompt_injection_suspected", "injection_suspected"}


def _pct(numerator: int, denominator: int) -> Optional[float]:
    return round(numerator / denominator * 100, 1) if denominator > 0 else None


def _p95(values: List[float]) -> float:
    if len(values) >= 20:
        return statistics.quantiles(values, n=20)[-1]
    return max(values)


def _gateway_denials() -> int:
    try:
        from services.gateway.gateway import _audit_log
        return sum(1 for e in _audit_log if e.get("event") == "tool_call_denied")
    except Exception:
        return 0


async def _count(db: AsyncSession, model, *conditions) -> int:
    res = await db.execute(select(func.count(model.id)).where(*conditions))
    return res.scalar() or 0


@router.get("/analytics/overview")
async def analytics_overview(db: AsyncSession = Depends(get_db)):
    """Metrics across stored tickets/approvals and runs held in memory since startup."""
    total_tickets = await _count(db, Ticket)
    resolved_count = await _count(db, Ticket, Ticket.status == TicketStatus.resolved)
    escalated_count = await _count(db, Ticket, Ticket.status == TicketStatus.escalated)
    awaiting_count = await _count(db, Ticket, Ticket.status == TicketStatus.awaiting_approval)

    approval_counts = {
        st: await _count(db, Approval, Approval.status == st)
        for st in (
            ApprovalStatus.approved,
            ApprovalStatus.rejected,
            ApprovalStatus.escalated,
            ApprovalStatus.expired,
        )
    }
    approved = approval_counts[ApprovalStatus.approved]
    rejected = approval_counts[ApprovalStatus.rejected]

    # Run-derived metrics (in-memory runs prioritized; falls back to DB WorkflowRun)
    latencies: List[float] = []
    costs: List[float] = []
    injection_count = 0
    forbidden_count = 0
    for r in _ACTIVE_RUNS.values():
        for n in r.get("nodes", []):
            if n.get("node") == "plan_action" and n.get("duration_ms"):
                latencies.append(float(n["duration_ms"]))
        state = r.get("state", {})
        if INJECTION_FLAGS & set(state.get("flags", [])):
            injection_count += 1
        forbidden_count += sum(1 for d in state.get("policy_decisions", []) if d.get("tier") == "forbidden")
        if state.get("total_llm_cost_usd"):
            costs.append(float(state["total_llm_cost_usd"]))

    if not latencies:
        wf_res = await db.execute(select(WorkflowRun).order_by(WorkflowRun.started_at.desc()).limit(50))
        for wf in wf_res.scalars().all():
            nodes = wf.nodes_timeline or []
            for n in nodes:
                if isinstance(n, dict) and n.get("node") == "plan_action" and n.get("duration_ms"):
                    latencies.append(float(n["duration_ms"]))
            state = wf.state_json or {}
            if isinstance(state, dict):
                if INJECTION_FLAGS & set(state.get("flags", [])):
                    injection_count += 1
                forbidden_count += sum(
                    1 for d in state.get("policy_decisions", [])
                    if isinstance(d, dict) and d.get("tier") == "forbidden"
                )
                if state.get("total_llm_cost_usd"):
                    costs.append(float(state["total_llm_cost_usd"]))

    cat_res = await db.execute(
        select(
            Ticket.category,
            func.count(Ticket.id),
            func.sum(case((Ticket.status == TicketStatus.resolved, 1), else_=0)),
        ).group_by(Ticket.category)
    )
    grouped: Dict[str, Dict[str, int]] = {}
    for cat_enum, tot, auto in cat_res.all():
        cat_key = cat_enum.value if hasattr(cat_enum, "value") else str(cat_enum or "other")
        label = CATEGORY_LABELS.get(cat_key, "Other")
        bucket = grouped.setdefault(label, {"total": 0, "automated": 0})
        bucket["total"] += tot or 0
        bucket["automated"] += int(auto or 0)
    category_automation = [
        {"category": k, "total": v["total"], "automated": v["automated"], "rate": _pct(v["automated"], v["total"])}
        for k, v in grouped.items()
    ]

    approval_outcomes = [
        {"name": "Approved", "value": approved, "color": "#10b981"},
        {"name": "Rejected", "value": rejected, "color": "#ef4444"},
        {"name": "Escalated", "value": approval_counts[ApprovalStatus.escalated], "color": "#f59e0b"},
        {"name": "Expired", "value": approval_counts[ApprovalStatus.expired], "color": "#94a3b8"},
    ]

    return {
        "automation_rate": _pct(resolved_count, total_tickets),
        "approval_acceptance_rate": _pct(approved, approved + rejected),
        "escalation_rate": _pct(escalated_count, total_tickets),
        "median_proposal_latency_ms": round(statistics.median(latencies), 1) if latencies else None,
        "p95_proposal_latency_ms": round(_p95(latencies), 1) if latencies else None,
        "cost_per_ticket_usd": round(statistics.mean(costs), 6) if costs else None,
        "injection_attempt_count": injection_count,
        "blocked_actions": forbidden_count,
        "gateway_denials": _gateway_denials(),
        "total_tickets": total_tickets,
        "resolved_tickets": resolved_count,
        "awaiting_approval_count": awaiting_count,
        "category_automation": category_automation,
        "approval_outcomes": approval_outcomes,
        "runs_sampled": max(len(_ACTIVE_RUNS), len(latencies)),
    }


@router.get("/analytics/security")
async def analytics_security():
    """Security counters from in-memory runs and the gateway."""
    kill_switch_active = False
    try:
        from services.gateway import gateway
        kill_switch_active = gateway._kill_switch
    except Exception:
        pass

    injection_count = 0
    blocked_count = 0
    identity_unverified = 0
    for r in _ACTIVE_RUNS.values():
        state = r.get("state", {})
        if INJECTION_FLAGS & set(state.get("flags", [])):
            injection_count += 1
        blocked_count += sum(1 for d in state.get("policy_decisions", []) if d.get("tier") == "forbidden")
        if state.get("identity") and not state["identity"].get("verified", True):
            identity_unverified += 1

    return {
        "injection_attempts": injection_count,
        "blocked_actions": blocked_count,
        "identity_mismatches": identity_unverified,
        "gateway_denials": _gateway_denials(),
        "kill_switch_active": kill_switch_active,
    }


@router.get("/traces/{run_id}")
async def get_trace(run_id: str):
    """Execution trace for a run held in memory (cleared on restart)."""
    run = _ACTIVE_RUNS.get(run_id)
    if run:
        return run
    return {"run_id": run_id, "nodes": [], "status": "not_found"}


@router.get("/analytics/ragas")
async def get_ragas_metrics():
    """Latest RAG benchmark report from evals/reports/ragas_report.json (404-style payload if absent)."""
    report_file = REPO_ROOT / "evals" / "reports" / "ragas_report.json"
    if report_file.exists():
        try:
            with open(report_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            log.warning("ragas.report_unreadable", error=str(e))
    return {"status": "no_report", "message": "No RAG benchmark report found. Run the benchmark to generate one."}


@router.post("/analytics/ragas/run")
async def trigger_ragas_benchmark():
    """Run the RAG benchmark (evals/rag_benchmark.py) against the golden query set."""
    try:
        from evals.rag_benchmark import run_ragas_benchmark
        report = await run_ragas_benchmark()
        return {"status": "completed", "report": report}
    except Exception as e:
        log.error("ragas.benchmark.failed", error=str(e))
        return {"status": "error", "message": str(e)}
