"""
backend/app/reliability/readback.py
Commit-Timeout Read-Back Verification State Machine (Spec Section 71, Failure Mode #6).
Prevents duplicate financial debit when HTTP connection times out after backend commit.
State machine: COMMITTED -> return cached success; NOT_COMMITTED -> safe retry; INDETERMINATE -> human escalation.
"""
from enum import Enum
from typing import Dict, Any, Optional
import structlog

from services import mcp_registry

log = structlog.get_logger()


class ReadBackState(str, Enum):
    COMMITTED = "COMMITTED"
    NOT_COMMITTED = "NOT_COMMITTED"
    INDETERMINATE = "INDETERMINATE"


class ReadBackVerifier:
    """
    Reconciles unknown-outcome write operations following network drop or timeout.
    """

    @staticmethod
    async def reconcile_timeout(
        tool: str,
        args: Dict[str, Any],
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Probe backend system to determine if the timed-out mutation was committed.
        """
        log.warn("readback.reconciliation_initiated", tool=tool, idempotency_key=idempotency_key)

        if tool == "billing.issue_refund":
            invoice_id = args.get("invoice_id")
            amount_cents = args.get("amount_cents", 0)

            try:
                # Probe invoice state
                inv = await mcp_registry.dispatch_tool("billing.get_invoice", {"invoice_id": invoice_id})
                
                # Check MCP billing in-memory idempotency store
                from services.mcp_billing.server import _idempotency_store, _refunds
                if idempotency_key and idempotency_key in _idempotency_store:
                    cached = _idempotency_store[idempotency_key]
                    log.info("readback.reconciled_committed", state=ReadBackState.COMMITTED, refund_id=cached.get("id"))
                    return {
                        "state": ReadBackState.COMMITTED,
                        "success": True,
                        "reconciled": True,
                        "idempotent_replay": True,
                        "result": cached,
                    }

                # Check if refund appears in refund log for this invoice
                matching_refund = next(
                    (r for r in _refunds if r.get("invoice_id") == invoice_id and r.get("idempotency_key") == idempotency_key),
                    None
                )
                if matching_refund:
                    log.info("readback.reconciled_committed_from_refunds", refund_id=matching_refund.get("id"))
                    return {
                        "state": ReadBackState.COMMITTED,
                        "success": True,
                        "reconciled": True,
                        "idempotent_replay": True,
                        "result": matching_refund,
                    }

                # If invoice exists and not marked refunded with this key
                log.info("readback.reconciled_not_committed", invoice_id=invoice_id)
                return {
                    "state": ReadBackState.NOT_COMMITTED,
                    "success": False,
                    "reconciled": True,
                    "safe_to_retry": True,
                }

            except Exception as e:
                log.error("readback.probe_failed", error=str(e))
                return {
                    "state": ReadBackState.INDETERMINATE,
                    "success": False,
                    "reconciled": False,
                    "error": str(e),
                    "requires_manual_reconciliation": True,
                }

        elif tool == "billing.change_plan":
            sub_id = args.get("subscription_id")
            new_plan = args.get("new_plan")
            try:
                sub = await mcp_registry.dispatch_tool("billing.get_subscription", {"subscription_id": sub_id})
                if sub.get("plan") == new_plan:
                    return {
                        "state": ReadBackState.COMMITTED,
                        "success": True,
                        "reconciled": True,
                        "result": sub,
                    }
                return {
                    "state": ReadBackState.NOT_COMMITTED,
                    "success": False,
                    "safe_to_retry": True,
                }
            except Exception as e:
                return {
                    "state": ReadBackState.INDETERMINATE,
                    "requires_manual_reconciliation": True,
                    "error": str(e),
                }

        # Default for unsupported tools
        return {
            "state": ReadBackState.INDETERMINATE,
            "requires_manual_reconciliation": True,
            "reason": f"No read-back probe available for tool '{tool}'",
        }
