"""
SQLAlchemy ORM Models — all tables for ResolveOps.
Uses UUID primary keys and timestamped base mixin.
"""
import uuid
from datetime import datetime, UTC

from sqlalchemy import (
    Boolean, Column, DateTime, Enum, Float, ForeignKey,
    Integer, String, Text, JSON, Index, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
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


class PolicyTier(str, enum.Enum):
    auto = "auto"
    approval = "approval"
    forbidden = "forbidden"


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


class AccessRole(str, enum.Enum):
    viewer = "viewer"
    member = "member"
    # admin and prod-admin are deliberately NOT included


class AuditEvent(str, enum.Enum):
    proposed = "proposed"
    policy_decision = "policy_decision"
    approval_requested = "approval_requested"
    approved = "approved"
    edited = "edited"
    rejected = "rejected"
    executed = "executed"
    verified = "verified"
    failed = "failed"
    compensated = "compensated"
    escalated = "escalated"


# ─── Core Business Data ────────────────────────────────────────────────────

class Account(Base):
    __tablename__ = "accounts"

    id = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
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

    id = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    account_id = Column(UUID(as_uuid=False), ForeignKey("accounts.id"), nullable=False)
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

    id = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    account_id = Column(UUID(as_uuid=False), ForeignKey("accounts.id"), nullable=False)
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

    id = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    account_id = Column(UUID(as_uuid=False), ForeignKey("accounts.id"), nullable=False)
    subscription_id = Column(UUID(as_uuid=False), ForeignKey("subscriptions.id"))
    amount_cents = Column(Integer, nullable=False)
    status = Column(String(50), default="paid")  # paid, unpaid, disputed
    invoice_date = Column(DateTime(timezone=True), default=now_utc)
    created_at = Column(DateTime(timezone=True), default=now_utc)

    account = relationship("Account", back_populates="invoices")
    subscription = relationship("Subscription", back_populates="invoices")
    refunds = relationship("Refund", back_populates="invoice")


class Refund(Base):
    __tablename__ = "refunds"

    id = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    invoice_id = Column(UUID(as_uuid=False), ForeignKey("invoices.id"), nullable=False)
    amount_cents = Column(Integer, nullable=False)
    reason = Column(String(100), nullable=False)
    idempotency_key = Column(String(255), unique=True, nullable=False)
    status = Column(String(50), default="completed")
    created_at = Column(DateTime(timezone=True), default=now_utc)

    invoice = relationship("Invoice", back_populates="refunds")

    __table_args__ = (Index("ix_refunds_idempotency", "idempotency_key"),)


class Credit(Base):
    __tablename__ = "credits"

    id = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    account_id = Column(UUID(as_uuid=False), ForeignKey("accounts.id"), nullable=False)
    amount_cents = Column(Integer, nullable=False)
    reason = Column(String(255))
    idempotency_key = Column(String(255), unique=True, nullable=False)
    status = Column(String(50), default="active")
    created_at = Column(DateTime(timezone=True), default=now_utc)

    __table_args__ = (Index("ix_credits_idempotency", "idempotency_key"),)


class AccessGrant(Base):
    __tablename__ = "access_grants"

    id = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    account_id = Column(UUID(as_uuid=False), ForeignKey("accounts.id"), nullable=False)
    user_email = Column(String(255), nullable=False)
    role = Column(Enum(AccessRole), nullable=False)
    granted_by = Column(String(255))
    expires_at = Column(DateTime(timezone=True))
    status = Column(String(50), default="active")
    created_at = Column(DateTime(timezone=True), default=now_utc)


# ─── Ticketing ─────────────────────────────────────────────────────────────

class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    account_id = Column(UUID(as_uuid=False), ForeignKey("accounts.id"))
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

    id = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    ticket_id = Column(UUID(as_uuid=False), ForeignKey("tickets.id"), nullable=False)
    author = Column(String(255))
    body = Column(Text)
    is_internal = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=now_utc)

    ticket = relationship("Ticket", back_populates="messages")


# ─── Workflow ──────────────────────────────────────────────────────────────

class WorkflowRun(Base):
    __tablename__ = "workflow_runs"

    id = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    ticket_id = Column(UUID(as_uuid=False), ForeignKey("tickets.id"), nullable=False)
    status = Column(Enum(WorkflowStatus), default=WorkflowStatus.running)
    started_at = Column(DateTime(timezone=True), default=now_utc)
    completed_at = Column(DateTime(timezone=True))
    error = Column(Text)
    langfuse_trace_id = Column(String(255))

    ticket = relationship("Ticket", back_populates="runs")
    tool_calls = relationship("ToolCall", back_populates="run")
    policy_decisions = relationship("PolicyDecisionRecord", back_populates="run")
    approvals = relationship("Approval", back_populates="run")


class ToolCall(Base):
    __tablename__ = "tool_calls"

    id = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    run_id = Column(UUID(as_uuid=False), ForeignKey("workflow_runs.id"), nullable=False)
    tool = Column(String(255), nullable=False)
    args_hash = Column(String(64))  # SHA256
    args_redacted = Column(JSON)
    result_status = Column(String(50))  # success, failed, idempotent_skip
    latency_ms = Column(Float)
    created_at = Column(DateTime(timezone=True), default=now_utc)

    run = relationship("WorkflowRun", back_populates="tool_calls")


# ─── Policy ────────────────────────────────────────────────────────────────

class PolicyVersion(Base):
    __tablename__ = "policy_versions"

    id = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    document_id = Column(String(255), nullable=False)
    version = Column(Integer, nullable=False)
    status = Column(String(50), default="active")  # active, deprecated
    effective_date = Column(DateTime(timezone=True))
    loaded_at = Column(DateTime(timezone=True), default=now_utc)

    __table_args__ = (UniqueConstraint("document_id", "version"),)


class PolicyDecisionRecord(Base):
    __tablename__ = "policy_decisions"

    id = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    run_id = Column(UUID(as_uuid=False), ForeignKey("workflow_runs.id"), nullable=False)
    tool = Column(String(255))
    tier = Column(Enum(PolicyTier))
    rule_id = Column(String(50))
    reason = Column(Text)
    created_at = Column(DateTime(timezone=True), default=now_utc)

    run = relationship("WorkflowRun", back_populates="policy_decisions")


# ─── Approvals ─────────────────────────────────────────────────────────────

class Approval(Base):
    __tablename__ = "approvals"

    id = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    run_id = Column(UUID(as_uuid=False), ForeignKey("workflow_runs.id"), nullable=False)
    ticket_id = Column(UUID(as_uuid=False), ForeignKey("tickets.id"), nullable=False)
    tool = Column(String(255), nullable=False)
    args_hash = Column(String(64), nullable=False)  # SHA256(ticket_id:tool:sorted_args)
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

    id = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
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


# ─── Evaluation ────────────────────────────────────────────────────────────

class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"

    id = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    scenario_id = Column(String(50), nullable=False)
    run_number = Column(Integer, nullable=False)
    result = Column(String(50))  # pass, fail
    unsafe_action = Column(Boolean, default=False)
    duplicate_effect = Column(Boolean, default=False)
    actual_tier = Column(String(50))
    expected_tier = Column(String(50))
    latency_ms = Column(Float)
    details = Column(JSON)
    created_at = Column(DateTime(timezone=True), default=now_utc)


class ScenarioResult(Base):
    __tablename__ = "scenario_results"

    id = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    scenario_id = Column(String(50), nullable=False, index=True)
    total_runs = Column(Integer, default=0)
    pass_count = Column(Integer, default=0)
    fail_count = Column(Integer, default=0)
    unsafe_count = Column(Integer, default=0)
    pass_rate = Column(Float)
    last_run_at = Column(DateTime(timezone=True))


# ─── Reliability ───────────────────────────────────────────────────────────

class OutboxEvent(Base):
    __tablename__ = "outbox_events"

    id = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    event_type = Column(String(100), nullable=False)
    payload = Column(JSON, nullable=False)
    status = Column(String(50), default="pending")  # pending, processed, failed
    created_at = Column(DateTime(timezone=True), default=now_utc)
    processed_at = Column(DateTime(timezone=True))

    __table_args__ = (Index("ix_outbox_status", "status"),)


class IdempotencyRecord(Base):
    __tablename__ = "idempotency_records"

    id = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    key = Column(String(64), unique=True, nullable=False)  # SHA256 hash
    tool = Column(String(255))
    result = Column(JSON)
    result_status = Column(String(50))
    created_at = Column(DateTime(timezone=True), default=now_utc)

    __table_args__ = (Index("ix_idempotency_key", "key"),)
