"""
Tests for audit logger — hash chain integrity and PII redaction.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2] / "backend"))

from app.audit.logger import AuditLogger, _redact_pii


def test_pii_redaction_email():
    redacted = _redact_pii("john.smith@acme-corp.com")
    assert "j***@acme-corp.com" == redacted
    assert "john.smith" not in redacted


def test_pii_redaction_dict():
    data = {"email": "user@example.com", "amount_cents": 3000, "invoice_id": "INV-001"}
    redacted = _redact_pii(data)
    assert "u***@example.com" == redacted["email"]
    assert redacted["amount_cents"] == 3000  # Amount preserved
    assert redacted["invoice_id"] == "INV-001"  # Non-PII preserved


def test_hash_chain_intact():
    logger = AuditLogger()
    for i in range(5):
        logger.log_event(
            event="ticket_received",
            ticket_id=f"TKT-{i:03d}",
            run_id=f"RUN-{i:03d}",
        )
    intact, reason = logger.verify_chain()
    assert intact is True, f"Chain broken: {reason}"
    assert reason is None


def test_hash_chain_tamper_detection():
    logger = AuditLogger()
    logger.log_event("ticket_received", ticket_id="TKT-001", run_id="RUN-001")
    logger.log_event("classification_done", ticket_id="TKT-001", run_id="RUN-001")
    logger.log_event("tool_call_result", ticket_id="TKT-001", run_id="RUN-001")

    # Tamper with a row
    logger._log[1]["event"] = "TAMPERED_EVENT"

    intact, reason = logger.verify_chain()
    assert intact is False
    assert reason is not None


def test_ticket_trail_filtering():
    logger = AuditLogger()
    logger.log_event("ticket_received", ticket_id="TKT-001", run_id="RUN-001")
    logger.log_event("ticket_received", ticket_id="TKT-002", run_id="RUN-002")
    logger.log_event("classification_done", ticket_id="TKT-001", run_id="RUN-001")

    trail = logger.get_ticket_trail("TKT-001")
    assert len(trail) == 2
    assert all(e["ticket_id"] == "TKT-001" for e in trail)


def test_export_csv():
    logger = AuditLogger()
    logger.log_event("ticket_received", ticket_id="TKT-001", run_id="RUN-001", tool="billing.get_invoice")
    csv_output = logger.export_ticket("TKT-001", fmt="csv")
    assert "TKT-001" in csv_output
    assert "ticket_received" in csv_output
    lines = csv_output.strip().split("\n")
    assert len(lines) == 2  # header + 1 event


def test_prev_hash_chain():
    """Each event's prev_hash must equal previous event's row_hash."""
    logger = AuditLogger()
    events = []
    for i in range(4):
        e = logger.log_event("tool_call_start", ticket_id="TKT-001", run_id="RUN-001")
        events.append(e)

    for i in range(1, len(events)):
        assert events[i]["prev_hash"] == events[i-1]["row_hash"], \
            f"Event {i} prev_hash doesn't match event {i-1} row_hash"
