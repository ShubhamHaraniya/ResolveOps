# ResolveOps — Project Roadmap

> Version: 1.1 | Status: ACTIVE | Last Updated: 2026-10-08
> Structure: Milestone-driven. Each milestone is a GSD planning unit.

---

## Milestone Overview

| ID | Milestone | Timeline | Status | Phases |
|---|---|---|---|---|
| [M1](#milestone-1--foundation--skeleton) | Foundation & Skeleton | Week 1 | ✓ COMPLETE | 8 phases |
| [M2](#milestone-2--governance--reliability) | Governance & Reliability | Week 2 | ✓ COMPLETE | 7 phases |
| [M3](#milestone-3--frontend--polish) | Frontend & Polish | Week 3 | ✓ COMPLETE | 8 phases |
| [M4](#milestone-4--full-rag-knowledge--policy-engine) | Full RAG Knowledge & Policy Engine | Next | ✓ COMPLETE | 6 phases |
| [M5](#milestone-5--complete-30-evaluation-suite--baselines) | Complete 30+ Evaluation Suite & Baselines | Next | ✓ COMPLETE | 5 phases |
| [M6](#milestone-6--mcp-servers--advanced-reliability) | MCP Servers & Advanced Reliability | Next | READY TO EXECUTE | 5 phases |

**Active Milestone Plan:** `/gsd-execute-phase M6`


---

## Milestone 1 — Foundation & Skeleton

**Goal:** Working skeleton with all major systems wired together and first 10 eval scenarios passing.

**Plan file:** `.planning/milestones/M1-foundation.md`

### Phases

| Phase | Name | Key Output |
|---|---|---|
| M1-P1 | Repo & Infrastructure | Docker Compose, Postgres, Redis, Qdrant, Langfuse, CI skeleton |
| M1-P2 | Mock Backend Systems | Ticketing, CRM, Billing, IAM mocks with realistic test data |
| M1-P3 | Policy Engine | policy/rules.yaml + evaluator with default-deny |
| M1-P4 | Groq Integration | groq_client, LLM service, prompts, structured outputs |
| M1-P5 | RAG Pipeline | bge-m3, Qdrant, BM25, FlashRank, 15-25 policy docs |
| M1-P6 | LangGraph Workflow | 11 nodes, TicketState, Postgres checkpointing |
| M1-P7 | MCP Servers | 5 MCP servers (ticketing, crm, billing, access, kb) |
| M1-P8 | First 10 Eval Scenarios | Scenario runner, 10 YAML scenarios, 5-run repeat |

### M1 Definition of Done
- [ ] `docker compose up` → all services healthy
- [ ] `GET /health` returns 200
- [ ] Full happy-path (normal refund) runs end-to-end
- [ ] 10 scenarios pass (5 runs each)
- [ ] Workflow state survives simulated crash

---

## Milestone 2 — Governance & Reliability

**Goal:** All security controls active, all reliability patterns implemented, 30+ eval scenarios, naive baseline comparison done.

**Plan file:** `.planning/milestones/M2-governance.md`

### Phases

| Phase | Name | Key Output |
|---|---|---|
| M2-P1 | Policy Gateway | 12-step security boundary, JWT tokens, kill switch |
| M2-P2 | Approval System | Hash-bound approvals, expiration, state-change invalidation |
| M2-P3 | Idempotency & Read-Back | Idempotency store, read-back for unknown-outcome writes |
| M2-P4 | Reliability Patterns | Saga, retries, circuit breakers, outbox pattern |
| M2-P5 | Audit Log | Append-only, hash-chained, PII-redacted, exportable |
| M2-P6 | Langfuse Integration | Full tracing, cost tracking, reviewer feedback loop |
| M2-P7 | Eval Suite + Baselines | 30+ scenarios, naive baseline, ablation matrix |

### M2 Definition of Done
- [ ] Agent can ONLY reach backends through gateway (no bypass path exists)
- [ ] Provenance check blocks invented IDs
- [ ] Identity mismatch blocks wrong-requester action
- [ ] Approval hash mismatch blocks edited action
- [ ] Idempotency: zero duplicate side-effects across all 30 scenarios
- [ ] Timeout-after-commit → read-back → no duplicate refund
- [ ] Naive baseline fails adversarial scenarios that ResolveOps passes
- [ ] Full audit trail reconstructable from audit_log alone

---

## Milestone 3 — Frontend & Polish

**Goal:** Full enterprise frontend, final hardening, CI safety gates, complete documentation, demo-ready.

**Plan file:** `.planning/milestones/M3-frontend.md`

### Phases

| Phase | Name | Key Output |
|---|---|---|
| M3-P1 | Frontend Shell & Design System | Next.js App Router, Tailwind tokens, sidebar, dark theme |
| M3-P2 | Dashboard Page | KPIs, charts, system health, kill switch state |
| M3-P3 | Tickets & Ticket Detail | Primary product screen — 3-column layout |
| M3-P4 | Approval Queue | Filtered queue, inline approve/reject, expiration countdown |
| M3-P5 | Customers, KB, Audit Pages | Customer detail, policy viewer with conflicts, audit timeline |
| M3-P6 | Analytics, Traces, Settings | Metrics charts, visual workflow trace, AI/policy config |
| M3-P7 | Demo Mode | 6 one-click scenarios with visual feedback |
| M3-P8 | CI/CD + Documentation | Safety gates, all 7 docs, README with 19 sections |

### M3 Definition of Done
- [x] All 9 pages work (dashboard, tickets, approvals, customers, kb, audit, analytics, traces, settings)
- [x] Demo mode: all 6 scenarios work end-to-end
- [x] CI hard-fails if unsafe_action_rate > 0 or duplicate_side_effect_rate > 0
- [x] All 7 docs complete
- [x] README with all 19 sections
- [x] 5-minute demo works

---

## Milestone 4 — Full RAG Knowledge & Policy Engine

**Goal:** Production-grade Hybrid RAG pipeline with 18 versioned policy documents, section-aware chunking, FastEmbed bge-m3 dense retrieval, BM25 lexical retrieval, RRF fusion, FlashRank reranking, and contradictory policy conflict handling.

**Plan file:** `.planning/milestones/M4-CONTEXT.md`

### Phases

| Phase | Name | Key Output |
|---|---|---|
| M4-P1 | Policy Corpus Expansion | 18 markdown documents with YAML frontmatter in `rag/documents/` |
| M4-P2 | Section-Aware Chunker | Clean markdown parser preserving title, section, version, dates, status |
| M4-P3 | Local FastEmbed Embeddings | `BAAI/bge-m3` ONNX embedder with CPU support & zero-PyTorch footprint |
| M4-P4 | Dual-Mode Qdrant Vector Store | HTTP + embedded fallback (`:memory:`) collection management |
| M4-P5 | BM25 + RRF Hybrid Fusion | Lexical exact token match + Reciprocal Rank Fusion |
| M4-P6 | FlashRank Reranker & Graph Wiring | Neural reranking to top 3-5, policy conflict detector, LangGraph wiring |

---

## Milestone 5 — Complete 30+ Evaluation Suite & Baselines

**Goal:** 30+ evaluation scenarios across 5 categories, Naive Baseline agent, and ablation testing matrix.

**Plan file:** `.planning/milestones/M5-PLAN.md`

### Phases

| Phase | Name | Key Output |
|---|---|---|
| M5-P1 | Scenario Suite Expansion | 30 YAML scenarios (6 Auto, 8 Approval, 5 Forbidden, 7 Adversarial, 4 Reliability) |
| M5-P2 | Naive Baseline Agent | Prompt-only safety agent bypassing Gateway to prove necessity |
| M5-P3 | Ablation Runner | 4 ablations (no-provenance, no-identity, no-approval-hash, no-idempotency) |
| M5-P4 | Automated Reporting | Markdown report tables in `evals/reports/` with 5-run variance |

### M5 Definition of Done
- [x] All 30 YAML scenario files present in `evals/scenarios/` (EVAL-001 to EVAL-030)
- [x] 6 Auto, 8 Approval, 5 Forbidden, 7 Adversarial, 4 Reliability scenarios covered
- [x] `evals/baselines/naive_agent.py` implemented and benchmarked
- [x] `evals/ablations/runner.py` implemented with 4 ablation modes
- [x] Component -> Attack Protected matrix generated
- [x] `evals/runner.py` computes all 12 metrics across 5-run repeats (150 total runs)
- [x] Hard CI safety gate passes: `unsafe_action_rate == 0` (0/150 runs)
- [x] `evals/reports/evaluation_report.md` created with complete comparative tables

---

## Milestone 6 — MCP Servers & Advanced Reliability

**Goal:** Standardized FastMCP tool servers with annotations and production reliability patterns.

**Plan file:** `.planning/milestones/M6-PLAN.md`

### Phases

| Phase | Name | Key Output |
|---|---|---|
| M6-P1 | MCP Protocol Servers | 5 FastMCP servers in `services/mcp_*` with read/write hints |
| M6-P2 | Transactional Outbox | PostgreSQL outbox pattern for reliable side-effects |
| M6-P3 | Commit Timeout Read-Back | Automatic state reconciliation on unknown-outcome writes |
| M6-P4 | Circuit Breakers & Saga | Degraded mode failover and multi-step compensation |
| M6-P5 | Policy Gateway & Tests | Gateway MCP integration + complete reliability test suite |

### M6 Definition of Done
- [ ] All 5 MCP servers implemented in `services/mcp_*` (`ticketing`, `crm`, `billing`, `access`, `kb`)
- [ ] Every tool annotated with `readOnlyHint`, `destructiveHint`, `idempotentHint`
- [ ] Unified MCP Registry `services/mcp_registry.py` functional
- [ ] Transactional Outbox pattern implemented in `backend/app/reliability/outbox.py`
- [ ] Commit-Timeout Read-Back verification state machine implemented in `backend/app/reliability/readback.py`
- [ ] Sliding-window circuit breaker implemented in `backend/app/reliability/circuit_breaker.py`
- [ ] Multi-step saga coordinator implemented in `backend/app/reliability/saga.py`
- [ ] Gateway `step11_execute` wired to MCP registry and reliability guards
- [ ] Full reliability test suite in `tests/reliability/` passing with 100% success rate
- [ ] All 30 evaluation scenarios passing (`python evals/runner.py`) with 0 unsafe actions

---

## Global Definition of Done

See each milestone's DoD above. Project is complete only when all milestone DoDs are checked.

Key non-negotiables (must NOT be cut):
- Policy Gateway
- 30+ Scenario Suite
- Identity Verification
- Idempotency
- Read-Back Verification
- Red-Team Tests
- Audit Trail
- Failure Modes Documentation

