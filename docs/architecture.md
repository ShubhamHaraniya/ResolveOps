# Architecture

This document describes how ResolveOps is built, based on the code in this repository.
For the safety guarantees and their limits see [permission-model.md](permission-model.md) and
[threat-model.md](threat-model.md).

## Overview

ResolveOps processes support tickets with a LangGraph workflow. An LLM (Groq) classifies the ticket and
proposes actions; everything that decides whether an action may run is deterministic code.

```
Ticket (REST / webhook)
        │
        ▼
 LangGraph workflow (backend/app/graph)
   intake → classify → verify_identity → gather_context → plan_action → policy_check
                                              │                              │
                                  not verified│        auto ─────────────────┤
                                              ▼        approval → approval_interrupt → (pause)
                                            close      forbidden ─────────────────────► close
                                                       auto ► execute → verify_outcome → draft_reply → close
        │
        ▼
 Policy gateway (services/gateway, in-process)  ──►  MCP-style tool servers (services/mcp_*)
        │                                                   │
        ▼                                                   ▼
 Hash-chained audit log (DB)                   mock ticketing / CRM / billing data
```

## Components

| Area | Location | What it does |
|---|---|---|
| API | `backend/app/api/` | FastAPI routers mounted under `/api` (tickets, runs, approvals, customers, audit, analytics, policies, webhooks, copilot, admin) plus `/health` and `/ready`. |
| Workflow | `backend/app/graph/` | 11-node LangGraph state machine, node implementations in `nodes/`, run orchestration in `runner.py`. |
| LLM client | `backend/app/llm/` | Groq chat-completions client over `httpx` (`complete_structured` for schema-validated JSON, `complete_text`), prompts and Pydantic schemas. Raises when `GROQ_API_KEY` is not set. |
| Policy engine | `backend/app/policy/engine.py` + `policy/rules.yaml` | Deterministic rule evaluation, default-deny. |
| Gateway | `services/gateway/` | 12-step enforcement pipeline, scoped JWTs, injection scanner. |
| Tool servers | `services/mcp_ticketing`, `mcp_crm`, `mcp_billing`, `mcp_access`, `mcp_kb`, registry in `services/mcp_registry.py` | In-process MCP-style tool servers with JSON schemas and read-only/destructive annotations. |
| Mock services | `services/mocks/` | Optional FastAPI apps (ticketing :8001, CRM :8002, billing :8003). Workflow nodes try them first and fall back to the in-process tool servers. They are run separately (`python -m services.mocks.ticketing`, etc.). |
| Audit | `backend/app/audit/` | Append-only, hash-chained `audit_log` table and chain verification. |
| Reliability | `backend/app/reliability/` | Per-service circuit breaker and timeout read-back verifier. |
| RAG | `rag/` | Hybrid retrieval over 18 sample policy documents (see below). |
| Database | `backend/app/db/` | Async SQLAlchemy models; PostgreSQL via `DATABASE_URL`, SQLite fallback file when it is unreachable. Tables are created at startup (`create_all`); there are no migrations. |
| Frontend | `frontend/` | Next.js app that talks to the backend through a rewrite of `/api` and `/ready` to `BACKEND_URL`. |
| Evals | `evals/` | Offline policy-layer scenario suite and an LLM-judged RAG benchmark. |

## Workflow nodes

| Node | Uses LLM | Purpose |
|---|---|---|
| `intake` | no | Load the ticket, initialise run state. |
| `classify` | yes (fast model) | Category / urgency / sentiment. The deterministic injection scan runs here and sets a flag. |
| `verify_identity` | no | Check the requester email against the account's authorized contacts from the CRM. If the requester is not verified the run goes straight to `close` with an escalation. |
| `gather_context` | no | Fetch account, invoices, subscription and account notes in parallel, plus RAG retrieval. |
| `plan_action` | yes (primary model) | Propose typed actions, citations and a draft reply. It does not call backends and does not decide authorization. |
| `policy_check` | no | Evaluate every proposed action with the policy engine; the most restrictive tier wins. |
| `approval_interrupt` | no | Create an approval record and pause the run. |
| `execute` | no | Send each action through the gateway; stops at the first failure and marks the run failed (nothing is rolled back). |
| `verify_outcome` | no | If an action timed out with an unknown outcome, query the backend by idempotency key (read-back). |
| `draft_reply` | yes | Draft the customer reply from what was actually executed. |
| `close` | no | Finalize status (resolved, escalated, rejected, failed). |

Routing after `policy_check`: any `forbidden` → `close` (escalation); else any `approval` → `approval_interrupt`;
else all `auto` → `execute`. When a reviewer approves, the run is re-invoked from `START` with
`resume_approval` set and jumps to `execute`; reject/escalate jump to `close`.
Only one approval-tier action per run is supported.

Run state is stored in `workflow_runs.state_json`; an in-memory cache (`_ACTIVE_RUNS`) holds active runs and the
LangGraph checkpointer is `MemorySaver` — there is no persistent checkpointer.

## Policy gateway

`services/gateway/gateway.py` runs 12 steps in order; any failure raises and nothing executes:

1. Validate the scoped HMAC-SHA256 JWT (bound to run, ticket, tool and argument hash).
2. Validate arguments against the tool schema from the MCP registry (the registry is the allowlist).
3. Provenance: every `*_id` / `email` argument must appear in the trusted context gathered from real tool results.
4. Identity binding: the requester must be in the account's authorized contacts (fails closed for writes).
5. Policy engine evaluation.
6. For approval-tier actions: the approval must exist, belong to this run/ticket/tool, be `approved`, be younger than 24 h, and its stored hash must match the arguments.
7. Idempotency: an identical earlier call returns the cached result.
8. Per-run tool-call budget (`MAX_TOOL_CALLS_PER_RUN`).
9. Audit event written before execution.
10. Kill-switch check.
11. Dispatch through the MCP registry, behind a per-service circuit breaker; a timeout triggers a read-back reconciliation.
12. Audit result.

Gateway state (approval registry, idempotency store, budgets, kill switch) lives in process memory.
The approvals API re-registers approval records from the database after a restart.

## Policy engine

`policy/rules.yaml` (version 3, fictional "Northwind Cloud" rules) defines rules per tool with optional `when`
conditions, a `tier` (`auto`, `approval`, `forbidden`), an `approver_role` or `escalate_to`, and a `priority` for the
cross-cutting rules. Unknown tools and unverified requesters default to `forbidden`. Precedence is
forbidden over approval over auto. Cross-cutting rules: SEC-001 (suspected injection), GEN-001 (legal hold),
GEN-002 (strategic accounts, financial tools need a support lead).

## Audit log

Each `audit_log` row stores `prev_hash` and `row_hash = SHA256(prev_hash + ":" + canonical_json(fields))`.
`GET /api/audit/verify` recomputes the chain. Emails and phone-like numbers are masked before storage
(`redact_pii`). The chain is tamper-evident for a single database; it is not an external or signed ledger.

## RAG

`rag/` ingests the 18 Markdown policy documents in `rag/documents/`, chunks them, embeds them with `fastembed`
(BAAI bge-small; a hash-based fallback is used if the model is unavailable), and indexes them in Qdrant
(`QDRANT_URL`; falls back to an in-memory index). Retrieval combines dense search and BM25 with reciprocal rank fusion
and an optional FlashRank rerank. The documents are informational context for the model and the knowledge-base page —
they never grant or deny actions; enforcement comes only from `policy/rules.yaml`.

## Frontend

Next.js (App Router), React, Tailwind CSS, Recharts. Pages: Dashboard, Tickets (list and detail), Approvals,
Customers, Knowledge Base, Audit Log, Analytics, Traces (list and per-run), Settings. All data is fetched from the
backend; there is no bundled sample data.
