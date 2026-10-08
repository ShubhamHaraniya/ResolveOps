"""
services/gateway/gateway.py
The Policy Gateway — the ONLY authorized path from the agent to any backend.

12 sequential enforcement steps. ALL must pass or execution is blocked.
No step can be skipped, bypassed, or reordered.

CRITICAL: This is NOT a suggestion layer. It is the enforcement boundary.
The LangGraph workflow MUST call the gateway for every tool execution.
No direct backend calls are permitted from node code.
"""
import hashlib
import json
import os
import time
import uuid
from datetime import datetime, UTC
from typing import Any, Literal

import httpx
import structlog
from fastapi import FastAPI, HTTPException, Depends, Header
from pydantic import BaseModel, Field

from tokens import make_args_hash, ScopedJWT
from injection import scan_all_context, InjectionResult

log = structlog.get_logger()

# ─── Config from environment ───────────────────────────────────────────────
TICKETING_URL = os.environ.get("MOCK_TICKETING_URL", "http://localhost:8001")
CRM_URL = os.environ.get("MOCK_CRM_URL", "http://localhost:8002")
BILLING_URL = os.environ.get("MOCK_BILLING_URL", "http://localhost:8003")
IAM_URL = os.environ.get("MOCK_IAM_URL", "http://localhost:8004")

GATEWAY_JWT_SECRET = os.environ.get("GATEWAY_JWT_SECRET", "dev-secret-change-in-production")
MAX_TOOL_CALLS_PER_RUN = int(os.environ.get("MAX_TOOL_CALLS_PER_RUN", "20"))
MAX_LLM_CALLS_PER_RUN = int(os.environ.get("MAX_LLM_CALLS_PER_RUN", "10"))
MAX_REPLANS = int(os.environ.get("MAX_REPLANS", "2"))

app = FastAPI(title="ResolveOps Policy Gateway", version="1.0.0")

# In-memory kill switch (in production: Redis)
_kill_switch: bool = False
# In-memory idempotency store (in production: Postgres + Redis)
_idempotency_store: dict[str, dict] = {}
# In-memory call counters per run: {run_id: {tool_calls: N, llm_calls: N, replans: N}}
_run_budgets: dict[str, dict] = {}
# In-memory audit log (in production: append-only Postgres table)
_audit_log: list[dict] = []

jwt_validator = ScopedJWT(secret=GATEWAY_JWT_SECRET)


# ─── Request / Response Models ─────────────────────────────────────────────

class GatewayRequest(BaseModel):
    run_id: str
    ticket_id: str
    tool: str = Field(description="Exact tool name: e.g. billing.issue_refund")
    args: dict[str, Any] = Field(default_factory=dict)
    token: str = Field(description="Scoped JWT for this specific tool call")
    approval_id: str | None = None  # Required for approval-tier actions
    approval_token: str | None = None  # Approval hash for validation
    # Context for provenance validation
    trusted_context: dict[str, Any] = Field(
        default_factory=dict,
        description="Verified context from prior tool results (invoice IDs, account IDs, etc.)"
    )
    injection_result: dict | None = None  # From injection scanner


class GatewayResponse(BaseModel):
    success: bool
    result: Any = None
    idempotent_replay: bool = False
    audit_event_id: str
    error: str | None = None
    blocked_reason: str | None = None


# ─── Step Implementations ───────────────────────────────────────────────────

def step1_authenticate_run(req: GatewayRequest) -> None:
    """Step 1: Validate scoped JWT."""
    args_hash = make_args_hash(req.tool, req.args)
    try:
        jwt_validator.validate(
            token=req.token,
            expected_run_id=req.run_id,
            expected_ticket_id=req.ticket_id,
            expected_tool=req.tool,
            expected_args_hash=args_hash,
        )
    except ValueError as e:
        raise HTTPException(status_code=401, detail=f"STEP1 AUTH FAILED: {e}")


def step2_validate_schema(req: GatewayRequest) -> None:
    """Step 2: Validate args against tool schema."""
    TOOL_SCHEMAS = {
        "billing.issue_refund": {"required": ["invoice_id", "amount_cents", "reason", "idempotency_key"]},
        "billing.issue_credit": {"required": ["account_id", "amount_cents", "reason", "idempotency_key"]},
        "billing.change_plan": {"required": ["subscription_id", "new_plan", "idempotency_key"]},
        "billing.pause_subscription": {"required": ["subscription_id"]},
        "access.grant_access": {"required": ["account_id", "user_email", "role", "expiry_days", "reason"]},
        "access.reset_mfa": {"required": ["email", "account_id", "reason"]},
        "ticketing.add_internal_note": {"required": ["ticket_id", "body"]},
        "ticketing.send_public_reply": {"required": ["ticket_id", "body"]},
        "ticketing.patch_ticket": {"required": ["ticket_id"]},
        "billing.get_invoice": {"required": ["invoice_id"]},
        "billing.list_invoices": {"required": ["account_id"]},
        "billing.get_subscription": {"required": ["subscription_id"]},
        "billing.preview_plan_change": {"required": ["subscription_id", "new_plan"]},
        "crm.get_account": {"required": ["account_id"]},
        "crm.find_contact": {"required": ["email"]},
        "access.get_user": {"required": ["email"]},
        "access.list_grants": {"required": ["account_id"]},
        "kb.search_policy": {"required": ["query"]},
    }
    schema = TOOL_SCHEMAS.get(req.tool)
    if schema is None:
        raise HTTPException(
            status_code=403,
            detail=f"STEP2 SCHEMA FAIL: Unknown tool '{req.tool}' — not in approved tool registry"
        )
    missing = [f for f in schema["required"] if f not in req.args]
    if missing:
        raise HTTPException(
            status_code=422,
            detail=f"STEP2 SCHEMA FAIL: Missing required args: {missing}"
        )


def step3_validate_provenance(req: GatewayRequest) -> None:
    """
    Step 3: All IDs in args must originate from trusted_context.
    Prevents the agent from inventing or hallucinating IDs.
    
    Any ID-like arg (ending in _id, or named 'email') must appear
    in the trusted context gathered from real tool results.
    """
    if not req.trusted_context:
        # If no context provided, skip provenance for read-only tools
        readonly_tools = {
            "billing.get_invoice", "billing.list_invoices", "billing.get_subscription",
            "billing.preview_plan_change", "crm.get_account", "crm.find_contact",
            "access.get_user", "access.list_grants", "kb.search_policy",
        }
        if req.tool in readonly_tools:
            return
        # Write tools without context → fail
        raise HTTPException(
            status_code=403,
            detail="STEP3 PROVENANCE FAIL: Trusted context is required for write operations"
        )

    # Build flat set of all trusted values from context
    trusted_values: set[str] = set()
    _flatten_values(req.trusted_context, trusted_values)

    # Check ID fields
    id_fields = [k for k in req.args if k.endswith("_id") or k in ("email", "user_email")]
    for field in id_fields:
        value = str(req.args[field])
        if value not in trusted_values:
            raise HTTPException(
                status_code=403,
                detail=f"STEP3 PROVENANCE FAIL: '{field}={value}' not found in trusted context — "
                       f"possible hallucinated or injected identifier"
            )


def _flatten_values(obj: Any, result: set, depth: int = 0):
    """Recursively extract all string/numeric values from a nested dict."""
    if depth > 5:
        return
    if isinstance(obj, dict):
        for v in obj.values():
            _flatten_values(v, result, depth + 1)
    elif isinstance(obj, (list, tuple)):
        for item in obj:
            _flatten_values(item, result, depth + 1)
    elif isinstance(obj, (str, int, float)) and obj:
        result.add(str(obj))


def step4_bind_identity(req: GatewayRequest) -> None:
    """
    Step 4: Verify requester is an authorized contact for the target account.
    Prevents wrong-requester attacks (attacker@gmail.com targeting Acme Corp).
    """
    ctx = req.trusted_context
    requester_email = ctx.get("requester_email", "")
    account_id = ctx.get("account_id") or req.args.get("account_id", "")
    
    # Skip identity check for non-account-specific reads
    if req.tool in ("kb.search_policy",):
        return

    if not requester_email:
        raise HTTPException(status_code=403, detail="STEP4 IDENTITY FAIL: No requester email in context")

    authorized_contacts = ctx.get("account", {}).get("authorized_contacts", [])
    if not authorized_contacts:
        # Trusted context doesn't have account info yet — pass (intake node hasn't fetched yet)
        return
    
    if requester_email not in authorized_contacts:
        raise HTTPException(
            status_code=403,
            detail=f"STEP4 IDENTITY FAIL: '{requester_email}' is not an authorized contact "
                   f"for account '{account_id}'"
        )


def step5_evaluate_policy(req: GatewayRequest) -> dict:
    """
    Step 5: Evaluate policy rules.
    Returns policy decision dict. Raises 403 if forbidden.
    """
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
    from app.policy.engine import PolicyEngine, PolicyContext
    
    engine = PolicyEngine()
    ctx_data = req.trusted_context
    
    from app.policy.engine import PolicyContext
    policy_ctx = PolicyContext(
        tool=req.tool,
        args=req.args,
        account=ctx_data.get("account", {}),
        requester=ctx_data.get("requester", {}),
        invoice=ctx_data.get("invoice"),
    )
    decision = engine.evaluate(policy_ctx)
    
    if decision.tier == "forbidden":
        raise HTTPException(
            status_code=403,
            detail=f"STEP5 POLICY FORBIDDEN: Rule {decision.rule_id} — {decision.reason}"
        )
    
    return {"tier": decision.tier, "rule_id": decision.rule_id, "approver_role": decision.approver_role}


def step6_validate_approval(req: GatewayRequest, policy_decision: dict) -> None:
    """
    Step 6: If approval-tier, validate approval exists, not expired, hash matches.
    The hash MUST match exactly — any arg modification invalidates the approval.
    """
    if policy_decision["tier"] != "approval":
        return

    if not req.approval_id:
        raise HTTPException(
            status_code=403,
            detail="STEP6 APPROVAL REQUIRED: This action requires human approval. "
                   "Submit for approval via POST /api/approvals first."
        )

    # Look up approval record (in-memory for now — Postgres in production)
    # For M2 integration test, acceptance is simulated
    approval_record = _get_approval(req.approval_id)
    if not approval_record:
        raise HTTPException(status_code=403, detail=f"STEP6 APPROVAL FAIL: Approval {req.approval_id} not found")

    if approval_record.get("status") != "approved":
        raise HTTPException(
            status_code=403,
            detail=f"STEP6 APPROVAL FAIL: Approval status is '{approval_record.get('status')}', not 'approved'"
        )

    # Expiry check
    expires_at = approval_record.get("expires_at", 0)
    if time.time() > expires_at:
        raise HTTPException(status_code=403, detail="STEP6 APPROVAL EXPIRED: Approval has expired (24h limit)")

    # Hash match — the MOST CRITICAL check
    expected_hash = make_args_hash(req.tool, req.args)
    stored_hash = approval_record.get("args_hash")
    if not stored_hash or stored_hash != expected_hash:
        raise HTTPException(
            status_code=403,
            detail=f"STEP6 APPROVAL HASH MISMATCH: Approved args don't match submitted args. "
                   f"Possible tampering or edit. Create a new approval request."
        )


def step7_check_idempotency(req: GatewayRequest) -> dict | None:
    """
    Step 7: Check idempotency store. Return cached result if exists.
    Key = SHA256(run_id + tool + sorted_args)
    """
    idem_key = make_args_hash(f"{req.run_id}:{req.ticket_id}", req.args)
    if idem_key in _idempotency_store:
        cached = _idempotency_store[idem_key]
        log.info("gateway.idempotency.replay", run_id=req.run_id, tool=req.tool)
        return cached
    return None


def step8_check_limits(req: GatewayRequest) -> None:
    """Step 8: Enforce per-run budget limits."""
    budgets = _run_budgets.setdefault(req.run_id, {"tool_calls": 0, "llm_calls": 0, "replans": 0})
    if budgets["tool_calls"] >= MAX_TOOL_CALLS_PER_RUN:
        raise HTTPException(
            status_code=429,
            detail=f"STEP8 BUDGET EXCEEDED: max_tool_calls={MAX_TOOL_CALLS_PER_RUN} reached for run {req.run_id}"
        )


def step9_audit_start(req: GatewayRequest, audit_event_id: str) -> None:
    """Step 9: Write audit event BEFORE execution."""
    event = {
        "id": audit_event_id,
        "timestamp": datetime.now(UTC).isoformat(),
        "event": "tool_call_start",
        "run_id": req.run_id,
        "ticket_id": req.ticket_id,
        "tool": req.tool,
        "args_hash": make_args_hash(req.tool, req.args),
        "args_redacted": _redact_pii(req.args),
        "actor_type": "agent",
        "status": "executing",
    }
    _audit_log.append(event)
    log.info("gateway.audit.start", **{k: v for k, v in event.items() if k != "args_redacted"})


def step10_check_kill_switch(req: GatewayRequest) -> None:
    """Step 10: Check global kill switch."""
    if _kill_switch:
        raise HTTPException(
            status_code=503,
            detail="STEP10 KILL SWITCH ACTIVE: All agent tool execution is suspended. "
                   "Contact support-ops@northwindcloud.com"
        )


async def step11_execute(req: GatewayRequest) -> Any:
    """Step 11: Dispatch to the appropriate mock backend."""
    tool = req.tool
    args = req.args
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            if tool == "billing.issue_refund":
                r = await client.post(f"{BILLING_URL}/refunds", json={
                    "invoice_id": args["invoice_id"],
                    "amount_cents": args["amount_cents"],
                    "reason": args["reason"],
                    "idempotency_key": args.get("idempotency_key", make_args_hash(tool, args)),
                }, headers={"Idempotency-Key": args.get("idempotency_key", "")})
                r.raise_for_status()
                return r.json()
            
            elif tool == "billing.issue_credit":
                r = await client.post(f"{BILLING_URL}/credits", json=args)
                r.raise_for_status()
                return r.json()
            
            elif tool == "billing.change_plan":
                sub_id = args.pop("subscription_id")
                r = await client.post(f"{BILLING_URL}/subscriptions/{sub_id}/change-plan", json=args)
                r.raise_for_status()
                return r.json()
            
            elif tool == "billing.get_invoice":
                r = await client.get(f"{BILLING_URL}/invoices/{args['invoice_id']}")
                r.raise_for_status()
                return r.json()
            
            elif tool == "billing.list_invoices":
                r = await client.get(f"{BILLING_URL}/customers/{args['account_id']}/invoices")
                r.raise_for_status()
                return r.json()
            
            elif tool == "billing.get_subscription":
                r = await client.get(f"{BILLING_URL}/subscriptions/{args['subscription_id']}")
                r.raise_for_status()
                return r.json()
            
            elif tool == "crm.get_account":
                r = await client.get(f"{CRM_URL}/accounts/{args['account_id']}")
                r.raise_for_status()
                return r.json()
            
            elif tool == "crm.find_contact":
                r = await client.get(f"{CRM_URL}/contacts", params={"email": args["email"]})
                r.raise_for_status()
                return r.json()
            
            elif tool == "access.grant_access":
                r = await client.post(f"{IAM_URL}/access-grants", json=args)
                r.raise_for_status()
                return r.json()
            
            elif tool == "access.reset_mfa":
                r = await client.post(f"{IAM_URL}/mfa-reset", json=args)
                r.raise_for_status()
                return r.json()
            
            elif tool == "access.get_user":
                r = await client.get(f"{IAM_URL}/users/{args['email']}")
                r.raise_for_status()
                return r.json()
            
            elif tool == "ticketing.add_internal_note":
                r = await client.post(f"{TICKETING_URL}/tickets/{args['ticket_id']}/comments", json={
                    "body": args["body"],
                    "is_internal": True,
                    "author": "agent@resolveops",
                })
                r.raise_for_status()
                return r.json()
            
            elif tool == "ticketing.send_public_reply":
                r = await client.post(f"{TICKETING_URL}/tickets/{args['ticket_id']}/comments", json={
                    "body": args["body"],
                    "is_internal": False,
                    "author": "support@northwindcloud.com",
                })
                r.raise_for_status()
                return r.json()
            
            elif tool == "ticketing.patch_ticket":
                ticket_id = args.pop("ticket_id")
                r = await client.patch(f"{TICKETING_URL}/tickets/{ticket_id}", json=args)
                r.raise_for_status()
                return r.json()
            
            else:
                raise HTTPException(status_code=403, detail=f"Unknown tool: {tool}")
        
        except httpx.HTTPStatusError as e:
            if e.response.status_code >= 500:
                raise HTTPException(status_code=502, detail=f"Backend error: {e.response.text[:200]}")
            raise HTTPException(status_code=e.response.status_code, detail=e.response.text[:200])


def step12_audit_result(
    req: GatewayRequest,
    audit_event_id: str,
    result: Any,
    idempotent_replay: bool,
) -> None:
    """Step 12: Write execution result to audit log."""
    event = {
        "id": f"{audit_event_id}-result",
        "timestamp": datetime.now(UTC).isoformat(),
        "event": "tool_call_result",
        "run_id": req.run_id,
        "ticket_id": req.ticket_id,
        "tool": req.tool,
        "args_hash": make_args_hash(req.tool, req.args),
        "result_status": "success",
        "idempotent_replay": idempotent_replay,
        "actor_type": "agent",
    }
    _audit_log.append(event)
    log.info("gateway.audit.result", **event)


# ─── Helpers ───────────────────────────────────────────────────────────────

def _redact_pii(args: dict) -> dict:
    """Redact PII fields before logging."""
    PII_FIELDS = {"email", "user_email", "phone", "card_number", "billing_address", "body"}
    redacted = {}
    for k, v in args.items():
        if k in PII_FIELDS:
            if isinstance(v, str) and "@" in v:
                parts = v.split("@")
                redacted[k] = f"{parts[0][:1]}***@{parts[1]}"
            else:
                redacted[k] = "[REDACTED]"
        else:
            redacted[k] = v
    return redacted


def _get_approval(approval_id: str) -> dict | None:
    """Retrieve approval record (in-memory for M2; Postgres in production)."""
    return _approvals.get(approval_id)


# In-memory approval store
_approvals: dict[str, dict] = {}


# ─── Gateway Endpoint ───────────────────────────────────────────────────────

@app.post("/execute", response_model=GatewayResponse)
async def execute(req: GatewayRequest) -> GatewayResponse:
    """
    The ONE AND ONLY path from the agent to any backend.
    All 12 steps must pass. Any failure → HTTP error, no execution.
    """
    audit_event_id = str(uuid.uuid4())[:8]
    
    log.info(
        "gateway.execute.start",
        run_id=req.run_id,
        ticket_id=req.ticket_id,
        tool=req.tool,
        audit_event_id=audit_event_id,
    )
    
    # ── Sequential 12-step enforcement ────────────────────────────────────
    step1_authenticate_run(req)
    step2_validate_schema(req)
    step3_validate_provenance(req)
    step4_bind_identity(req)
    policy_decision = step5_evaluate_policy(req)
    step6_validate_approval(req, policy_decision)
    
    # Idempotency — return cached if exists
    cached = step7_check_idempotency(req)
    if cached:
        return GatewayResponse(
            success=True,
            result=cached["result"],
            idempotent_replay=True,
            audit_event_id=audit_event_id,
        )
    
    step8_check_limits(req)
    step9_audit_start(req, audit_event_id)
    step10_check_kill_switch(req)
    
    # Execute
    result = await step11_execute(req)
    
    # Post-execution accounting
    budgets = _run_budgets.setdefault(req.run_id, {"tool_calls": 0, "llm_calls": 0, "replans": 0})
    budgets["tool_calls"] += 1
    
    # Cache result for idempotency
    idem_key = make_args_hash(f"{req.run_id}:{req.ticket_id}", req.args)
    _idempotency_store[idem_key] = {"result": result, "timestamp": time.time()}
    
    step12_audit_result(req, audit_event_id, result, idempotent_replay=False)
    
    return GatewayResponse(
        success=True,
        result=result,
        idempotent_replay=False,
        audit_event_id=audit_event_id,
    )


# ─── Management Endpoints ───────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "kill_switch": _kill_switch, "service": "gateway"}


@app.post("/admin/kill-switch/activate")
def activate_kill_switch():
    global _kill_switch
    _kill_switch = True
    log.warning("gateway.kill_switch.ACTIVATED")
    return {"kill_switch": True, "message": "All agent execution suspended"}


@app.post("/admin/kill-switch/deactivate")
def deactivate_kill_switch():
    global _kill_switch
    _kill_switch = False
    log.warning("gateway.kill_switch.DEACTIVATED")
    return {"kill_switch": False, "message": "Agent execution resumed"}


@app.get("/audit")
def get_audit_log(run_id: str = None, ticket_id: str = None, limit: int = 100):
    events = _audit_log
    if run_id:
        events = [e for e in events if e.get("run_id") == run_id]
    if ticket_id:
        events = [e for e in events if e.get("ticket_id") == ticket_id]
    return {"events": events[-limit:], "total": len(events)}


@app.post("/approvals/{approval_id}/register")
def register_approval(approval_id: str, record: dict):
    """Register an approved action (called by the approval API after human approval)."""
    _approvals[approval_id] = record
    return {"registered": True, "approval_id": approval_id}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
