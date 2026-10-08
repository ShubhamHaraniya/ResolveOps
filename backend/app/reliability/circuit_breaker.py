"""
backend/app/reliability/circuit_breaker.py
Sliding-Window Circuit Breaker (Spec Section 72, Failure Mode #12).
Prevents cascading failures when backend services (billing, crm, ticketing, iam, kb) degrade.
States:
  - CLOSED: System healthy, normal execution.
  - OPEN: Tripped after 5 consecutive failures; fast-fails with CircuitOpenError.
  - HALF_OPEN: Trial period after recovery timeout; requires 3 consecutive successes to heal.
"""
import time
from enum import Enum
from typing import Dict, Any, Callable, Coroutine
import structlog

log = structlog.get_logger()


class CircuitState(str, Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitOpenError(Exception):
    """Raised when a tool call is attempted against an OPEN circuit."""
    def __init__(self, service: str, retry_after: float):
        super().__init__(
            f"CIRCUIT OPEN: Service '{service}' is currently degraded. "
            f"Failing fast to protect upstream systems. Retry after {retry_after:.1f}s."
        )
        self.service = service
        self.retry_after = retry_after


class CircuitBreaker:
    """
    Per-service circuit breaker.
    """

    def __init__(
        self,
        service: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        success_threshold: int = 3,
    ):
        self.service = service
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold

        self.state = CircuitState.CLOSED
        self.consecutive_failures = 0
        self.consecutive_successes = 0
        self.last_failure_time: float = 0.0
        self.last_state_change: float = time.time()

    def can_execute(self) -> bool:
        """
        Check if execution is permitted under current circuit state.
        Raises CircuitOpenError if circuit is active.
        """
        now = time.time()

        if self.state == CircuitState.OPEN:
            elapsed = now - self.last_failure_time
            if elapsed >= self.recovery_timeout:
                # Transition to HALF_OPEN probe state
                log.info("circuit.transition_half_open", service=self.service, elapsed=elapsed)
                self.state = CircuitState.HALF_OPEN
                self.consecutive_successes = 0
                self.last_state_change = now
                return True
            else:
                retry_after = self.recovery_timeout - elapsed
                log.warn("circuit.fast_fail_open", service=self.service, retry_after=retry_after)
                raise CircuitOpenError(self.service, retry_after)

        return True

    def record_success(self) -> None:
        """Record successful call outcome."""
        now = time.time()
        if self.state == CircuitState.HALF_OPEN:
            self.consecutive_successes += 1
            log.info("circuit.half_open_success", service=self.service, count=self.consecutive_successes)
            if self.consecutive_successes >= self.success_threshold:
                log.info("circuit.healed_closed", service=self.service)
                self.state = CircuitState.CLOSED
                self.consecutive_failures = 0
                self.consecutive_successes = 0
                self.last_state_change = now
        elif self.state == CircuitState.CLOSED:
            self.consecutive_failures = 0

    def record_failure(self) -> None:
        """Record failure outcome."""
        now = time.time()
        self.last_failure_time = now

        if self.state == CircuitState.HALF_OPEN:
            log.warn("circuit.half_open_failed_trip", service=self.service)
            self.state = CircuitState.OPEN
            self.consecutive_failures = self.failure_threshold
            self.last_state_change = now

        elif self.state == CircuitState.CLOSED:
            self.consecutive_failures += 1
            log.warn("circuit.recorded_failure", service=self.service, count=self.consecutive_failures)
            if self.consecutive_failures >= self.failure_threshold:
                log.error("circuit.tripped_open", service=self.service, threshold=self.failure_threshold)
                self.state = CircuitState.OPEN
                self.last_state_change = now

    def reset(self) -> None:
        """Reset breaker to clean CLOSED state."""
        self.state = CircuitState.CLOSED
        self.consecutive_failures = 0
        self.consecutive_successes = 0
        self.last_failure_time = 0.0
        self.last_state_change = time.time()


# ─── Registry of service breakers ───────────────────────────────────────────

_BREAKER_REGISTRY: Dict[str, CircuitBreaker] = {}


def get_circuit_breaker(service: str) -> CircuitBreaker:
    """Retrieve or initialize the circuit breaker for a service."""
    if service not in _BREAKER_REGISTRY:
        _BREAKER_REGISTRY[service] = CircuitBreaker(service=service)
    return _BREAKER_REGISTRY[service]


def reset_all_breakers() -> None:
    """Reset all circuit breakers (for tests or manual operator clearing)."""
    for breaker in _BREAKER_REGISTRY.values():
        breaker.reset()
