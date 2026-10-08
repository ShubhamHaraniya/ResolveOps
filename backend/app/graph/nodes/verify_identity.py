import structlog
from app.graph.state import TicketState
log = structlog.get_logger()
async def verify_identity_node(state: TicketState) -> dict:
    log.info('node.verify_identity', ticket_id=state.get('ticket_id'))
    return {}
