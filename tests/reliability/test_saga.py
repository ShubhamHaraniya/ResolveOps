"""
tests/reliability/test_saga.py
Unit tests for Multi-Step Saga Coordinator, forward execution, and reverse compensation.
"""
import asyncio
import pytest
from backend.app.reliability.saga import SagaCoordinator, SagaStatus


def test_saga_happy_path_success():
    """Verify that multi-step saga executes all steps to completion."""
    saga = SagaCoordinator(saga_name="test_happy_path", ticket_id="TICK-101")
    saga.add_step(
        name="step1_tag",
        tool="ticketing.set_tags",
        args={"ticket_id": "TICK-101", "tags": ["plan_upgrade_pending"]},
    )
    saga.add_step(
        name="step2_note",
        tool="ticketing.add_internal_note",
        args={"ticket_id": "TICK-101", "body": "Upgrading plan via saga"},
    )

    result = asyncio.run(saga.execute())
    assert result["success"] is True
    assert result["status"] == SagaStatus.COMPLETED
    assert len(result["history"]) == 2


def test_saga_failure_and_reverse_compensation():
    """Verify that failure on step 2 triggers compensation for step 1."""
    saga = SagaCoordinator(saga_name="test_compensation", ticket_id="TICK-101")

    # Step 1 succeeds, has compensating step
    saga.add_step(
        name="step1_apply_tag",
        tool="ticketing.set_tags",
        args={"ticket_id": "TICK-101", "tags": ["in_progress"]},
        compensating_tool="ticketing.set_tags",
        compensating_args={"ticket_id": "TICK-101", "tags": ["rolled_back"]},
    )

    # Step 2 intentionally fails (requesting forbidden admin role)
    saga.add_step(
        name="step2_fail_admin",
        tool="access.grant_access",
        args={
            "account_id": "ACCT-001",
            "user_email": "bad@actor.com",
            "role": "admin",
            "reason": "illegal",
        },
    )

    result = asyncio.run(saga.execute())
    assert result["success"] is False
    assert result["status"] == SagaStatus.COMPENSATED
    assert result["compensated"] is True
    assert result["failed_step"] == "step2_fail_admin"

    # Verify history contains the compensation execution
    steps_run = [h["step"] for h in result["history"]]
    assert "compensate_step1_apply_tag" in steps_run
