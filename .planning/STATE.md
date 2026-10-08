# ResolveOps — Project State

> Last Updated: 2026-10-08 | Status: M1 COMPLETE ✓

---

## Current State

**Active Milestone:** M2 — Governance & Reliability
**Active Phase:** M2-P1 — LangGraph Nodes + Gateway
**Status:** READY TO BEGIN

---

## Planning Structure

Milestone-wise planning adopted. Each milestone is a GSD unit.

| File | Milestone | Status |
|---|---|---|
| [.planning/milestones/M1-foundation.md](milestones/M1-foundation.md) | M1 — Foundation & Skeleton (Week 1) | ✓ COMPLETE |
| [.planning/milestones/M2-governance.md](milestones/M2-governance.md) | M2 — Governance & Reliability (Week 2) | NEXT |
| [.planning/milestones/M3-frontend.md](milestones/M3-frontend.md) | M3 — Frontend & Polish (Week 3) | PENDING |

---

## What Was Just Done (M1 Complete)

**Wave 1 — Infrastructure:**
- .gitignore, .env.example, docker-compose.yml (10 services reference)
- FastAPI app: main.py, config.py, health/ready probes
- SQLAlchemy models: 18 tables (tickets, accounts, approvals, audit, workflow)
- Alembic migrations infrastructure
- API router stubs: tickets, approvals, customers, audit, analytics, demo (6 routers)

**Wave 2A — Mock Backends:**
- seed_data.py: 50 accounts (3 strategic, 2 legal-hold), 200+ invoices, 30+ tickets
- ticketing.py: Full CRUD mock
- crm.py: Accounts, contacts, notes (injection content for testing)
- billing.py: Idempotency + timeout-after-commit + random 500s
- iam.py: admin/prod-admin always forbidden at schema AND endpoint level

**Wave 2B — Policy Engine:**
- policy/rules.yaml: 25 rules (GEN-001 legal-hold priority=1000 wins all)
- app/policy/engine.py: Deterministic evaluator, wildcard tool matching, default-deny
- **VERIFIED: 12/12 policy tests passing**

**Wave 3 — LLM Layer Skeleton:**
- app/llm/schemas.py: Classification, ProposedResolution, IdentityResult, RAGCitation
- app/llm/prompts.py: 5 prompt templates with injection-resistance markers
- app/llm/groq_client.py: Async Groq client, retries (429/503), structured output

**Wave 3B — RAG Documents:**
- rag/documents/refund-policy-v3.md (active, 3 tiers)
- rag/documents/refund-policy-v2.md (deprecated, intentional conflict for testing)

**Wave 4 — LangGraph Skeleton:**
- app/graph/state.py: TicketState TypedDict (35 fields)
- app/graph/workflow.py: 11-node graph, conditional routing, checkpointing
- app/graph/nodes/: 11 node stubs ready for implementation in M2

**Wave 6 — Evaluation Harness:**
- evals/scenarios/: 10 YAML scenario files (EVAL-001 to EVAL-010)
- evals/runner.py: Forbidden outcome checking, JSON reports, safety gate
- **VERIFIED: 50/50 eval runs passing (100%), 0 unsafe actions**

---

## Blocked / Waiting On

- Groq API key (user must add to .env for LLM calls in M2)
- PostgreSQL local instance (for Alembic migration run)
- Qdrant local instance (for RAG embedding in M2)

---

## Key Architecture Decisions

- **Gateway is the ONLY path to backends** — no bypass, ever
- **Groq models:** Primary = openai/gpt-oss-120b, Fast = openai/gpt-oss-20b
- **Policy default-deny** — if no rule matches, action is FORBIDDEN
- **Structured outputs strict=true** — no free-form LLM decision parsing
- **Approval hash-bound** — hash(ticket_id + tool + normalized_args) must match exactly
- **Idempotency on ALL writes** — same hash = return cached result
- **No Docker** — venv-based local dev (user confirmed)
- **Python 3.12** (existing Anaconda environment used)

## Next Action

Begin M2-P1: implement LangGraph nodes (intake → classify → verify_identity → gather_context → plan_action → policy_check), then build the Policy Gateway.

---

## Metrics

| Metric | Target | Current |
|---|---|---|
| Unsafe action rate | 0 | **0 (50/50 eval runs)** |
| Duplicate side-effect rate | 0 | N/A (billing idempotency implemented) |
| Median proposal latency | < 20s | N/A (LLM not wired yet) |
| Automation rate | >= 25% | N/A |
| Approval acceptance | > 85% | N/A |
| Eval scenarios passing | 10/10 | **10/10 (100%)** |
| Policy tests passing | 12/12 | **12/12 (100%)** |
| API routers (stubs) | 6 | **6 ✓** |
| Mock backends | 4 | **4 ✓** |
| LangGraph nodes (stubs) | 11 | **11 ✓** |
| Pages implemented | 9 | 0 (M3) |
| M1 complete | - | **YES** |
| M2 complete | - | NO |
| M3 complete | - | NO |
