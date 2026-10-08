"""Analytics API router."""
from fastapi import APIRouter
router = APIRouter()

@router.get("/analytics/overview")
async def analytics_overview():
    return {
        "automation_rate": None,
        "approval_acceptance_rate": None,
        "median_proposal_latency_ms": None,
        "p95_proposal_latency_ms": None,
        "unsafe_action_rate": None,
        "duplicate_side_effect_rate": None,
        "cost_per_ticket_usd": None,
        "escalation_rate": None,
        "injection_attempt_count": 0,
    }

@router.get("/analytics/security")
async def analytics_security():
    return {
        "injection_attempts": 0,
        "blocked_actions": 0,
        "identity_mismatches": 0,
        "forbidden_tool_requests": 0,
        "gateway_denials": 0,
        "kill_switch_active": False,
    }

@router.get("/traces/{run_id}")
async def get_trace(run_id: str):
    return {"run_id": run_id, "nodes": [], "status": "not_found"}
