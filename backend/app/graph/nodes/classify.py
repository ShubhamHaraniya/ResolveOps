import structlog
from app.graph.state import TicketState
log = structlog.get_logger()
async def classify_node(state: TicketState) -> dict:
    log.info('node.classify', ticket_id=state.get('ticket_id'))
    return {}
