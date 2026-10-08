"""
backend/app/reliability/saga.py
Multi-Step Saga Coordinator (Spec Section 73, ADR-009).
Coordinates atomic execution across heterogeneous systems (Billing, CRM, IAM, Ticketing).
Implements reverse compensation upon partial execution failure.
"""
from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum
from typing import List, Dict, Any, Callable, Optional, Awaitable
import structlog

from services import mcp_registry

log = structlog.get_logger()


class SagaStatus(str, Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    COMPENSATING = "COMPENSATING"
    COMPENSATED = "COMPENSATED"
    FAILED_NEEDS_MANUAL_RECONCILIATION = "FAILED_NEEDS_MANUAL_RECONCILIATION"


@dataclass
class SagaStep:
    name: str
    tool: str
    args: Dict[str, Any]
    compensating_tool: Optional[str] = None
    compensating_args: Optional[Dict[str, Any]] = None
    executed: bool = False
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class SagaCoordinator:
    """
    Executes an ordered sequence of side-effect steps.
    If a failure occurs, runs compensating transactions in reverse order.
    """

    def __init__(self, saga_name: str, ticket_id: str):
        self.saga_name = saga_name
        self.ticket_id = ticket_id
        self.steps: List[SagaStep] = []
        self.status = SagaStatus.PENDING
        self.log_history: List[Dict[str, Any]] = []

    def add_step(
        self,
        name: str,
        tool: str,
        args: Dict[str, Any],
        compensating_tool: Optional[str] = None,
        compensating_args: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Register a step with optional compensation definition."""
        step = SagaStep(
            name=name,
            tool=tool,
            args=args,
            compensating_tool=compensating_tool,
            compensating_args=compensating_args,
        )
        self.steps.append(step)

    async def execute(self) -> Dict[str, Any]:
        """
        Execute all registered steps sequentially.
        Rolls back via compensation if any step fails.
        """
        log.info("saga.execute_start", saga=self.saga_name, ticket_id=self.ticket_id, total_steps=len(self.steps))
        executed_steps: List[SagaStep] = []

        for step in self.steps:
            log.info("saga.step_executing", step_name=step.name, tool=step.tool)
            try:
                result = await mcp_registry.dispatch_tool(step.tool, step.args)
                step.executed = True
                step.result = result
                executed_steps.append(step)
                self.log_history.append({"step": step.name, "status": "succeeded", "result": result})
            except Exception as e:
                log.error("saga.step_failed", step_name=step.name, error=str(e))
                step.error = str(e)
                self.status = SagaStatus.COMPENSATING
                self.log_history.append({"step": step.name, "status": "failed", "error": str(e)})

                # Initiate compensation in reverse order
                comp_success = await self._rollback(executed_steps)
                if comp_success:
                    self.status = SagaStatus.COMPENSATED
                    return {
                        "saga": self.saga_name,
                        "status": self.status,
                        "success": False,
                        "failed_step": step.name,
                        "error": str(e),
                        "compensated": True,
                        "history": self.log_history,
                    }
                else:
                    self.status = SagaStatus.FAILED_NEEDS_MANUAL_RECONCILIATION
                    return {
                        "saga": self.saga_name,
                        "status": self.status,
                        "success": False,
                        "failed_step": step.name,
                        "error": str(e),
                        "manual_reconciliation_required": True,
                        "compensated": False,
                        "history": self.log_history,
                    }

        self.status = SagaStatus.COMPLETED
        log.info("saga.execute_complete", saga=self.saga_name)
        return {
            "saga": self.saga_name,
            "status": self.status,
            "success": True,
            "history": self.log_history,
        }

    async def _rollback(self, executed_steps: List[SagaStep]) -> bool:
        """Execute compensating transactions in reverse order."""
        log.warn("saga.rollback_initiated", saga=self.saga_name, steps_to_rollback=len(executed_steps))
        all_compensated = True

        for step in reversed(executed_steps):
            if not step.compensating_tool:
                log.info("saga.step_has_no_compensation", step_name=step.name)
                continue

            log.info("saga.compensating_step", step_name=step.name, comp_tool=step.compensating_tool)
            try:
                comp_args = step.compensating_args or {}
                comp_res = await mcp_registry.dispatch_tool(step.compensating_tool, comp_args)
                self.log_history.append({
                    "step": f"compensate_{step.name}",
                    "status": "compensated",
                    "result": comp_res,
                })
            except Exception as e:
                log.error("saga.compensation_failed", step_name=step.name, error=str(e))
                all_compensated = False
                self.log_history.append({
                    "step": f"compensate_{step.name}",
                    "status": "compensation_error",
                    "error": str(e),
                })

        return all_compensated
