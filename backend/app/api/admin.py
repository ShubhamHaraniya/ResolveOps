"""Admin endpoints: global kill switch for policy-gateway tool execution.

The switch lives in the memory of the backend process (the gateway is in-process), so it
resets on restart and is not shared between multiple workers. These endpoints have no
authentication (the REST API has none) - do not expose them publicly.
"""
import structlog
from fastapi import APIRouter
from pydantic import BaseModel

from services.gateway import gateway

router = APIRouter()
log = structlog.get_logger()


class KillSwitchState(BaseModel):
    active: bool


@router.get("/admin/kill-switch", response_model=KillSwitchState)
async def get_kill_switch():
    return KillSwitchState(active=gateway.kill_switch_active())


@router.post("/admin/kill-switch", response_model=KillSwitchState)
async def set_kill_switch(body: KillSwitchState):
    return KillSwitchState(active=gateway.set_kill_switch(body.active))
