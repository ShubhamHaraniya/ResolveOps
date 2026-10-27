"""
backend/app/mapping.py
Shared mapping of free-form category / priority strings onto the stored enums.
"""
from typing import Optional

from app.db.models import TicketCategory, TicketUrgency

_CATEGORY_MAP = {
    "refund": TicketCategory.refund,
    "refund_request": TicketCategory.refund,
    "credit": TicketCategory.credit,
    "plan_change": TicketCategory.plan_change,
    "seat_change": TicketCategory.seat_change,
    "access_request": TicketCategory.access_request,
    "mfa_reset": TicketCategory.mfa_reset,
    "invoice_question": TicketCategory.invoice_question,
    "billing_inquiry": TicketCategory.invoice_question,
    "billing_contact": TicketCategory.billing_contact,
}

_URGENCY_MAP = {
    "low": TicketUrgency.low,
    "medium": TicketUrgency.medium,
    "normal": TicketUrgency.medium,
    "high": TicketUrgency.high,
    "critical": TicketUrgency.critical,
    "urgent": TicketUrgency.critical,
}


def map_category(value: Optional[str]) -> TicketCategory:
    """Unknown or empty values map to ``TicketCategory.other``."""
    return _CATEGORY_MAP.get((value or "").lower().strip(), TicketCategory.other)


def map_urgency(value: Optional[str]) -> TicketUrgency:
    """Unknown or empty values map to ``TicketUrgency.medium``."""
    return _URGENCY_MAP.get((value or "").lower().strip(), TicketUrgency.medium)
