import structlog
from app.graph.state import TicketState
log = structlog.get_logger()
async def gather_context_node(state: TicketState) -> dict:
    log.info('node.gather_context', ticket_id=state.get('ticket_id'))
    return {}
