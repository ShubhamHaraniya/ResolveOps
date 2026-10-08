"""
tests/reliability/test_outbox.py
Unit tests for PostgreSQL Transactional Outbox pattern and OutboxProcessor.
"""
import asyncio
import pytest
from backend.app.reliability.outbox import (
    record_intent,
    fetch_pending_events,
    mark_processed,
    mark_failed,
    OutboxProcessor,
    _in_memory_outbox,
)


@pytest.fixture(autouse=True)
def clear_outbox():
    _in_memory_outbox.clear()
    yield
    _in_memory_outbox.clear()


def test_record_intent_and_fetch():
    """Verify recording side-effect intent."""
    event = asyncio.run(record_intent(
        event_type="ticketing.set_tags",
        payload={"ticket_id": "TICK-101", "tags": ["priority", "billing"]},
    ))
    assert event["status"] == "pending"
    assert event["event_type"] == "ticketing.set_tags"

    pending = asyncio.run(fetch_pending_events())
    assert len(pending) == 1
    assert pending[0]["id"] == event["id"]


def test_mark_processed_and_failed():
    """Verify status transitions on outbox events."""
    event1 = asyncio.run(record_intent("tool1", {"data": 1}))
    event2 = asyncio.run(record_intent("tool2", {"data": 2}))

    asyncio.run(mark_processed(event1["id"]))
    asyncio.run(mark_failed(event2["id"], "Simulated network failure"))

    pending = asyncio.run(fetch_pending_events())
    assert len(pending) == 0

    assert _in_memory_outbox[0]["status"] == "processed"
    assert _in_memory_outbox[0]["processed_at"] is not None

    assert _in_memory_outbox[1]["status"] == "failed"
    assert _in_memory_outbox[1]["error"] == "Simulated network failure"


def test_outbox_processor_execution():
    """Verify background worker processing pending outbox items via MCP registry."""
    asyncio.run(record_intent(
        event_type="ticketing.set_tags",
        payload={"ticket_id": "TICK-101", "tags": ["processed_by_outbox"]},
    ))

    processor = OutboxProcessor()
    results = asyncio.run(processor.process_batch())

    assert len(results) == 1
    assert results[0]["status"] == "processed"

    # Pending queue should now be empty
    pending = asyncio.run(fetch_pending_events())
    assert len(pending) == 0
