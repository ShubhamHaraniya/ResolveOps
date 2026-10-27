"""
backend/app/api/runs.py
Runs API router for querying live LangGraph workflow run state.

Runs come from two places: runs held in memory by this process (freshest) and the
``workflow_runs`` table. Values that are not tracked (for example token counts) are
returned as ``null`` rather than estimated.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Ticket, WorkflowRun
from app.db.session import get_db
from app.graph.runner import _ACTIVE_RUNS, get_run

router = APIRouter()

# Nodes that call the LLM; every other node is deterministic.
LLM_NODES = {"classify", "plan_action"}


def _parse(ts: Optional[str]) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(ts) if ts else None
    except ValueError:
        return None


def _duration_ms(started: Optional[str], ended: Optional[str]) -> Optional[int]:
    s, e = _parse(started), _parse(ended)
    if s and e:
        return int((e - s).total_seconds() * 1000)
    return None


def _node_view(idx: int, node: Dict[str, Any]) -> Dict[str, Any]:
    key = node.get("node") or node.get("name") or f"node_{idx + 1}"
    latency = node.get("duration_ms")
    return {
        "id": node.get("id") or f"n-{idx + 1}",
        "name": key,
        "display_name": node.get("name") or key,
        "status": node.get("status", "pending"),
        "latency_ms": int(latency) if latency is not None else None,
        "provider": "Groq" if key in LLM_NODES else "Deterministic",
        "error": node.get("error"),
    }


def _run_view(
    run_id: str,
    ticket_id: Optional[str],
    subject: Optional[str],
    status: str,
    started_at: Optional[str],
    ended_at: Optional[str],
    nodes: List[Dict[str, Any]],
    state: Dict[str, Any],
    error: Optional[str] = None,
    trace_id: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "run_id": run_id,
        "ticket_id": ticket_id,
        "ticket_number": f"TCK-{ticket_id[:8].upper()}" if ticket_id else None,
        "subject": subject,
        "status": status,
        "started_at": started_at,
        "ended_at": ended_at,
        "total_duration_ms": _duration_ms(started_at, ended_at),
        "total_tokens": None,  # token usage is not aggregated per run
        "total_cost": state.get("total_llm_cost_usd"),
        "llm_calls": state.get("total_llm_calls"),
        "langfuse_trace_id": trace_id or state.get("langfuse_trace_id"),
        "error": error,
        "nodes": [_node_view(i, n) for i, n in enumerate(nodes)],
    }


def _status_str(status: Any) -> str:
    return status.value if hasattr(status, "value") else str(status)


@router.get("/runs")
async def list_runs(limit: int = 20, db: AsyncSession = Depends(get_db)):
    """List workflow runs (in-memory runs first, then stored runs), newest first."""
    runs: Dict[str, Dict[str, Any]] = {}

    res = await db.execute(select(WorkflowRun).order_by(desc(WorkflowRun.started_at)).limit(limit))
    db_runs = res.scalars().all()
    subjects: Dict[str, str] = {}
    ticket_ids = {r.ticket_id for r in db_runs if r.ticket_id}
    ticket_ids |= {r.get("ticket_id") for r in _ACTIVE_RUNS.values() if r.get("ticket_id")}
    if ticket_ids:
        t_res = await db.execute(select(Ticket.id, Ticket.subject).where(Ticket.id.in_(ticket_ids)))
        subjects = {tid: subj for tid, subj in t_res.all()}

    for r in db_runs:
        state = r.state_json or {}
        runs[r.id] = _run_view(
            r.id, r.ticket_id, subjects.get(r.ticket_id), _status_str(r.status),
            r.started_at.isoformat() if r.started_at else None,
            r.completed_at.isoformat() if r.completed_at else None,
            r.nodes_timeline or [], state, r.error, r.langfuse_trace_id,
        )

    # In-memory runs are fresher than the persisted copy; they override it.
    for run_id, active in _ACTIVE_RUNS.items():
        runs[run_id] = _run_view(
            run_id, active.get("ticket_id"), subjects.get(active.get("ticket_id")), active.get("status", "running"),
            active.get("started_at"), active.get("completed_at"),
            active.get("nodes", []), active.get("state", {}), active.get("error"),
        )

    results = sorted(runs.values(), key=lambda r: r.get("started_at") or "", reverse=True)[:limit]
    return {"runs": results, "total": len(results)}


@router.get("/runs/{run_id}")
async def get_run_status(run_id: str, db: AsyncSession = Depends(get_db)):
    """Return live execution state and node timeline for a workflow run."""
    run = get_run(run_id)
    if run:
        return run

    res = await db.execute(select(WorkflowRun).where(WorkflowRun.id == run_id))
    r = res.scalars().first()
    if not r:
        raise HTTPException(status_code=404, detail="Run not found")

    return {
        "run_id": r.id,
        "ticket_id": r.ticket_id,
        "status": _status_str(r.status),
        "started_at": r.started_at.isoformat() if r.started_at else None,
        "completed_at": r.completed_at.isoformat() if r.completed_at else None,
        "error": r.error,
        "nodes": r.nodes_timeline or [],
        "state": r.state_json or {},
    }
