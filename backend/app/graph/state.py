"""
LangGraph TicketState — the single source of truth for a workflow run.
All nodes read from and write to this state.
Postgres-checkpointed for crash recovery.
"""
from typing import TypedDict, Literal, Any


class TicketState(TypedDict, total=False):
    # ── Input ──────────────────────────────────────────────────
    ticket_id: str
    run_id: str
    raw_ticket: dict                    # Raw ticket from ticketing mock

    # ── Classification ─────────────────────────────────────────
    classification: dict | None         # Classification schema

    # ── Identity ───────────────────────────────────────────────
    identity: dict | None               # IdentityResult schema

    # ── Context ────────────────────────────────────────────────
    context: dict | None                # {account, contacts, invoices, subscriptions, rag_results}

    # ── Proposal ───────────────────────────────────────────────
    proposal: dict | None               # ProposedResolution schema

    # ── Policy ─────────────────────────────────────────────────
    policy_decisions: list[dict]        # List of PolicyDecision

    # ── Approval ───────────────────────────────────────────────
    approval: dict | None               # ApprovalRecord (from DB)
    approval_id: str | None

    # ── Execution ──────────────────────────────────────────────
    executed: list[dict]                # List of ExecutedAction results
    compensations: list[dict]           # List of Compensation records (saga)

    # ── Control ────────────────────────────────────────────────
    flags: list[str]                    # ["injection_suspected", "identity_mismatch", ...]
    attempts: dict[str, int]            # Retry counters per node name
    status: Literal[
        "running",
        "awaiting_approval",
        "escalated",
        "done",
        "failed",
    ]
    error: str | None
    escalation_reason: str | None

    # ── Cost / Observability ───────────────────────────────────
    total_llm_cost_usd: float
    total_tool_calls: int
    total_llm_calls: int
    replans: int
    langfuse_trace_id: str | None
