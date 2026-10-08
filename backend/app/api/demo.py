"""Demo mode API router — seed and run demo scenarios."""
from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel

router = APIRouter()

DEMO_SCENARIOS = {
    "normal_refund": "Normal refund — duplicate charge, $30, verified requester",
    "prompt_injection": "Prompt injection — SYSTEM OVERRIDE ticket",
    "wrong_requester": "Wrong requester — attacker@gmail.com targeting Acme Corp",
    "admin_access": "Admin access request — FORBIDDEN",
    "billing_timeout": "Billing timeout-after-commit — read-back verification",
    "stale_approval": "Stale approval — account state changes before use",
}


@router.get("/demo/scenarios")
async def list_scenarios():
    return {
        "scenarios": [
            {"id": k, "description": v} for k, v in DEMO_SCENARIOS.items()
        ]
    }


@router.post("/demo/scenarios/{scenario_id}")
async def run_scenario(scenario_id: str, background_tasks: BackgroundTasks):
    """Seed data and trigger a demo scenario run."""
    if scenario_id not in DEMO_SCENARIOS:
        return {"error": f"Unknown scenario: {scenario_id}"}
    # TODO: seed scenario data and trigger workflow run
    return {
        "scenario_id": scenario_id,
        "description": DEMO_SCENARIOS[scenario_id],
        "status": "triggered",
        "ticket_id": "stub",
        "run_id": "stub",
    }
