"""
execute node — call the policy gateway for each approved action.
Gateway is the ONLY path to any backend. No direct calls.
If an action fails the run is marked failed; nothing is rolled back.
"""
import hashlib
import json
import os
from datetime import datetime, UTC
import structlog

from app.graph.state import TicketState

log = structlog.get_logger()

GATEWAY_JWT_SECRET = os.environ.get("GATEWAY_JWT_SECRET", "dev-secret-change-in-production")


def _make_args_hash(tool: str, args: dict) -> str:
    normalized = json.dumps(args, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(f"{tool}:{normalized}".encode()).hexdigest()


def _make_scoped_token(run_id: str, ticket_id: str, tool: str, args: dict) -> str:
    """Generate scoped JWT for this specific tool call."""
    from services.gateway.tokens import ScopedJWT, make_args_hash
    jwt = ScopedJWT(secret=GATEWAY_JWT_SECRET)
    args_hash = make_args_hash(tool, args)
    return jwt.generate(run_id=run_id, ticket_id=ticket_id, tool=tool, args_hash=args_hash)


async def execute_node(state: TicketState) -> dict:
    """
    Execute each approved action through the policy gateway.
    Stops at the first failure and marks the run failed (no rollback).
    """
    ticket_id = state.get("ticket_id")
    run_id = state.get("run_id")
    proposal = state.get("proposal", {})
    context = state.get("context", {})
    approval_id = state.get("approval_id")

    actions = proposal.get("actions", [])
    decisions = state.get("policy_decisions", [])
    executed = list(state.get("executed", []))

    log.info("node.execute.start", ticket_id=ticket_id, action_count=len(actions))

    # Build trusted context for gateway provenance validation
    invoices_list = context.get("invoices", [])
    primary_invoice = invoices_list[0] if invoices_list else None

    trusted_context = {
        "ticket_id": ticket_id,
        "account_id": context.get("account_id") or "ACC-001",
        "account": context.get("account", {}),
        "requester_email": state.get("raw_ticket", {}).get("requester_email"),
        "requester": context.get("requester", {}),
        "invoice": primary_invoice,
        "invoices": [inv.get("id") for inv in invoices_list if isinstance(inv, dict)],
        # Flatten invoice IDs into trusted context
        **{inv.get("id"): inv for inv in invoices_list if isinstance(inv, dict) and inv.get("id")},
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
            from services.gateway.gateway import execute as inprocess_execute, GatewayRequest
            gw_req = GatewayRequest(**gateway_payload)
            gw_res = await inprocess_execute(gw_req)
            executed.append({
                "tool": tool,
                "args": args,
                "result": gw_res.result,
                "idempotent_replay": gw_res.idempotent_replay,
                "audit_event_id": gw_res.audit_event_id,
                "executed_at": datetime.now(UTC).isoformat(),
            })
            log.info("execute.action_success", tool=tool, ticket_id=ticket_id)

        except Exception as e:
            # Check if this was a simulated timeout after commit (Requirement 13)
            import httpx
            if isinstance(e, (httpx.TimeoutException, TimeoutError)) or "timeout" in str(e).lower():
                log.error("execute.gateway_timeout", tool=tool, error=str(e))
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

            error_detail = getattr(e, "detail", str(e))
            log.error("execute.action_failed", tool=tool, error=error_detail)

            return {
                "executed": executed,
                "status": "failed",
                "error": f"Action {tool} failed: {error_detail}",
                "flags": list(state.get("flags", [])) + ["execution_failed"],
            }

    log.info(
        "node.execute.done",
        ticket_id=ticket_id,
        executed_count=len(executed),
        all_successful=all("error" not in e for e in executed),
    )

    return {
        "executed": executed,
        "total_tool_calls": state.get("total_tool_calls", 0) + len(executed),
    }
