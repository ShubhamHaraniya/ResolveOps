"""
execute node — call the policy gateway for each approved action.
Gateway is the ONLY path to any backend. No direct calls.
Implements saga pattern: if any action fails, compensate previous ones.
"""
import hashlib
import json
import os
import time
import uuid
from datetime import datetime, UTC
import structlog
import httpx

from app.graph.state import TicketState

log = structlog.get_logger()

GATEWAY_URL = os.environ.get("GATEWAY_URL", "http://localhost:8000")
GATEWAY_JWT_SECRET = os.environ.get("GATEWAY_JWT_SECRET", "dev-secret-change-in-production")


def _make_args_hash(tool: str, args: dict) -> str:
    normalized = json.dumps(args, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(f"{tool}:{normalized}".encode()).hexdigest()


def _make_scoped_token(run_id: str, ticket_id: str, tool: str, args: dict) -> str:
    """Generate scoped JWT for this specific tool call."""
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "services", "gateway"))
    from tokens import ScopedJWT, make_args_hash
    jwt = ScopedJWT(secret=GATEWAY_JWT_SECRET)
    args_hash = make_args_hash(tool, args)
    return jwt.generate(run_id=run_id, ticket_id=ticket_id, tool=tool, args_hash=args_hash)


async def execute_node(state: TicketState) -> dict:
    """
    Execute each approved action through the policy gateway.
    Uses saga pattern: track all successes, compensate on failure.
    """
    ticket_id = state.get("ticket_id")
    run_id = state.get("run_id")
    proposal = state.get("proposal", {})
    context = state.get("context", {})
    approval = state.get("approval", {})
    approval_id = state.get("approval_id")

    actions = proposal.get("actions", [])
    decisions = state.get("policy_decisions", [])
    executed = list(state.get("executed", []))
    compensations = list(state.get("compensations", []))

    log.info("node.execute.start", ticket_id=ticket_id, action_count=len(actions))

    # Build trusted context for gateway provenance validation
    trusted_context = {
        "ticket_id": ticket_id,
        "account_id": context.get("account_id"),
        "account": context.get("account", {}),
        "requester_email": state.get("raw_ticket", {}).get("requester_email"),
        "requester": context.get("requester", {}),
        "invoices": [inv.get("id") for inv in context.get("invoices", [])],
        # Flatten invoice IDs into trusted context
        **{inv.get("id"): inv for inv in context.get("invoices", []) if inv.get("id")},
    }

    for i, action in enumerate(actions):
        tool = action.get("tool", "")
        args = action.get("args", action.get("arguments", {}))
        decision = decisions[i] if i < len(decisions) else {}

        # Add idempotency key to write operations
        if not args.get("idempotency_key") and not tool.startswith(("billing.get", "billing.list", "crm.", "access.get", "access.list")):
            args = {**args, "idempotency_key": _make_args_hash(f"{run_id}:{ticket_id}", args)}

        # Generate scoped token
        try:
            token = _make_scoped_token(run_id, ticket_id, tool, args)
        except Exception as e:
            log.error("execute.token_generation_failed", tool=tool, error=str(e))
            return {
                "executed": executed,
                "status": "failed",
                "error": f"Token generation failed for {tool}: {e}",
            }

        gateway_payload = {
            "run_id": run_id,
            "ticket_id": ticket_id,
            "tool": tool,
            "args": args,
            "token": token,
            "approval_id": approval_id if decision.get("tier") == "approval" else None,
            "trusted_context": trusted_context,
        }

        try:
            async with httpx.AsyncClient(timeout=35.0) as client:
                resp = await client.post(f"{GATEWAY_URL}/execute", json=gateway_payload)

            if resp.status_code == 200:
                result = resp.json()
                executed.append({
                    "tool": tool,
                    "args": args,
                    "result": result.get("result"),
                    "idempotent_replay": result.get("idempotent_replay", False),
                    "audit_event_id": result.get("audit_event_id"),
                    "executed_at": datetime.now(UTC).isoformat(),
                })
                log.info("execute.action_success", tool=tool, ticket_id=ticket_id)

            else:
                error_detail = resp.json().get("detail", resp.text[:200])
                log.error("execute.action_failed", tool=tool, status=resp.status_code, detail=error_detail)
                # Saga: mark compensation needed for previously executed actions
                compensations.append({
                    "failed_tool": tool,
                    "error": error_detail,
                    "compensate": [e["tool"] for e in executed],
                    "timestamp": datetime.now(UTC).isoformat(),
                })
                return {
                    "executed": executed,
                    "compensations": compensations,
                    "status": "failed",
                    "error": f"Action {tool} failed: {error_detail}",
                    "flags": list(state.get("flags", [])) + ["execution_failed"],
                }

        except (httpx.ConnectError, httpx.TimeoutException) as e:
            log.error("execute.gateway_unreachable", tool=tool, error=str(e))
            # Timeout-after-commit scenario: log as unknown outcome
            executed.append({
                "tool": tool,
                "args": args,
                "result": None,
                "idempotent_replay": False,
                "audit_event_id": None,
                "executed_at": datetime.now(UTC).isoformat(),
                "outcome": "unknown_timeout",
                "note": "Gateway timeout — read-back verification needed",
            })
            return {
                "executed": executed,
                "status": "failed",
                "error": f"Gateway timeout on {tool} — outcome unknown, read-back required",
                "flags": list(state.get("flags", [])) + ["timeout_after_commit"],
            }

    log.info(
        "node.execute.done",
        ticket_id=ticket_id,
        executed_count=len(executed),
        all_successful=all("error" not in e for e in executed),
    )

    return {
        "executed": executed,
        "compensations": compensations,
        "total_tool_calls": state.get("total_tool_calls", 0) + len(executed),
    }
