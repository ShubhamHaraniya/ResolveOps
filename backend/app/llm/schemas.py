"""
LLM Output Schemas — All Pydantic models for structured Groq responses.
All workflow-critical decisions use these schemas (never free-form text).
"""
from typing import Any, Literal
from pydantic import BaseModel, Field


class Classification(BaseModel):
    """Output of classify_ticket() using GROQ_MODEL_FAST."""
    category: Literal[
        "refund", "credit", "plan_change", "seat_change",
        "access_request", "mfa_reset", "invoice_question",
        "billing_contact", "other"
    ]
    urgency: Literal["low", "medium", "high", "critical"]
    sentiment: Literal["positive", "neutral", "frustrated", "angry"]
    confidence: float = Field(ge=0.0, le=1.0)
    human_review_required: bool  # True if confidence < 0.7
    brief_reason: str = Field(max_length=200)


class IdentityResult(BaseModel):
    """Result of deterministic identity verification (NOT LLM-generated)."""
    verified: bool
    method: str
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str
    authorized_contact_match: bool
    requester_email: str
    account_id: str | None = None


class RAGCitation(BaseModel):
    """A single retrieved policy chunk with full provenance."""
    chunk_id: str
    document_id: str
    version: int
    section: str
    content: str
    relevance_score: float = Field(ge=0.0, le=1.0)
    status: Literal["active", "deprecated"]
    effective_date: str | None = None


class ProposedAction(BaseModel):
    """A single typed action proposed by the planning LLM."""
    tool: str = Field(description="Exact tool name: e.g. billing.issue_refund")
    arguments: dict[str, Any] = Field(
        description="Typed arguments. All IDs must come from trusted context, not invented."
    )
    reason: str = Field(max_length=500)
    risk_level: Literal["low", "medium", "high"]


class PolicyDecisionLLM(BaseModel):
    """Policy decision as part of proposal (informational — actual decision from engine)."""
    tier: Literal["auto", "approval", "forbidden"]
    rule_id: str
    reason: str


class ProposedResolution(BaseModel):
    """
    Full structured proposal from plan_action() using GROQ_MODEL_PRIMARY.
    This is a PROPOSAL only — gateway makes final authorization decision.
    """
    actions: list[ProposedAction] = Field(
        max_length=5,
        description="Proposed actions. Max 5. Must not include forbidden operations."
    )
    rag_citations: list[RAGCitation] = Field(
        default_factory=list,
        description="Policy chunks used to inform the proposal."
    )
    draft_reply: str = Field(
        max_length=2000,
        description="Draft customer reply. Uses only verified facts. No invented promises."
    )
    risk_flags: list[str] = Field(
        default_factory=list,
        description="e.g. ['injection_suspected', 'identity_mismatch', 'strategic_account']"
    )
    reasoning_summary: str = Field(
        max_length=500,
        description="Brief operational reasoning. NOT full chain-of-thought."
    )
    clarification_needed: bool = False
    clarification_question: str | None = None


class TokenUsage(BaseModel):
    """Token usage tracking for cost estimation."""
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost_usd: float | None = None


class LLMCallResult(BaseModel):
    """Wrapper for any LLM call result with usage tracking."""
    result: Any
    usage: TokenUsage
    latency_ms: float
    model: str
    call_id: str
