"""
Policy Engine — Deterministic Rule Evaluator

Evaluates proposed actions against policy/rules.yaml.
Never uses LLM for policy decisions — fully deterministic.

Priority order:
1. GEN-001 (legal_hold=true) — always checked first
2. Forbidden rules (most specific match)
3. Approval rules (most specific match)
4. Auto rules
5. Default deny (no matching rule → forbidden)
"""
import fnmatch
import functools
import hashlib
import os
import signal
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel

def _find_policy_file() -> Path:
    """
    Locate policy/rules.yaml.
    Priority:
    1. POLICY_FILE env var (override for tests / containers)
    2. Walk up from __file__ until we find policy/rules.yaml
    """
    env_path = os.environ.get("POLICY_FILE")
    if env_path:
        return Path(env_path)
    current = Path(__file__).resolve()
    for parent in current.parents:
        candidate = parent / "policy" / "rules.yaml"
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        f"Could not find policy/rules.yaml starting from {current}. "
        "Set POLICY_FILE env var to override."
    )

# Resolved once at import time — can be overridden with POLICY_FILE env var
POLICY_FILE = _find_policy_file()


class PolicyDecision(BaseModel):
    tier: Literal["auto", "approval", "forbidden"]
    rule_id: str
    reason: str
    approver_role: str | None = None
    escalate_to: str | None = None
    policy_version: int = 3


class PolicyContext(BaseModel):
    tool: str
    args: dict[str, Any] = {}
    account: dict[str, Any] = {}
    requester: dict[str, Any] = {}
    invoice: dict[str, Any] | None = None
    subscription: dict[str, Any] | None = None


class PolicyEngine:
    """
    Loads and evaluates policy rules from rules.yaml.
    Rules are cached at startup and reloaded on SIGHUP.
    """

    def __init__(self, policy_path: Path = POLICY_FILE):
        self.policy_path = policy_path
        self._rules: list[dict] = []
        self._version: int = 0
        self._defaults: dict = {}
        self._load()

        # Reload on SIGHUP (Unix) — no-op on Windows
        try:
            signal.signal(signal.SIGHUP, lambda *_: self._load())
        except (AttributeError, OSError):
            pass

    def _load(self):
        """Load and validate policy rules from YAML."""
        with open(self.policy_path) as f:
            data = yaml.safe_load(f)
        self._version = data.get("version", 1)
        self._defaults = data.get("defaults", {})
        rules = data.get("rules", [])
        # Sort by priority descending (higher priority = checked first)
        self._rules = sorted(rules, key=lambda r: r.get("priority", 0), reverse=True)

    def evaluate(self, ctx: PolicyContext) -> PolicyDecision:
        """
        Evaluate a proposed action against all rules.
        Returns the MOST RESTRICTIVE matching decision.

        Tier priority: forbidden > approval > auto > default-deny
        """
        best_forbidden: PolicyDecision | None = None
        best_approval: PolicyDecision | None = None
        best_auto: PolicyDecision | None = None

        for rule in self._rules:
            if not self._tool_matches(rule["tool"], ctx.tool):
                continue
            if not self._conditions_match(rule.get("when", {}), ctx):
                continue

            tier = rule["tier"]
            decision = PolicyDecision(
                tier=tier,
                rule_id=rule["id"],
                reason=rule.get("description", ""),
                approver_role=rule.get("approver_role"),
                escalate_to=rule.get("escalate_to"),
                policy_version=self._version,
            )

            if tier == "forbidden":
                # First (highest priority) forbidden rule wins
                if best_forbidden is None:
                    best_forbidden = decision
            elif tier == "approval":
                if best_approval is None:
                    best_approval = decision
            elif tier == "auto":
                if best_auto is None:
                    best_auto = decision

        # Return most restrictive
        if best_forbidden:
            return best_forbidden
        if best_approval:
            return best_approval
        if best_auto:
            return best_auto

        # Default deny
        return PolicyDecision(
            tier="forbidden",
            rule_id="DEFAULT-DENY",
            reason=f"No policy rule matched tool '{ctx.tool}' — default deny",
            policy_version=self._version,
        )

    def _tool_matches(self, pattern: str, tool: str) -> bool:
        """Match tool name against pattern. Supports '*' and 'prefix.*' wildcards."""
        if pattern == "*":
            return True
        if pattern == tool:
            return True
        # Glob matching: 'billing.*' matches 'billing.issue_refund'
        return fnmatch.fnmatch(tool, pattern)

    def _conditions_match(self, conditions: dict, ctx: PolicyContext) -> bool:
        """
        Evaluate all conditions against context.
        All conditions must match (AND logic).
        """
        for key, value in conditions.items():
            if not self._evaluate_condition(key, value, ctx):
                return False
        return True

    def _evaluate_condition(self, key: str, condition: Any, ctx: PolicyContext) -> bool:
        """Evaluate a single condition."""
        actual = self._resolve_value(key, ctx)
        if actual is None:
            # If the context doesn't have this key, condition doesn't match
            return False

        if isinstance(condition, dict):
            # Operator conditions: {lte: 5000}, {gt: 1000}, {in: [...]}
            for op, expected in condition.items():
                if op == "lte" and not (actual <= expected):
                    return False
                elif op == "lt" and not (actual < expected):
                    return False
                elif op == "gte" and not (actual >= expected):
                    return False
                elif op == "gt" and not (actual > expected):
                    return False
                elif op == "eq" and not (actual == expected):
                    return False
                elif op == "in":
                    if actual not in expected:
                        return False
            return True
        else:
            # Direct equality
            return actual == condition

    def _resolve_value(self, key: str, ctx: PolicyContext) -> Any:
        """
        Resolve a dotted key against PolicyContext.
        Examples:
          'amount_cents'               → ctx.args['amount_cents']
          'account.strategic'          → ctx.account['is_strategic']
          'account.legal_hold'         → ctx.account['is_legal_hold']
          'requester.is_authorized_contact' → ctx.requester['is_authorized']
          'invoice.age_days'           → ctx.invoice['age_days']
          'role'                       → ctx.args['role']
          'expiry_days'                → ctx.args['expiry_days']
        """
        parts = key.split(".")

        if len(parts) == 1:
            # Direct arg key
            return ctx.args.get(key)

        source = parts[0]
        field = ".".join(parts[1:])

        if source == "account":
            # Map YAML field names to model field names
            field_map = {
                "strategic": "is_strategic",
                "legal_hold": "is_legal_hold",
                "plan": "plan",
                "arr_cents": "arr_cents",
            }
            return ctx.account.get(field_map.get(field, field))

        elif source == "requester":
            field_map = {
                "is_authorized_contact": "is_authorized",
                "email": "email",
            }
            return ctx.requester.get(field_map.get(field, field))

        elif source == "invoice" and ctx.invoice:
            return ctx.invoice.get(field)

        elif source == "subscription" and ctx.subscription:
            return ctx.subscription.get(field)

        return None


# Singleton engine
@functools.lru_cache(maxsize=1)
def get_policy_engine() -> PolicyEngine:
    return PolicyEngine()
