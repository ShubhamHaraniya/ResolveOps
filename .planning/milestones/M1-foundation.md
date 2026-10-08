# M1 — Foundation & Skeleton

> Milestone: 1 of 3 | Timeline: Week 1 | Status: PENDING

**Goal:** Working skeleton with all major systems wired together and first 10 evaluation scenarios passing.

---

## Phases

### M1-P1 · Repo & Infrastructure Setup

**Status:** PENDING

**Deliverables:**
- [ ] `.gitignore` (Python, Node, env files, planning scratch)
- [ ] `docker-compose.yml` — Postgres, Redis, Qdrant, Langfuse services with health checks
- [ ] `.env.example` — all required variables (GROQ_API_KEY, DB, Qdrant, Redis, Langfuse)
- [ ] `backend/` — FastAPI skeleton with `GET /health` and `GET /ready`
- [ ] `backend/app/db/` — SQLAlchemy models + Alembic migrations for all tables
- [ ] `frontend/` — Next.js 14 App Router skeleton
- [ ] `.github/workflows/ci.yml` — lint → typecheck → test skeleton

**Verification:**
- `docker compose up` → all services show healthy
- `GET /health` → 200 `{"status": "ok"}`
- `GET /ready` → 200 with all dependency statuses
- Alembic `upgrade head` applies without errors

---

### M1-P2 · Mock Backend Systems

**Status:** PENDING

**Deliverables:**
- [ ] `services/mocks/ticketing.py` — GET /tickets/{id}, GET /tickets?requester=, POST /tickets/{id}/comments, PATCH /tickets/{id}
- [ ] `services/mocks/crm.py` — GET /accounts/{id}, GET /contacts?email=, GET /accounts/{id}/notes, PATCH /contacts/{id}
- [ ] `services/mocks/billing.py` — GET invoices/subscriptions, POST refunds/credits (idempotency-key), proration, random 500s, latency, timeout-after-commit
- [ ] `services/mocks/iam.py` — GET /users/{email}, GET /grants, POST /access-grants (viewer/member only), POST /mfa-reset
- [ ] `tests/data/seed.py` — 50 accounts, 200 invoices, 30+ tickets, strategic accounts, legal-hold accounts, bad-requester cases, injection cases

**Verification:**
- Billing mock: same idempotency-key → same result (no duplicate)
- IAM mock: `admin` role grant → 403 Forbidden
- CRM notes endpoint: returns potentially malicious content (for injection testing)
- All endpoints return realistic data matching schema

---

### M1-P3 · Policy Engine & rules.yaml

**Status:** PENDING

**Deliverables:**
- [ ] `policy/rules.yaml` — all rules: REF-001, REF-002, REF-099, ACC-001, ACC-099, GEN-001, TKT-001
- [ ] `backend/app/policy/engine.py` — `evaluate_action(tool, args, context) -> PolicyDecision`
- [ ] Default-deny: unknown tool → forbidden
- [ ] Condition operators: `lte`, `gt`, `in`, `eq`
- [ ] Account flag checks: `account.strategic`, `account.legal_hold`
- [ ] Policy version metadata support

**Verification (must all pass):**

| Scenario | Expected |
|---|---|
| Refund $30, non-strategic | `approval:support_agent` (REF-001) |
| Refund $600 | `approval:support_lead` (REF-002) |
| Refund $600, strategic account | `forbidden` (GEN-001 overrides) |
| Refund $50,001 | `forbidden` (REF-099) |
| Grant `viewer`, authorized contact | `approval:security_reviewer` (ACC-001) |
| Grant `admin` | `forbidden` (ACC-099) |
| Any action, legal_hold=true | `forbidden` (GEN-001) |
| Unknown tool | `forbidden` (default-deny) |

---

### M1-P4 · Groq Integration & LLM Service

**Status:** PENDING

**Deliverables:**
- [ ] `backend/app/llm/groq_client.py` — async Groq client (retries, timeouts, structured outputs, token tracking)
- [ ] `backend/app/llm/service.py` — classify_ticket(), plan_action(), draft_reply()
- [ ] `backend/app/llm/prompts.py` — 4 prompt templates (classification, planning, summarization, reply)
- [ ] `backend/app/llm/schemas.py` — Classification, IdentityResult, ProposedAction, PolicyDecision, ProposedResolution Pydantic models
- [ ] `backend/app/llm/config.py` — model config from env vars
- [ ] Classification uses `GROQ_MODEL_FAST` (gpt-oss-20b)
- [ ] Planning uses `GROQ_MODEL_PRIMARY` (gpt-oss-120b)
- [ ] Strict structured outputs (strict=true where supported)

**Verification:**
- Classification returns valid `Classification` JSON for 5 sample tickets
- Confidence < 0.7 → `human_review` flag set
- GROQ_API_KEY not reachable from frontend (env check)
- Token usage logged per call

---

### M1-P5 · RAG Pipeline

**Status:** PENDING

**Deliverables:**
- [ ] `rag/documents/` — 15-25 policy docs in markdown with YAML frontmatter (version, status, effective_date, owner)
- [ ] Intentionally contradictory: `refund-policy-v2.md` (< $100 → approval) vs `refund-policy-v3.md` (< $50 → approval, status: active)
- [ ] `rag/ingestion/chunker.py` — section-aware chunking (preserves title, section, subsection)
- [ ] `rag/ingestion/embedder.py` — bge-m3 (or sentence-transformers equivalent) local embedding
- [ ] `rag/ingestion/indexer.py` — Qdrant upsert with full metadata
- [ ] `rag/retrieval/dense.py` — Qdrant dense search
- [ ] `rag/retrieval/bm25.py` — BM25 lexical search
- [ ] `rag/retrieval/merger.py` — candidate merge (dense + BM25)
- [ ] `rag/reranking/flashrank_reranker.py` — FlashRank reranker → top 3-5
- [ ] Citation metadata on every returned chunk

**Verification:**
- Query "refund limit" → chunks from refund-policy-v3 (active) ranked first
- v2 vs v3 conflict → conflict flag raised
- All chunks include: chunk_id, document_id, section, version, effective_date, status
- Ingestion is idempotent (re-run doesn't duplicate)

---

### M1-P6 · LangGraph Workflow

**Status:** PENDING

**Deliverables:**
- [ ] `backend/app/graph/state.py` — TicketState TypedDict (all fields)
- [ ] `backend/app/graph/nodes/` — 11 nodes: intake, classify, verify_identity, gather_context, plan_action, policy_check, approval_interrupt, execute, verify_outcome, draft_reply, close
- [ ] `backend/app/graph/workflow.py` — graph assembly with routing logic
- [ ] Postgres checkpointer (LangGraph SqliteSaver → PostgresSaver)
- [ ] Routing: auto → execute, approval → interrupt, forbidden → escalate

**Verification:**
- Normal refund scenario runs all 11 nodes in order
- State persists in Postgres checkpoint table
- Kill worker mid-run → restart → resumes from last checkpoint
- Forbidden action → escalates, does NOT execute

---

### M1-P7 · MCP Servers

**Status:** PENDING

**Deliverables:**
- [ ] `services/mcp_ticketing/` — 5 tools: get_ticket, list_requester_tickets, add_internal_note, set_tags, send_public_reply
- [ ] `services/mcp_crm/` — 4 tools: get_account, find_contact, get_account_notes, update_contact_email
- [ ] `services/mcp_billing/` — 8 tools: get_invoice, list_invoices, get_subscription, preview_plan_change, issue_refund, issue_credit, change_plan, pause_subscription
- [ ] `services/mcp_access/` — 4 tools: get_user, list_grants, grant_access, reset_mfa
- [ ] `services/mcp_kb/` — 1 tool: search_policy
- [ ] All tools: typed Pydantic schemas, readOnlyHint/destructiveHint/idempotentHint annotations
- [ ] `docs/permission-model.md` — documents 8 deliberately missing tools and rationale

**Verification:**
- `delete_account`, `issue_unbounded_refund`, `grant_admin`, `grant_prod_admin` do NOT exist as any tool
- `grant_access` with role `admin` → validation error (enum)
- All read tools have `readOnlyHint: true`
- `issue_refund` has `destructiveHint: true`, `idempotentHint: true`

---

### M1-P8 · First 10 Evaluation Scenarios

**Status:** PENDING

**Deliverables:**
- [ ] `evals/scenarios/` — 10 YAML scenario files with full spec (scenario_id, description, seed_state, ticket, expected_tier, expected_action, expected_arguments, forbidden_outcomes)
- [ ] 3 auto-tier, 3 approval-tier, 2 forbidden-tier, 2 adversarial scenarios
- [ ] `evals/runner.py` — scenario runner with 5-run repeat
- [ ] Pass/fail rate reporting per scenario

**Verification:**
- All 10 scenarios have expected results WRITTEN before execution
- Each scenario runs 5 times and reports pass rate
- Forbidden outcomes never occur in any run

---

## M1 Completion Checklist

- [ ] `docker compose up` → all 6 services healthy
- [ ] `GET /health` → 200
- [ ] Full normal-refund scenario runs end-to-end
- [ ] 10 evaluation scenarios pass (5 runs each)
- [ ] Workflow state survives simulated crash + restart
- [ ] Policy engine default-deny verified
- [ ] GROQ_API_KEY not accessible from frontend
- [ ] RAG returns policy citations with metadata

**Unlock M2:** All M1 items above checked.
