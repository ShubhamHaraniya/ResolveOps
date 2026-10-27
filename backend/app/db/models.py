"""
SQLAlchemy ORM Models — all tables for ResolveOps.
Uses UUID primary keys and timestamped base mixin.
"""
import uuid
from datetime import datetime, UTC

from sqlalchemy import (
    Boolean, Column, DateTime, Enum, ForeignKey,
    Integer, String, Text, JSON, Index,
)
from sqlalchemy.orm import DeclarativeBase, relationship
import enum


class Base(DeclarativeBase):
    pass


def now_utc():
    return datetime.now(UTC)


def new_uuid():
    return str(uuid.uuid4())


# ─── Enums ─────────────────────────────────────────────────────────────────

class AccountPlan(str, enum.Enum):
    starter = "starter"
    pro = "pro"
    enterprise = "enterprise"
    enterprise_plus = "enterprise_plus"


class TicketStatus(str, enum.Enum):
    open = "open"
    in_progress = "in_progress"
    awaiting_approval = "awaiting_approval"
    resolved = "resolved"
    escalated = "escalated"
    closed = "closed"


class TicketCategory(str, enum.Enum):
    refund = "refund"
    credit = "credit"
    plan_change = "plan_change"
    seat_change = "seat_change"
    access_request = "access_request"
    mfa_reset = "mfa_reset"
    invoice_question = "invoice_question"
    billing_contact = "billing_contact"
    other = "other"


class TicketUrgency(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class ApprovalStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    escalated = "escalated"
    expired = "expired"
    invalidated = "invalidated"


class WorkflowStatus(str, enum.Enum):
    running = "running"
    awaiting_approval = "awaiting_approval"
    escalated = "escalated"
    done = "done"
    failed = "failed"


class AuditEvent(str, enum.Enum):
    received = "received"
    proposed = "proposed"
    policy_decision = "policy_decision"
    approval_requested = "approval_requested"
    approved = "approved"
    edited = "edited"
    rejected = "rejected"
    executed = "executed"
    verified = "verified"
    failed = "failed"
    escalated = "escalated"
    tool_call_start = "tool_call_start"
    tool_call_result = "tool_call_result"
    tool_call_denied = "tool_call_denied"


# ─── Core Business Data ────────────────────────────────────────────────────

class Account(Base):
    __tablename__ = "accounts"

    id = Column(String(64), primary_key=True, default=new_uuid)
    name = Column(String(255), nullable=False, index=True)
    plan = Column(Enum(AccountPlan), nullable=False, default=AccountPlan.starter)
    arr_cents = Column(Integer, nullable=False, default=0)  # Annual Recurring Revenue
    is_strategic = Column(Boolean, nullable=False, default=False)
    is_legal_hold = Column(Boolean, nullable=False, default=False)
    csm_owner = Column(String(255))
    status = Column(String(50), default="active")
    created_at = Column(DateTime(timezone=True), default=now_utc)
    updated_at = Column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)

    contacts = relationship("Contact", back_populates="account")
    subscriptions = relationship("Subscription", back_populates="account")
    invoices = relationship("Invoice", back_populates="account")
    tickets = relationship("Ticket", back_populates="account")


class Contact(Base):
    __tablename__ = "contacts"

    id = Column(String(64), primary_key=True, default=new_uuid)
    account_id = Column(String(64), ForeignKey("accounts.id"), nullable=False)
    email = Column(String(255), nullable=False, index=True)
    name = Column(String(255))
    is_authorized = Column(Boolean, nullable=False, default=False)
    role = Column(String(100), default="user")
    created_at = Column(DateTime(timezone=True), default=now_utc)
    updated_at = Column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)

    account = relationship("Account", back_populates="contacts")

    __table_args__ = (Index("ix_contacts_account_email", "account_id", "email"),)


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(String(64), primary_key=True, default=new_uuid)
    account_id = Column(String(64), ForeignKey("accounts.id"), nullable=False)
    plan = Column(Enum(AccountPlan), nullable=False)
    seats = Column(Integer, default=1)
    status = Column(String(50), default="active")
    current_period_end = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=now_utc)
    updated_at = Column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)

    account = relationship("Account", back_populates="subscriptions")
    invoices = relationship("Invoice", back_populates="subscription")


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(String(64), primary_key=True, default=new_uuid)
    account_id = Column(String(64), ForeignKey("accounts.id"), nullable=False)
    subscription_id = Column(String(64), ForeignKey("subscriptions.id"))
    amount_cents = Column(Integer, nullable=False)
    status = Column(String(50), default="paid")  # paid, unpaid, disputed
    invoice_date = Column(DateTime(timezone=True), default=now_utc)
    created_at = Column(DateTime(timezone=True), default=now_utc)

    account = relationship("Account", back_populates="invoices")
    subscription = relationship("Subscription", back_populates="invoices")


# ─── Ticketing ─────────────────────────────────────────────────────────────

class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(String(64), primary_key=True, default=new_uuid)
    account_id = Column(String(64), ForeignKey("accounts.id"))
    requester_email = Column(String(255), nullable=False, index=True)
    subject = Column(String(500), nullable=False)
    body_html = Column(Text)
    category = Column(Enum(TicketCategory))
    urgency = Column(Enum(TicketUrgency), default=TicketUrgency.medium)
    sentiment = Column(String(50))
    status = Column(Enum(TicketStatus), default=TicketStatus.open)
    risk_flags = Column(JSON, default=list)  # ["injection_suspected", "identity_mismatch"]
    created_at = Column(DateTime(timezone=True), default=now_utc)
    updated_at = Column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)

    account = relationship("Account", back_populates="tickets")
    messages = relationship("TicketMessage", back_populates="ticket")
    runs = relationship("WorkflowRun", back_populates="ticket")


class TicketMessage(Base):
    __tablename__ = "ticket_messages"

    id = Column(String(64), primary_key=True, default=new_uuid)
    ticket_id = Column(String(64), ForeignKey("tickets.id"), nullable=False)
    author = Column(String(255))
    body = Column(Text)
    is_internal = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=now_utc)

    ticket = relationship("Ticket", back_populates="messages")


# ─── Workflow ──────────────────────────────────────────────────────────────

class WorkflowRun(Base):
    __tablename__ = "workflow_runs"

    id = Column(String(64), primary_key=True, default=new_uuid)
    ticket_id = Column(String(64), ForeignKey("tickets.id"), nullable=False)
    status = Column(Enum(WorkflowStatus), default=WorkflowStatus.running)
    started_at = Column(DateTime(timezone=True), default=now_utc)
    completed_at = Column(DateTime(timezone=True))
    error = Column(Text)
    langfuse_trace_id = Column(String(255))
    nodes_timeline = Column(JSON, default=list)
    state_json = Column(JSON, default=dict)

    ticket = relationship("Ticket", back_populates="runs")
    approvals = relationship("Approval", back_populates="run")


# ─── Approvals ─────────────────────────────────────────────────────────────

class Approval(Base):
    __tablename__ = "approvals"

    id = Column(String(64), primary_key=True, default=new_uuid)
    run_id = Column(String(64), ForeignKey("workflow_runs.id"), nullable=False)
    ticket_id = Column(String(64), ForeignKey("tickets.id"), nullable=False)
    tool = Column(String(255), nullable=False)
    args_hash = Column(String(64), nullable=False)  # SHA256(tool:sorted_json(args))
    args_redacted = Column(JSON)
    args_normalized = Column(JSON)  # full args for hash validation
    policy_rule = Column(String(50))
    approver_role = Column(String(100))
    status = Column(Enum(ApprovalStatus), default=ApprovalStatus.pending)
    created_at = Column(DateTime(timezone=True), default=now_utc)
    expires_at = Column(DateTime(timezone=True))  # created_at + 24h
    reviewed_at = Column(DateTime(timezone=True))
    reviewer_id = Column(String(255))
    edit_reason = Column(Text)

    run = relationship("WorkflowRun", back_populates="approvals")

    __table_args__ = (Index("ix_approvals_ticket_status", "ticket_id", "status"),)


# ─── Audit Log (append-only) ───────────────────────────────────────────────

class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(String(64), primary_key=True, default=new_uuid)
    timestamp = Column(DateTime(timezone=True), default=now_utc, nullable=False)
    run_id = Column(String(255))
    ticket_id = Column(String(255), index=True)
    actor_type = Column(String(50))   # agent, human, system
    actor_id = Column(String(255))
    event = Column(Enum(AuditEvent), nullable=False)
    tool = Column(String(255))
    args_hash = Column(String(64))
    args_redacted = Column(JSON)
    policy_rule = Column(String(50))
    policy_version = Column(Integer)
    idempotency_key = Column(String(255))
    result_status = Column(String(50))
    trace_id = Column(String(255))
    prev_hash = Column(String(64))   # Hash chain: previous row's row_hash
    row_hash = Column(String(64))    # SHA256(prev_hash + row content)

    __table_args__ = (
        Index("ix_audit_log_ticket", "ticket_id"),
        Index("ix_audit_log_timestamp", "timestamp"),
        Index("ix_audit_log_event", "event"),
    )


