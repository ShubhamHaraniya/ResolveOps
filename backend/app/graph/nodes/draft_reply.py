import structlog
from app.graph.state import TicketState
log = structlog.get_logger()
async def draft_reply_node(state: TicketState) -> dict:
    log.info('node.draft_reply', ticket_id=state.get('ticket_id'))
    return {}
