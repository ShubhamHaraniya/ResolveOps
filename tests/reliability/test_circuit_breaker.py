"""
tests/reliability/test_circuit_breaker.py
Unit tests for sliding-window circuit breaker state transitions (CLOSED -> OPEN -> HALF_OPEN -> CLOSED).
"""
import time
import pytest
from backend.app.reliability.circuit_breaker import (
    CircuitBreaker,
    CircuitState,
    CircuitOpenError,
)


def test_circuit_breaker_initial_closed():
    """Verify breaker starts in CLOSED healthy state."""
    cb = CircuitBreaker(service="test_svc", failure_threshold=3, recovery_timeout=0.1)
    assert cb.state == CircuitState.CLOSED
    assert cb.can_execute() is True


def test_circuit_trips_to_open_after_failures():
    """Verify breaker trips to OPEN after consecutive failures exceed threshold."""
    cb = CircuitBreaker(service="billing_test", failure_threshold=3, recovery_timeout=0.2)

    cb.record_failure()
    assert cb.state == CircuitState.CLOSED
    cb.record_failure()
    assert cb.state == CircuitState.CLOSED

    # 3rd failure trips the breaker
    cb.record_failure()
    assert cb.state == CircuitState.OPEN

    # Execution should now be blocked
    with pytest.raises(CircuitOpenError, match="CIRCUIT OPEN"):
        cb.can_execute()


def test_circuit_half_open_and_recovery():
    """Verify transition from OPEN to HALF_OPEN after timeout, and heal to CLOSED on successes."""
    cb = CircuitBreaker(
        service="crm_test",
        failure_threshold=2,
        recovery_timeout=0.05,
        success_threshold=2,
    )

    cb.record_failure()
    cb.record_failure()
    assert cb.state == CircuitState.OPEN

    # Wait for recovery timeout
    time.sleep(0.06)

    # can_execute should transition to HALF_OPEN
    assert cb.can_execute() is True
    assert cb.state == CircuitState.HALF_OPEN

    # Record 1st success in HALF_OPEN
    cb.record_success()
    assert cb.state == CircuitState.HALF_OPEN

    # Record 2nd success in HALF_OPEN -> should heal back to CLOSED
    cb.record_success()
    assert cb.state == CircuitState.CLOSED
    assert cb.consecutive_failures == 0
