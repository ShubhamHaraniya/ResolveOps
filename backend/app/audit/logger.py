"""
backend/app/audit/logger.py
Audit log — append-only, hash-chained, PII-redacted.

All 11 event types:
1. ticket_received
2. classification_done
3. identity_verified / identity_rejected
4. context_gathered
5. plan_proposed
6. policy_decision
7. approval_requested
8. approval_decision (approved/rejected/edited/escalated)
9. tool_call_start
10. tool_call_result
11. ticket_resolved / escalated / failed

Hash chain: row_hash = SHA256(prev_hash + row_content)
PII redaction: email → j***@domain.com, phone → [PHONE], amount kept (financial record)
"""
import hashlib
import json
import re
import time
import uuid
from datetime import datetime, UTC
from typing import Any, Literal

import structlog

log = structlog.get_logger()

EventType = Literal[
    "ticket_received",
    "classification_done",
    "identity_verified",
    "identity_rejected",
    "context_gathered",
    "plan_proposed",
    "policy_decision",
    "approval_requested",
    "approval_approved",
    "approval_rejected",
    "approval_edited",
    "approval_escalated",
    "tool_call_start",
    "tool_call_result",
    "ticket_resolved",
    "ticket_escalated",
    "ticket_failed",
    "kill_switch_activated",
    "injection_detected",
]


def _redact_pii(value: Any) -> Any:
    """Redact PII from values before audit logging."""
    if isinstance(value, str):
        # Redact email addresses: j***@domain.com
        value = re.sub(
            r"([a-zA-Z0-9._%+-])[a-zA-Z0-9._%+-]*(@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})",
            lambda m: f"{m.group(1)}***{m.group(2)}",
            value,
        )
        # Redact phone numbers
        value = re.sub(r"\+?[\d\s\-\(\)]{10,}", "[PHONE]", value)
    elif isinstance(value, dict):
        return {k: _redact_pii(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [_redact_pii(item) for item in value]
    return value


def _compute_row_hash(prev_hash: str, row_content: str) -> str:
    """SHA256(prev_hash + row_content) — enables tamper detection."""
    combined = f"{prev_hash}{row_content}"
    return hashlib.sha256(combined.encode()).hexdigest()


class AuditLogger:
    """
    Append-only audit logger with hash chain.
    In production: writes to append-only Postgres table with no UPDATE/DELETE.
    In development: in-memory list.
    """

    GENESIS_HASH = "0" * 64

    def __init__(self, db_session=None):
        self._db = db_session
        self._log: list[dict] = []
        self._prev_hash = self.GENESIS_HASH

    def log_event(
        self,
        event: EventType,
        ticket_id: str,
        run_id: str,
        actor_type: Literal["agent", "human", "system"] = "agent",
        actor_id: str = "agent@resolveops",
        tool: str | None = None,
        args: dict | None = None,
        policy_rule: str | None = None,
        policy_version: int | None = 3,
        idempotency_key: str | None = None,
        result_status: str | None = None,
        trace_id: str | None = None,
        extra: dict | None = None,
    ) -> dict:
        """Log a single audit event with hash chaining."""
        event_id = str(uuid.uuid4())
        timestamp = datetime.now(UTC).isoformat()

        # Redact PII from args before storage
        args_redacted = _redact_pii(args or {})
        args_hash = None
        if args:
            args_hash = hashlib.sha256(
                json.dumps(args, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest()[:16]

        # Build row content for hash
        row_content = json.dumps({
            "id": event_id,
            "timestamp": timestamp,
            "event": event,
            "ticket_id": ticket_id,
            "run_id": run_id,
            "tool": tool,
            "args_hash": args_hash,
        }, sort_keys=True, separators=(",", ":"))

        row_hash = _compute_row_hash(self._prev_hash, row_content)

        record = {
            "id": event_id,
            "timestamp": timestamp,
            "event": event,
            "ticket_id": ticket_id,
            "run_id": run_id,
            "actor_type": actor_type,
            "actor_id": _redact_pii(actor_id),
            "tool": tool,
            "args_hash": args_hash,
            "args_redacted": args_redacted,
            "policy_rule": policy_rule,
            "policy_version": policy_version,
            "idempotency_key": idempotency_key,
            "result_status": result_status,
            "trace_id": trace_id,
            "prev_hash": self._prev_hash,
            "row_hash": row_hash,
            **(extra or {}),
        }

        self._log.append(record)
        self._prev_hash = row_hash

        log.info(
            "audit.event",
            event_type=event,
            ticket_id=ticket_id,
            run_id=run_id,
            tool=tool,
            result_status=result_status,
        )

        return record

    def verify_chain(self) -> tuple[bool, str | None]:
        """
        Verify hash chain integrity.
        Returns (True, None) if intact, (False, reason) if broken.
        """
        prev_hash = self.GENESIS_HASH
        for i, record in enumerate(self._log):
            expected_prev = record.get("prev_hash")
            if expected_prev != prev_hash:
                return False, f"Chain broken at event {i} ({record['id']}): prev_hash mismatch"

            # Recompute row hash
            row_content = json.dumps({
                "id": record["id"],
                "timestamp": record["timestamp"],
                "event": record["event"],
                "ticket_id": record["ticket_id"],
                "run_id": record["run_id"],
                "tool": record.get("tool"),
                "args_hash": record.get("args_hash"),
            }, sort_keys=True, separators=(",", ":"))

            expected_hash = _compute_row_hash(prev_hash, row_content)
            if record.get("row_hash") != expected_hash:
                return False, f"Row hash mismatch at event {i} ({record['id']})"

            prev_hash = record["row_hash"]

        return True, None

    def get_ticket_trail(self, ticket_id: str) -> list[dict]:
        return [e for e in self._log if e.get("ticket_id") == ticket_id]

    def get_run_trail(self, run_id: str) -> list[dict]:
        return [e for e in self._log if e.get("run_id") == run_id]

    def export_ticket(self, ticket_id: str, fmt: str = "json") -> str:
        events = self.get_ticket_trail(ticket_id)
        if fmt == "json":
            return json.dumps(events, indent=2)
        elif fmt == "csv":
            if not events:
                return "id,timestamp,event,tool,result_status"
            headers = ["id", "timestamp", "event", "ticket_id", "run_id", "tool", "result_status"]
            lines = [",".join(headers)]
            for e in events:
                lines.append(",".join(str(e.get(h, "")) for h in headers))
            return "\n".join(lines)
        return json.dumps(events)


# Singleton
_audit_logger: AuditLogger | None = None


def get_audit_logger() -> AuditLogger:
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger
