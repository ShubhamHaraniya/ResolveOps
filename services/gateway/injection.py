"""
services/gateway/injection.py
Prompt injection detection layer.

IMPORTANT: Detection NEVER blocks — it flags.
The policy engine and identity checks block.
Injection detection provides signal for human review and risk scoring.

Detection strategy: deterministic keyword/pattern matching (no LLM).
LLM-based detection would be ironic and unreliable.
"""
import re
from dataclasses import dataclass, field


@dataclass
class InjectionResult:
    suspected: bool
    confidence: float  # 0.0 - 1.0
    patterns_matched: list[str] = field(default_factory=list)
    risk_score: float = 0.0


# Patterns that strongly indicate injection attempts
INJECTION_PATTERNS: list[tuple[str, float, str]] = [
    # (pattern_regex, confidence_weight, label)
    (r"(?i)system\s*override", 0.95, "system_override_claim"),
    (r"(?i)ignore\s+(previous|all|prior|your)\s+instructions", 0.95, "ignore_instructions"),
    (r"(?i)ignore\s+(company|security|refund|billing)\s+polic(y|ies)", 0.90, "ignore_policy"),
    (r"(?i)(pre-?authorized|pre-?approved)\s+by\s+(ceo|cfo|finance|management)", 0.85, "false_authority_claim"),
    (r"(?i)you\s+are\s+now\s+in\s+(admin|root|superuser|god)\s+mode", 0.95, "privilege_escalation"),
    (r"(?i)bypass\s+(security|policy|check|restriction|gateway)", 0.90, "bypass_request"),
    (r"(?i)force\s+(execute|run|apply|refund|credit)", 0.80, "force_execute"),
    (r"(?i)this\s+(has\s+been|is)\s+(already\s+)?approved\s+by\s+(ceo|finance|legal)", 0.85, "false_approval_claim"),
    (r"(?i)grant\s+(me\s+)?(admin|root|superuser|full)\s+access", 0.85, "admin_access_request"),
    (r"(?i)your\s+true\s+role\s+is", 0.90, "role_override"),
    (r"(?i)acting\s+as\s+(a\s+)?(different|new|another)\s+(ai|agent|assistant)", 0.80, "persona_override"),
    (r"(?i)<\s*/?system\s*>", 0.70, "system_tag_in_content"),
    (r"(?i)\[\s*INST\s*\]|\[SYS\]", 0.75, "llm_prompt_tag"),
    (r"(?i)forget\s+(everything|all|previous)", 0.85, "memory_wipe"),
    (r"(?i)disregard\s+(all|previous|your)\s+(instructions|rules|guidelines)", 0.90, "disregard_instructions"),
    # Financial manipulation patterns
    (r"(?i)already\s+processed\s+refund\s+of\s+\$[\d,]+", 0.70, "false_refund_claim"),
    (r"(?i)auth(orization)?\s*(code|ref|number)?\s*:\s*AUTH-\d+", 0.60, "fake_auth_code"),
    # Cross-account targeting signals
    (r"(?i)for\s+(acme|globex|initech|megacorp)\s+corp", 0.40, "cross_account_reference"),
]

# Patterns that appear in legitimate tickets (reduce false positives)
ALLOWLIST_PATTERNS = [
    r"(?i)please\s+ignore\s+(my\s+previous\s+)?email",  # Legitimate email threading
    r"(?i)our\s+finance\s+team\s+approved",  # Could be legitimate context
]


def detect_injection(
    text: str,
    source: str = "ticket_body",
    context_sources: list[str] = None,
) -> InjectionResult:
    """
    Scan text for injection patterns.
    
    Args:
        text: The text to scan (ticket body, CRM note, etc.)
        source: Where the text came from (for audit logging)
        context_sources: Other text sources to scan (CRM notes, etc.)
    
    Returns:
        InjectionResult with suspected flag and confidence score.
    """
    all_text = text
    if context_sources:
        all_text = text + "\n" + "\n".join(context_sources)

    matched_patterns = []
    total_weight = 0.0

    for pattern, weight, label in INJECTION_PATTERNS:
        if re.search(pattern, all_text):
            matched_patterns.append(label)
            total_weight += weight

    # Apply allowlist (reduce confidence if allowlist patterns match)
    allowlist_hits = sum(
        1 for p in ALLOWLIST_PATTERNS if re.search(p, all_text)
    )
    reduction = allowlist_hits * 0.15

    confidence = min(1.0, max(0.0, total_weight - reduction))
    suspected = confidence >= 0.5 or any(
        w >= 0.90 for _, w, l in INJECTION_PATTERNS
        if l in matched_patterns
    )

    return InjectionResult(
        suspected=suspected,
        confidence=round(confidence, 3),
        patterns_matched=matched_patterns,
        risk_score=round(confidence, 3),
    )


def scan_all_context(
    ticket_body: str,
    ticket_subject: str = "",
    crm_notes: list[str] = None,
) -> InjectionResult:
    """Scan all user-supplied context surfaces."""
    combined = f"{ticket_subject}\n{ticket_body}"
    context = crm_notes or []
    return detect_injection(combined, source="combined_ticket", context_sources=context)
