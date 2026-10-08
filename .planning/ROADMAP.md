# ResolveOps — Project Roadmap

> Version: 1.0 | Status: ACTIVE | Last Updated: 2026-10-08

---

## Milestone 1: Foundation & Skeleton (Week 1)

**Goal:** Working skeleton with all major systems wired together and first 10 evaluation scenarios passing.

### Phase 1.1 — Repository & Infrastructure Setup
**Status:** PENDING

**Deliverables:**
- [ ] Git repo with proper .gitignore
- [ ] docker-compose.yml (Postgres, Redis, Qdrant, Langfuse)
- [ ] .env.example with all required variables
- [ ] Alembic migrations for all tables
- [ ] FastAPI app skeleton with health/ready endpoints
- [ ] Next.js app skeleton with App Router
- [ ] CI pipeline skeleton (lint, type check, test)

**Verification:**
- `docker compose up` brings all services healthy
- `GET /health` returns 200
- `GET /ready` returns 200 with all dependencies

---

### Phase 1.2 — Mock Backend Systems
**Status:** PENDING

**Deliverables:**
- [ ] Mock Ticketing system (GET /tickets, POST /tickets/{id}/comments, PATCH /tickets/{id})
- [ ] Mock CRM system (GET /accounts, GET /contacts, GET /accounts/{id}/notes)
- [ ] Mock Billing system (GET invoices/subscriptions, POST refunds/credits with idempotency)
- [ ] Mock IAM system (GET users/grants, POST access-grants, POST mfa-reset)
- [ ] Test data: 50 accounts, 200 invoices, 30+ tickets
- [ ] Strategic accounts, legal-hold accounts, bad requester cases
- [ ] Billing mock with random 500s, latency, timeout-after-commit simulation

**Verification:**
- All mock endpoints return realistic data
- Billing mock correctly enforces idempotency keys
- Duplicate refund returns original result, not a new one

---

### Phase 1.3 — Policy Engine & Rules
**Status:** PENDING

**Deliverables:**
- [ ] policy/rules.yaml with all defined rules (REF-001, REF-002, REF-099, ACC-001, ACC-099, GEN-001, TKT-001)
- [ ] Policy engine implementation (evaluate_action function)
- [ ] Default deny for unknown tools
- [ ] Support for conditional rule evaluation (lte, gt, in operators)
- [ ] Policy version metadata

**Verification:**
- refund $30 for non-strategic account → approval (REF-001)
- refund $600 for any account → approval:finance (REF-002)
- refund $600 for strategic account → forbidden (GEN-001 + REF-002)
- refund $50,001 → forbidden (REF-099)
- grant viewer access, authorized contact → approval (ACC-001)
- grant admin access → forbidden (ACC-099)
- any action on legal_hold account → forbidden (GEN-001)
- unknown tool → forbidden

---

### Phase 1.4 — Groq Integration & LLM Service
**Status:** PENDING

**Deliverables:**
- [ ] backend/app/llm/groq_client.py — Groq API client with retries, timeouts, structured outputs
- [ ] backend/app/llm/service.py — LLM service layer
- [ ] backend/app/llm/prompts.py — Classification, planning, summarization, reply drafting prompts
- [ ] backend/app/llm/schemas.py — Pydantic schemas for all LLM outputs
- [ ] backend/app/llm/config.py — Model configuration
- [ ] Classification using gpt-oss-20b returning category/urgency/sentiment/confidence
- [ ] Planning using gpt-oss-120b returning ProposedResolution

**Verification:**
- Classification returns valid JSON for sample tickets
- Low confidence (< 0.7) triggers human review flag
- Structured output validation rejects malformed responses
- Groq key not accessible from frontend

---

### Phase 1.5 — RAG Pipeline
**Status:** PENDING

**Deliverables:**
- [ ] 15-25 policy documents in rag/documents/ (markdown with frontmatter)
- [ ] Intentionally contradictory refund-policy-v2 and refund-policy-v3
- [ ] rag/ingestion/ — Cleaning, section-aware chunking, metadata extraction
- [ ] bge-m3 (or equivalent) local embedding model integration
- [ ] Qdrant collection setup with full metadata schema
- [ ] rag/retrieval/ — Dense retrieval via Qdrant
- [ ] BM25 lexical retrieval implementation
- [ ] Candidate merge logic
- [ ] FlashRank reranker integration
- [ ] Top 3-5 chunks returned with citation metadata

**Verification:**
- Query "refund limit" returns chunks from refund-policy-v3 (active)
- Policy conflict detection works for v2 vs v3
- All chunks include: chunk_id, document_id, section, version, effective_date, status
- Ingestion pipeline is idempotent

---

### Phase 1.6 — LangGraph Workflow
**Status:** PENDING

**Deliverables:**
- [ ] TicketState TypedDict with all fields
- [ ] All 11 nodes implemented: intake, classify, verify_identity, gather_context, plan_action, policy_check, approval_interrupt, execute, verify_outcome, draft_reply, close
- [ ] Postgres checkpointing via LangGraph
- [ ] Workflow routing logic (auto/approval/forbidden branches)
- [ ] Basic escalation path

**Verification:**
- Full happy path runs end-to-end for normal refund scenario
- Workflow state persists in Postgres
- Simulated crash during approval → resume from checkpoint
- Forbidden actions escalate correctly

---

### Phase 1.7 — MCP Servers
**Status:** PENDING

**Deliverables:**
- [ ] mcp_ticketing — get_ticket, list_requester_tickets, add_internal_note, set_tags, send_public_reply
- [ ] mcp_crm — get_account, find_contact, get_account_notes, update_contact_email
- [ ] mcp_billing — get_invoice, list_invoices, get_subscription, preview_plan_change, issue_refund, issue_credit, change_plan, pause_subscription
- [ ] mcp_access — get_user, list_grants, grant_access, reset_mfa
- [ ] mcp_kb — search_policy
- [ ] Typed Pydantic schemas for all tools
- [ ] readOnlyHint, destructiveHint, idempotentHint annotations
- [ ] Deliberate exclusions: delete_account, issue_unbounded_refund, grant_admin, etc.

**Verification:**
- All MCP tools call mock backends correctly
- Destructive tools require explicit arguments
- Admin grant tools don't exist in any MCP server
- Excluded tools documented in docs/permission-model.md

---

### Phase 1.8 — First 10 Evaluation Scenarios
**Status:** PENDING

**Deliverables:**
- [ ] evals/scenarios/ with 10 YAML scenario definitions
- [ ] Scenario runner script
- [ ] Auto-tier: 3 scenarios
- [ ] Approval-tier: 3 scenarios
- [ ] Forbidden-tier: 2 scenarios
- [ ] Adversarial: 2 scenarios

**Verification:**
- All 10 scenarios have expected_tier and forbidden_outcomes defined before execution
- Scenarios run 5 times each and report pass/fail rate

---

## Milestone 2: Governance & Reliability (Week 2)

**Goal:** All security controls active, reliability patterns implemented, 30+ evaluation scenarios, naive baseline for comparison.

### Phase 2.1 — Policy Gateway (Primary Security Boundary)
**Status:** PENDING

**Deliverables:**
- [ ] services/gateway/ — Full gateway implementation
- [ ] Step 1: Authenticate workflow run (JWT validation)
- [ ] Step 2: Schema validation (Pydantic)
- [ ] Step 3: Provenance validation (all IDs from trusted sources)
- [ ] Step 4: Identity binding (requester linked to target account)
- [ ] Step 5: Policy evaluation (rules.yaml)
- [ ] Step 6: Approval validation (hash check)
- [ ] Step 7: Idempotency check (hash → execution result)
- [ ] Step 8: Rate/budget limit check
- [ ] Step 9: Audit start event
- [ ] Step 10: Kill switch check
- [ ] Step 11: Execute
- [ ] Step 12: Audit result event
- [ ] Short-lived scoped JWT tokens (ticket_id, tool, run_id, exp)
- [ ] Prompt injection detection and flagging

**Verification:**
- Agent can ONLY call backends through the gateway
- Provenance failure blocks injection of invented IDs
- Identity mismatch blocks action for wrong requester
- Approval hash mismatch blocks edited action
- Kill switch immediately stops all execution
- Every gateway call produces audit events

---

### Phase 2.2 — Approval System
**Status:** PENDING

**Deliverables:**
- [ ] Approval queue database table
- [ ] API: GET /api/approvals, POST /api/approvals/{id}/approve, /reject, /edit, /escalate
- [ ] Approval hash: hash(ticket_id + tool + normalized_arguments)
- [ ] Approval expiration: 24 hours
- [ ] State change invalidation logic
- [ ] Edit → revalidate → re-approve flow
- [ ] Escalation routing

**Verification:**
- Approving $30 refund cannot execute $300 refund
- Approval expires after 24 hours
- Account state change invalidates pending approval
- Edit requires full revalidation before execution

---

### Phase 2.3 — Idempotency & Read-Back
**Status:** PENDING

**Deliverables:**
- [ ] Idempotency key generation: hash(ticket_id + tool + normalized_arguments)
- [ ] Idempotency store in Redis/Postgres
- [ ] Read-back logic for unknown-outcome writes
- [ ] Duplicate detection before any financial write
- [ ] Billing mock timeout-after-commit simulation

**Verification:**
- Duplicate refund request returns original result
- Timeout-after-commit → read-back finds existing refund → no duplicate
- Zero duplicate side-effects across all 30 scenarios

---

### Phase 2.4 — Reliability: Saga, Retries, Circuit Breakers
**Status:** PENDING

**Deliverables:**
- [ ] Saga implementation for multi-step actions
- [ ] Compensation handlers for partial failures
- [ ] Exponential backoff with jitter for transient errors
- [ ] Circuit breaker for each backend service
- [ ] Outbox pattern for atomic side-effect intent
- [ ] Outbox processor for reliable dispatch
- [ ] Partial failure detection and manual reconciliation routing

**Verification:**
- Billing success + CRM failure → retry CRM → if still broken → manual reconciliation flag
- Circuit breaker trips after 5 consecutive failures
- Degraded service routes tickets to humans
- No false ticket resolution on partial failure

---

### Phase 2.5 — Audit Log
**Status:** PENDING

**Deliverables:**
- [ ] audit_log table (append-only, no UPDATE/DELETE)
- [ ] All fields: id, timestamp, run_id, ticket_id, actor_type, actor_id, event, tool, args_hash, args_redacted, policy_rule, policy_version, idempotency_key, result_status, trace_id, prev_hash, row_hash
- [ ] All event types: proposed, policy_decision, approval_requested, approved, edited, rejected, executed, verified, failed, compensated, escalated
- [ ] Hash chain: prev_hash → row_hash
- [ ] PII redaction before storage
- [ ] Export API (JSON + CSV)

**Verification:**
- Full ticket audit trail reconstructable from audit_log alone
- Tampered row detectable via hash chain break
- PII fields redacted in all audit records
- Export includes all events for ticket

---

### Phase 2.6 — Langfuse Integration
**Status:** PENDING

**Deliverables:**
- [ ] Langfuse tracing for every workflow node
- [ ] Langfuse trace for every Groq request (model, tokens, latency, cost)
- [ ] Langfuse trace for every tool call
- [ ] Langfuse trace for policy decisions
- [ ] Metadata: ticket_id, run_id, policy_rule, policy_version, prompt_version, model_version
- [ ] PII redaction in Langfuse payloads
- [ ] Reviewer feedback → Langfuse score → evaluation dataset pipeline

**Verification:**
- Every ticket run traceable in Langfuse UI
- Token usage and estimated cost logged per ticket
- No API keys or secrets in Langfuse logs

---

### Phase 2.7 — Remaining 20+ Evaluation Scenarios + Naive Baseline
**Status:** PENDING

**Deliverables:**
- [ ] 20 additional scenarios (total 30+)
- [ ] 15-20 adversarial/red-team scenarios in evals/redteam/
- [ ] Naive Agent implementation (Groq + prompt-only safety + direct tools)
- [ ] Comparison matrix: ResolveOps vs Naive Agent
- [ ] Ablation tests: remove provenance, remove identity, remove approval hash, remove idempotency
- [ ] Scenario runner with 5-run repeat and pass/fail variance reporting

**Verification:**
- 30+ scenarios defined with expected results before execution
- Naive agent fails adversarial scenarios that ResolveOps passes
- Ablation shows which control prevents which attack

---

## Milestone 3: Frontend & Final Polish (Week 3)

**Goal:** Full enterprise frontend, final hardening, CI safety gates, complete documentation, demo-ready.

### Phase 3.1 — Frontend Core Shell & Design System
**Status:** PENDING

**Deliverables:**
- [ ] Next.js App Router project setup
- [ ] Tailwind config with design tokens (colors, spacing, typography)
- [ ] shadcn/ui component configuration
- [ ] Global layout: header + sidebar + main content
- [ ] Sidebar navigation (all 9 sections + connected systems status)
- [ ] Dark navy sidebar, light/gray content area
- [ ] Google Fonts (Inter or similar)
- [ ] Loading skeleton components
- [ ] Error, empty, forbidden state components

---

### Phase 3.2 — Dashboard Page
**Status:** PENDING

**Deliverables:**
- [ ] Route: /dashboard
- [ ] KPI cards: Tickets Today, Automation Rate, Approval Acceptance, Median Proposal Time, Unsafe Actions
- [ ] Charts: Tickets by Resolution Tier, Average Handling Time, Automation Trend, System Health
- [ ] Recent activity feed
- [ ] System health status
- [ ] Kill switch state display
- [ ] Demo mode banner

---

### Phase 3.3 — Tickets List & Ticket Detail Pages
**Status:** PENDING

**Deliverables:**
- [ ] Route: /tickets — Table with filters and search
- [ ] Route: /tickets/[id] — Three-column layout
- [ ] Left column: Customer Context, Identity, Invoices, Related Tickets
- [ ] Center column: Conversation, AI Activity, Evidence
- [ ] Right column: AI Analysis, Proposed Action, Policy, Risk, Audit
- [ ] Identity verification card (verified/not-verified states)
- [ ] Policy display with source citation
- [ ] Exact API effect expandable panel
- [ ] Approve/Edit/Reject/Escalate action buttons
- [ ] Policy conflict warning display
- [ ] Injection attempt flag display

---

### Phase 3.4 — Approval Queue Page
**Status:** PENDING

**Deliverables:**
- [ ] Route: /approvals
- [ ] Tabs: All, Financial, Security, Low Confidence, Conflicts
- [ ] Table with all approval metadata
- [ ] Inline approve/reject actions
- [ ] Age display (time since approval requested)
- [ ] Expiration countdown
- [ ] Stale approval detection UI

---

### Phase 3.5 — Customers, Knowledge Base, Audit Pages
**Status:** PENDING

**Deliverables:**
- [ ] Route: /customers — table + customer detail with 7 tabs
- [ ] Route: /knowledge-base — document list + viewer + conflict warnings
- [ ] Route: /audit — filtered timeline with full event detail + export

---

### Phase 3.6 — Analytics, Traces, Settings Pages
**Status:** PENDING

**Deliverables:**
- [ ] Route: /analytics — all metrics + charts (Recharts)
- [ ] Route: /traces/[runId] — visual workflow node graph with status/latency/tokens/cost per node
- [ ] Route: /settings — AI config, policy version, integrations, kill switch

---

### Phase 3.7 — Demo Mode
**Status:** PENDING

**Deliverables:**
- [ ] DEMO MODE banner
- [ ] 6 demo scenario buttons: Normal Refund, Prompt Injection, Wrong Requester, Admin Access, Billing Timeout, Stale Approval
- [ ] One-click scenario seeding and execution
- [ ] Visual feedback during scenario execution

---

### Phase 3.8 — CI/CD Safety Gates & Final Documentation
**Status:** PENDING

**Deliverables:**
- [ ] GitHub Actions: lint → typecheck → unit → policy → gateway → integration → scenario → security → eval → safety gates
- [ ] Hard fail if unsafe_action_rate > 0 or duplicate_side_effect_rate > 0
- [ ] README.md with all 19 sections
- [ ] docs/architecture.md with ADRs
- [ ] docs/permission-model.md
- [ ] docs/threat-model.md
- [ ] docs/failure-modes.md
- [ ] docs/runbook.md
- [ ] docs/demo-script.md
- [ ] Docker Compose polish (health checks, restart policies)
- [ ] Final evaluation run with honest results

---

## Definition of Done

The project is complete when ALL of the following are verified:

### Infrastructure
- [ ] docker compose up brings all services healthy
- [ ] Groq integration works with both models
- [ ] Structured outputs enforced

### Security Controls
- [ ] Groq key protected server-side
- [ ] Gateway is mandatory (no bypass path)
- [ ] Identity is deterministic
- [ ] Provenance checks work
- [ ] Approval binding works
- [ ] Stale approval invalidation works

### Reliability Controls
- [ ] Idempotency works
- [ ] Timeout-after-commit → read-back works
- [ ] Saga works
- [ ] Circuit breakers work
- [ ] Postgres checkpointing / crash resume works

### Data Systems
- [ ] RAG works (hybrid retrieval + reranking)
- [ ] Qdrant works
- [ ] Policy conflicts handled
- [ ] Policy documents versioned

### Agent Workflow
- [ ] LangGraph workflow runs end-to-end
- [ ] MCP servers work
- [ ] All demo scenarios work

### Evaluation
- [ ] Audit log works with hash chaining
- [ ] Kill switch works
- [ ] Red-team suite (30+ scenarios) works
- [ ] Naive baseline comparison done
- [ ] Ablation tests done
- [ ] Repeated evaluation (5x) done
- [ ] CI safety gates pass

### Frontend
- [ ] All 9 pages work
- [ ] Demo mode works
- [ ] Langfuse traces visible

### Documentation
- [ ] All 7 docs complete
- [ ] README with 19 sections complete
- [ ] Measured results reported honestly (N/A if not measured)
- [ ] 5-minute demo works
