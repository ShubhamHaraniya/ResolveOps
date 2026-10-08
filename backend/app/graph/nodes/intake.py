import structlog
from app.graph.state import TicketState
log = structlog.get_logger()
async def intake_node(state: TicketState) -> dict:
    log.info('node.intake', ticket_id=state.get('ticket_id'))
    return {}
