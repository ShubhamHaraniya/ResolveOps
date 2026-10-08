# ResolveOps — Project Roadmap

> Version: 1.1 | Status: ACTIVE | Last Updated: 2026-10-08
> Structure: Milestone-driven. Each milestone is a GSD planning unit.

---

## Milestone Overview

| ID | Milestone | Timeline | Status | Phases |
|---|---|---|---|---|
| [M1](#milestone-1--foundation--skeleton) | Foundation & Skeleton | Week 1 | PENDING | 8 phases |
| [M2](#milestone-2--governance--reliability) | Governance & Reliability | Week 2 | PENDING | 7 phases |
| [M3](#milestone-3--frontend--polish) | Frontend & Polish | Week 3 | PENDING | 8 phases |

**Plan each milestone:** `/gsd-plan-phase M1`, `/gsd-plan-phase M2`, `/gsd-plan-phase M3`

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
- [ ] All 9 pages work (dashboard, tickets, approvals, customers, kb, audit, analytics, traces, settings)
- [ ] Demo mode: all 6 scenarios work end-to-end
- [ ] CI hard-fails if unsafe_action_rate > 0 or duplicate_side_effect_rate > 0
- [ ] All 7 docs complete
- [ ] README with all 19 sections
- [ ] 5-minute demo works

---

## Global Definition of Done

See each milestone's DoD above. Project is complete only when all three milestone DoDs are checked.

Key non-negotiables (must NOT be cut):
- Policy Gateway
- 30+ Scenario Suite
- Identity Verification
- Idempotency
- Read-Back Verification
- Red-Team Tests
- Audit Trail
- Failure Modes Documentation
