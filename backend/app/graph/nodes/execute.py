import structlog
from app.graph.state import TicketState
log = structlog.get_logger()
async def execute_node(state: TicketState) -> dict:
    log.info('node.execute', ticket_id=state.get('ticket_id'))
    return {}
