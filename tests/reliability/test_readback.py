"""
tests/reliability/test_readback.py
Unit tests for Commit-Timeout Read-Back verification state machine.
"""
import asyncio
import pytest
from backend.app.reliability.readback import ReadBackVerifier, ReadBackState
from services import mcp_registry


def test_readback_reconciles_committed():
    """
    Simulate scenario where refund succeeds on billing backend, but HTTP connection drops.
    Read-back probe must detect the existing idempotency record and return COMMITTED with 0 duplicate writes.
    """
    idemp_key = "idemp-commit-timeout-test-123"
    args = {
        "invoice_id": "INV-001",
        "amount_cents": 1500,
        "reason": "billing_error",
        "idempotency_key": idemp_key,
    }

    # First, simulate backend commit
    asyncio.run(mcp_registry.dispatch_tool("billing.issue_refund", args))

    # Now simulate read-back verifier probing after timeout
    result = asyncio.run(ReadBackVerifier.reconcile_timeout("billing.issue_refund", args, idemp_key))

    assert result["state"] == ReadBackState.COMMITTED
    assert result["success"] is True
    assert result["idempotent_replay"] is True
    assert result["result"]["amount_cents"] == 1500


def test_readback_detects_not_committed():
    """
    Simulate scenario where mutation never reached billing backend.
    Read-back probe must return NOT_COMMITTED and confirm safe_to_retry.
    """
    idemp_key = "uncommitted-key-456"
    args = {
        "invoice_id": "INV-001",
        "amount_cents": 500,
        "reason": "duplicate_charge",
        "idempotency_key": idemp_key,
    }

    result = asyncio.run(ReadBackVerifier.reconcile_timeout("billing.issue_refund", args, idemp_key))

    assert result["state"] == ReadBackState.NOT_COMMITTED
    assert result["safe_to_retry"] is True
    assert result["success"] is False
