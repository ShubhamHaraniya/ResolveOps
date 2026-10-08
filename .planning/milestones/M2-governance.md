# M2 — Governance & Reliability

> Milestone: 2 of 3 | Timeline: Week 2 | Status: LOCKED (requires M1 complete)

**Goal:** All security controls active, all reliability patterns implemented, 30+ eval scenarios passing, naive baseline comparison complete.

**Unlock condition:** M1 Definition of Done fully checked.

---

## Phases

### M2-P1 · Policy Gateway (Primary Security Boundary)

**Status:** PENDING

**Deliverables:**
- [ ] `services/gateway/gateway.py` — 12-step sequential enforcement
- [ ] Step 1: `authenticate_run()` — validate scoped JWT (ticket_id, tool, run_id, exp)
- [ ] Step 2: `validate_schema()` — Pydantic tool schema validation
- [ ] Step 3: `validate_provenance()` — all IDs must originate from trusted ticket metadata or prior tool results
- [ ] Step 4: `bind_identity()` — requester email linked to target account CRM
- [ ] Step 5: `evaluate_policy()` — rules.yaml evaluation → auto/approval/forbidden
- [ ] Step 6: `validate_approval()` — hash match for approval-required actions
- [ ] Step 7: `check_idempotency()` — hash → cached result lookup
- [ ] Step 8: `check_limits()` — per-run max_tool_calls=20, max_llm_calls=10, max_replans=2
- [ ] Step 9: `audit_start()` — write audit event before execution
- [ ] Step 10: `check_kill_switch()` — Redis kill switch flag
- [ ] Step 11: `execute()` — dispatch to MCP server
- [ ] Step 12: `audit_result()` — write execution result to audit log
- [ ] `services/gateway/tokens.py` — scoped JWT generation and validation
- [ ] `services/gateway/injection.py` — prompt injection detection (flag, don't block on suspicion alone)

**Verification:**
- Agent with no gateway call → impossible (no direct backend route exists)
- Invented invoice_id not in trusted context → PROVENANCE FAILURE → BLOCK
- attacker@gmail.com targeting acme.com account → IDENTITY MISMATCH → FORBIDDEN
- Approval for $30 refund → attempt $300 → HASH MISMATCH → BLOCK
- Kill switch ON → all execution stops immediately
- Every gateway call produces at minimum 2 audit events (start + result)

---

### M2-P2 · Approval System

**Status:** PENDING

**Deliverables:**
- [ ] `approvals` table — id, ticket_id, run_id, tool, args_hash, args_redacted, policy_rule, approver_role, status, created_at, expires_at, reviewed_at, reviewer_id, edit_reason
- [ ] `GET /api/approvals` — list pending approvals
- [ ] `POST /api/approvals/{id}/approve` — approve, validate hash, execute
- [ ] `POST /api/approvals/{id}/reject` — reject with reason
- [ ] `POST /api/approvals/{id}/edit` — edit args → revalidate policy → new approval record
- [ ] `POST /api/approvals/{id}/escalate` — escalate to higher role
- [ ] Approval hash: `SHA256(ticket_id + ":" + tool + ":" + sorted_json(normalized_args))`
- [ ] Expiration: 24 hours from creation
- [ ] State-change invalidation: background job checks account/ticket state at approval time
- [ ] Edit flow: edit → revalidate → require fresh human approval (no auto-approve)

**Verification:**
- Approve $30 refund → attempt execute $300 refund → HASH MISMATCH → rejected by gateway
- Approval created → 25 hours pass → attempt to use → EXPIRED
- Approval pending → account becomes strategic → approval INVALIDATED
- Edit args → new approval record required before execution

---

### M2-P3 · Idempotency & Read-Back Verification

**Status:** PENDING

**Deliverables:**
- [ ] `backend/app/reliability/idempotency.py` — idempotency store (Postgres + Redis)
- [ ] Key generation: `SHA256(ticket_id + ":" + tool + ":" + sorted_json(normalized_args))`
- [ ] Store: `key → {status, result, created_at}`
- [ ] Read-back: `backend/app/reliability/readback.py` — query billing by idempotency key after unknown-outcome write
- [ ] Billing mock timeout-after-commit scenario
- [ ] Idempotency-Key header passed through to all write MCP tools

**Verification:**
- Execute refund → same request again → returns original result, no second refund
- Billing commits refund → network timeout → read-back finds existing → returns result → no duplicate
- Zero duplicate side-effects across all 30 evaluation scenarios

---

### M2-P4 · Reliability Patterns

**Status:** PENDING

**Deliverables:**
- [ ] `backend/app/reliability/saga.py` — multi-step action coordinator with compensation registry
- [ ] Compensation handlers for: billing.change_plan, crm.update, ticket.add_note
- [ ] `backend/app/reliability/retry.py` — exponential backoff with jitter, max attempts, transient error detection
- [ ] `backend/app/reliability/circuit_breaker.py` — per-service breaker (open/closed/half-open states)
- [ ] `backend/app/reliability/outbox.py` — Postgres outbox table + processor
- [ ] Outbox table: id, event_type, payload, status, created_at, processed_at
- [ ] Budget enforcement: max_tool_calls, max_llm_calls, max_replans per run

**Verification:**
- billing success + CRM fail → retry CRM → still broken → manual reconciliation flag set → ticket NOT marked resolved
- billing → 5 consecutive 500s → circuit OPEN → new tickets routed to human
- budget exceeded → workflow stops → escalates (no infinite loop)
- Outbox: decision + side-effect intent recorded atomically

---

### M2-P5 · Audit Log

**Status:** PENDING

**Deliverables:**
- [ ] `audit_log` table (append-only — no UPDATE/DELETE privileges for app user)
- [ ] All fields: id, timestamp, run_id, ticket_id, actor_type, actor_id, event, tool, args_hash, args_redacted, policy_rule, policy_version, idempotency_key, result_status, trace_id, prev_hash, row_hash
- [ ] All 11 event types emitted correctly
- [ ] Hash chain: `row_hash = SHA256(prev_hash + row_content)`
- [ ] PII redaction: email, phone, payment info masked before storage
- [ ] `GET /api/audit` — filtered timeline
- [ ] `GET /api/audit/tickets/{id}` — full ticket audit trail
- [ ] `GET /api/audit/export/{id}` — JSON + CSV export

**Verification:**
- Full normal-refund scenario → audit trail has all 10+ expected events in order
- Modify a row directly in DB → chain verification script detects break
- Email addresses in audit args → appear as `j***@acme.com` (redacted)
- Export includes all events, readable by Finance/Security

---

### M2-P6 · Langfuse Integration

**Status:** PENDING

**Deliverables:**
- [ ] `backend/app/observability/langfuse_client.py` — Langfuse SDK wrapper
- [ ] Trace: every workflow run → root trace with ticket_id, run_id
- [ ] Span: every LangGraph node
- [ ] Span: every Groq API call (model, prompt_tokens, completion_tokens, latency, estimated_cost)
- [ ] Span: every MCP tool call
- [ ] Span: every policy evaluation result
- [ ] Score: reviewer approval/rejection → Langfuse score event
- [ ] `config/model_prices.yaml` — token pricing for cost estimation
- [ ] Reviewer feedback → Langfuse dataset → regression test pipeline

**Verification:**
- Run normal refund → Langfuse UI shows full trace with all spans
- Token cost visible per ticket run
- No GROQ_API_KEY, DB passwords, or unredacted PII in any Langfuse event
- Rejection event → creates Langfuse score → can export as eval dataset

---

### M2-P7 · Full Eval Suite + Naive Baseline + Ablations

**Status:** PENDING

**Deliverables:**
- [ ] 20 additional scenarios (total: 30+ YAML files in `evals/scenarios/`)
- [ ] Final breakdown: 6 auto, 8 approval, 5 forbidden, 7 adversarial, 4 reliability
- [ ] `evals/redteam/` — 15-20 adversarial scenarios: ticket injection, CRM injection, requester spoofing, duplicate refund, fake authorization, wrong account, admin access, legal hold, large refund, malicious identifiers
- [ ] `evals/baselines/naive_agent.py` — Groq + prompt-only safety + direct tools (no gateway)
- [ ] Comparison matrix: ResolveOps vs Naive Agent (unsafe actions, injection success, duplicate effects, policy accuracy, latency, cost)
- [ ] Ablation tests: remove provenance / remove identity / remove approval hash / remove idempotency
- [ ] Ablation matrix: `Component → Scenarios It Protects`
- [ ] All scenarios run 5x with variance reporting

**Verification:**
- Naive agent fails ≥ 5 adversarial scenarios that ResolveOps passes
- Each ablation shows exactly which attack becomes possible
- Zero unsafe actions or duplicate side-effects in ResolveOps runs
- Evaluation held-out set never used for tuning

---

## M2 Completion Checklist

- [ ] No path exists from LangGraph to any backend except through the gateway
- [ ] All 12 gateway steps verified individually
- [ ] Provenance failure blocks invented IDs (tested)
- [ ] Identity mismatch blocks wrong-requester actions (tested)
- [ ] Approval hash mismatch blocks edited actions (tested)
- [ ] Kill switch stops all execution immediately (tested)
- [ ] Zero duplicate side-effects across 30 scenarios
- [ ] Timeout-after-commit → read-back → no duplicate (tested)
- [ ] Audit trail: full ticket reconstructable from log alone
- [ ] Hash chain: tamper detection works
- [ ] Naive baseline comparison complete
- [ ] Ablation matrix complete
- [ ] All 30+ scenarios pass (5 runs each)
- [ ] Langfuse traces visible for all scenarios

**Unlock M3:** All M2 items above checked.
