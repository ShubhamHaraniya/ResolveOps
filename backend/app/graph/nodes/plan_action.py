import structlog
from app.graph.state import TicketState
log = structlog.get_logger()
async def plan_action_node(state: TicketState) -> dict:
    log.info('node.plan_action', ticket_id=state.get('ticket_id'))
    return {}
