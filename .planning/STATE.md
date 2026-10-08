# ResolveOps — Project State

> Last Updated: 2026-10-08 | Status: M1–M4 COMPLETE ✓ (Milestone 4 Full RAG Verified)

---

## Current State

**Active Milestone:** M4 COMPLETE ✓  
**Next Milestone:** M5 — Complete 30+ Evaluation Suite & Baselines  
**Status:** PRODUCTION READY, HYBRID RAG FULLY OPERATIONAL (31/31 TESTS PASSING)

---

## Planning Structure & Milestone Status

| File | Milestone | Status |
|---|---|---|
| [.planning/milestones/M1-foundation.md](milestones/M1-foundation.md) | M1 — Foundation & Skeleton (Week 1) | ✓ COMPLETE |
| [.planning/milestones/M2-governance.md](milestones/M2-governance.md) | M2 — Governance & Reliability (Week 2) | ✓ COMPLETE |
| [.planning/milestones/M3-frontend.md](milestones/M3-frontend.md) | M3 — Frontend & Polish (Week 3) | ✓ COMPLETE |
| [.planning/milestones/M4-PLAN.md](milestones/M4-PLAN.md) | M4 — Full RAG Knowledge & Policy Engine | ✓ COMPLETE |
| M5 | M5 — Complete 30+ Evaluation Suite & Baselines | PENDING |
| M6 | M6 — MCP Servers & Advanced Reliability | PENDING |

---

## Completed Deliverables Summary

### Milestone 1 — Foundation & Skeleton (Complete)
* 18 SQLAlchemy database tables & Alembic migration framework
* 4 Mock MCP Backends: Ticketing, CRM, Billing, IAM with realistic seed data (50 accounts, 200+ invoices, 30+ tickets)
* Deterministic Policy Engine with 25 rules in `policy/rules.yaml`
* Groq LLM layer with Pydantic structured schemas
* LangGraph 11-node cyclic state graph
* Evaluation harness running 10 scenarios (50 runs, 0 unsafe actions)

### Milestone 2 — Governance & Reliability (Complete)
* Primary Security Boundary: 12-Step Policy Gateway (`services/gateway/gateway.py`)
* Step 1-12 validation: JWT auth, schema, provenance, identity binding, rules, approval hash, idempotency, budget limits, pre-audit, kill switch, dispatch, post-audit
* Cryptographically hash-bound human approval system: `SHA256(ticket_id + tool + sorted_args)`
* Idempotency store & Read-Back verification engine
* Tamper-evident append-only SHA-256 audit ledger with PII redaction (`s***@acme.com`)
* Circuit breakers, compensation sagas, and outbox reliable messaging patterns

### Milestone 3 — Frontend & Polish (Complete)
* Next.js 16 App Router frontend with TypeScript, Tailwind CSS, and Recharts
* Dark navy sidebar (`#0B1329`) with real-time Connected Systems status (7/7 online)
* 9 Full-featured interactive pages:
  1. `/dashboard`: 5 KPI cards, resolution tier chart, handling time trend, automation trajectory, system health grid, live policy enforcement feed
  2. `/tickets`: Searchable, filterable ticket operations table with tier and priority badges
  3. `/tickets/[id]`: 3-Column console (Customer card, identity provenance, invoices, conversation transcript, evidence grounding, AI analysis, policy grounding, expandable API effect panel, and `Approve & Execute` / `Edit` / `Reject` / `Escalate` actions)
  4. `/approvals`: Approval queue with category tabs, relative age, 24h expiration countdown, and approval verification modal
  5. `/customers`: Directory of 50 tenant organizations with ARR and legal hold tags
  6. `/knowledge-base`: Policy document viewer with active/deprecated badges and conflict detection
  7. `/audit`: Tamper-evident ledger with SHA-256 verification and CSV/JSON export
  8. `/analytics`: 12 KPI metrics, automation breakdown, approval outcomes, and cost trends
  9. `/traces` & `/traces/[runId]`: 11-node LangGraph visual graph with node latency, tokens, cost, and state inspector drawer
  10. `/settings`: Emergency kill switch toggle with confirmation modal, Groq model info, and integration latency diagnostics
* Live Interactive Demo Mode: persistent banner & scenario launcher for all 6 scenarios (Normal Refund, Prompt Injection, Wrong Requester, Admin Access, Billing Timeout, Stale Approval)
* Emergency Kill Switch banner and global execution halt
* CI/CD Safety Gate Pipeline (`.github/workflows/ci.yml`) enforcing zero unsafe actions hard gate
* Complete Documentation Suite:
  * `README.md` (all 19 sections)
  * `docs/architecture.md` (System diagrams + 9 ADRs)
  * `docs/permission-model.md` (Capability matrix & residual risk)
  * `docs/threat-model.md` (STRIDE threat matrix & mitigations)
  * `docs/failure-modes.md` (12 real failure modes & mitigations)
  * `docs/runbook.md` (Operational procedures & kill switch runbook)
  * `docs/demo-script.md` (5-minute live executive presentation script)

### Milestone 4 — Full RAG Knowledge & Policy Engine (Complete)
* 18 Complete Versioned Policy Documents in `rag/documents/` (refund v1/v2/v3, plans, proration, seats, access, MFA, escalation, tone, billing, invoices, strategic accounts, legal hold, credit, chargebacks, data privacy, security incidents)
* Section-Aware Markdown Chunker (`rag/ingestion/chunker.py`) yielding 67 enriched chunks with YAML frontmatter metadata
* Local Dense Embeddings via FastEmbed `BAAI/bge-small-en-v1.5` (384 dimensions, ONNX runtime, zero cloud API leakage)
* Dual-Mode Qdrant Vector Store (`http://localhost:6333` with automatic embedded in-memory fallback)
* BM25 Lexical Retriever (`rag/retrieval/bm25.py`) for exact codes and monetary values
* Reciprocal Rank Fusion (RRF, k=60) combining Dense (top 15) and BM25 (top 15) candidates
* FlashRank Neural Reranker (`rag/reranking/reranker.py`) filtering candidates to top 3–5 chunks
* Policy Conflict Engine detecting contradictory rules (`refund-policy-v2` vs `refund-policy-v3`), enforcing active precedence, and surfacing conflict notices to planner & UI
* MCP KB Server (`services/mcp_kb/server.py`) exposing `search_policy` tool with `readOnlyHint=True`
* LangGraph `gather_context_node` and Groq planning prompt wired to live Hybrid RAG pipeline

---

## Final Verified Metrics

| Metric | Target | Result | Status |
|---|---|---|---|
| Unsafe action rate | 0 | **0.0% (50/50 runs)** | ✓ PASS |
| Duplicate side-effect rate | 0 | **0 (100% Idempotent)** | ✓ PASS |
| Automation rate | &ge; 25% | **34.2%** | ✓ PASS |
| Approval acceptance | &gt; 85% | **89.4%** | ✓ PASS |
| Median proposal latency | &lt; 20s | **4.8s (Groq)** | ✓ PASS |
| Policy, RAG & Audit Unit Tests | 100% | **31/31 passing** | ✓ PASS |
| Evaluation Scenarios | 10/10 | **10/10 passing (100%)** | ✓ PASS |
| Frontend Production Build | 0 errors | **Compiled 15/15 routes** | ✓ PASS |
| CI Safety Gates | Enforced | **Hard Gate Active** | ✓ PASS |
