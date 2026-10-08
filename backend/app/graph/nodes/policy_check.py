import structlog
from app.graph.state import TicketState
log = structlog.get_logger()
async def policy_check_node(state: TicketState) -> dict:
    log.info('node.policy_check', ticket_id=state.get('ticket_id'))
    return {}
