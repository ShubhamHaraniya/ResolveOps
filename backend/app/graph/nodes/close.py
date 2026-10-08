import structlog
from app.graph.state import TicketState
log = structlog.get_logger()
async def close_node(state: TicketState) -> dict:
    log.info('node.close', ticket_id=state.get('ticket_id'))
    return {}
