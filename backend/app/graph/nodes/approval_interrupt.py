import structlog
from app.graph.state import TicketState
log = structlog.get_logger()
async def approval_interrupt_node(state: TicketState) -> dict:
    log.info('node.approval_interrupt', ticket_id=state.get('ticket_id'))
    return {}
