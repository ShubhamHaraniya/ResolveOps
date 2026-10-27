"""
LLM output schemas — Pydantic models for Groq structured outputs.
All models use strict JSON mode (no loose fields).
"""
from typing import Literal, Optional, Any
from pydantic import BaseModel, Field


class TokenUsage(BaseModel):
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0


class LLMCallResult(BaseModel):
    result: Any
    usage: TokenUsage
    latency_ms: float = 0.0
    model: str
    call_id: str


class Classification(BaseModel):
    """Ticket classification result."""
    category: Literal[
        "refund_request",
        "billing_inquiry",
        "access_request",
        "plan_change",
        "technical_support",
        "account_information",
        "general_inquiry",
        "complaint",
        "other",
    ]
    urgency: Literal["critical", "high", "medium", "low"]
    sentiment: Literal["positive", "neutral", "frustrated", "angry"]
    confidence: float = Field(ge=0.0, le=1.0, description="0-1 classification confidence")
    human_review_required: bool = Field(
        default=False,
        description="True if ticket is ambiguous, sensitive, or has injection signals"
    )
    brief_reason: str = Field(max_length=200, description="One-line reason for classification")


class RAGCitation(BaseModel):
    """Citation from a policy document."""
    document_id: str
    version: int
    section: str
    excerpt: str = Field(max_length=500)
    relevance_score: float = Field(ge=0.0, le=1.0)


class ProposedAction(BaseModel):
    """A single proposed tool call."""
    tool: str = Field(description="Tool name from approved registry, e.g. billing.issue_refund")
    arguments: dict = Field(description="Tool arguments as a flat dict with snake_case keys")
    reason: str = Field(max_length=200, description="Brief reason for proposing this action")
    risk_level: Literal["low", "medium", "high", "critical"] = Field(default="low")


class ProposedResolution(BaseModel):
    """Complete proposed resolution for a ticket."""
    actions: list[ProposedAction] = Field(
        default_factory=list,
        max_length=5,
        description="Ordered list of proposed tool calls (max 5)"
    )
    rag_citations: list[RAGCitation] = Field(
        default_factory=list,
        max_length=3,
        description="Policy citations supporting this proposal"
    )
    draft_reply: str = Field(
        default="",
        max_length=1000,
        description="Draft customer reply (will be reviewed before sending)"
    )
    risk_flags: list[str] = Field(
        default_factory=list,
        description="Risk signals: injection_suspected, legal_hold, strategic_account, etc."
    )
    reasoning_summary: str = Field(
        max_length=500,
        description="Internal explanation of why these actions were chosen"
    )
    clarification_needed: bool = Field(
        default=False,
        description="True if more information is needed before acting"
    )
    clarification_question: Optional[str] = Field(
        default=None,
        max_length=300,
        description="If clarification_needed, what question to ask the customer"
    )


class IdentityResult(BaseModel):
    """Result of identity verification (deterministic — not LLM)."""
    verified: bool
    method: Literal[
        "crm_authorized_contact",
        "crm_lookup",
        "crm_error",
        "crm_unavailable",
        "none",
    ]
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str
    authorized_contact_match: bool
    requester_email: str
    account_id: Optional[str] = None
