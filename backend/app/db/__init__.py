"""DB package: importing it registers every model on ``Base.metadata``."""
from app.db.models import (  # noqa: F401
    Base,
    Account, Contact, Subscription, Invoice,
    Ticket, TicketMessage, WorkflowRun, Approval, AuditLog,
)

__all__ = ["Base"]
