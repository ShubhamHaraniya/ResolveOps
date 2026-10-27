<div align="center">

# ⚡ ResolveOps

### Governed AI Support Operations Platform

*An LLM agent that reads tickets, plans actions, and enforces policy — deterministically.*

[![Python 3.12](https://img.shields.io/badge/Python-3.12-blue?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-Workflow-orange)](https://github.com/langchain-ai/langgraph)
[![Next.js](https://img.shields.io/badge/Next.js-16-black?logo=next.js&logoColor=white)](https://nextjs.org/)
[![Groq](https://img.shields.io/badge/LLM-Groq-F55036)](https://groq.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green)](LICENSE)

---

> ResolveOps is a **production-grade reference implementation** of a governed AI support-operations system. An LLM agent reads support tickets, proposes resolutions, and a **deterministic policy layer** — not the model — decides whether each action may execute automatically, requires a human approval, or is outright forbidden. Every tool call passes through a 12-step security gateway and is recorded in a cryptographic hash-chained audit log.

</div>

---

## Table of Contents

- [Key Features](#key-features)
- [System Architecture](#system-architecture)
- [AI and Agentic Stack](#ai-and-agentic-stack)
- [Policy and Governance Engine](#policy-and-governance-engine)
- [Frontend Pages](#frontend-pages)
- [Backend API Reference](#backend-api-reference)
- [Security Features](#security-features)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)
- [Configuration](#configuration)
- [Testing and Evaluation](#testing-and-evaluation)
- [Project Structure](#project-structure)
- [Known Limitations](#known-limitations)
- [Further Documentation](#further-documentation)

---

## Key Features

| Feature | Description |
|---|---|
| **LangGraph Agentic Workflow** | 11-node ticket processing pipeline with Langfuse tracing |
| **Deterministic Policy Engine** | YAML-driven rules enforced outside the LLM — model cannot override |
| **12-Step Policy Gateway** | JWT, schema validation, identity binding, budget limits, kill switch |
| **Human-in-the-Loop Approvals** | Approve, Reject, Edit, or Escalate proposed tool calls |
| **Prompt Injection Detection** | Regex-pattern scanner — deterministic, no LLM needed |
| **Hash-Chained Audit Log** | Tamper-evident, verifiable, per-ticket exportable |
| **Hybrid RAG Knowledge Base** | Dense + BM25 retrieval with FlashRank reranking over 18 policy docs |
| **AI Copilot** | RAG-powered operational assistant with live DB context |
| **Live Analytics Dashboard** | Automation rate, approval outcomes, category breakdowns, latency |
| **Inbound Webhooks** | Zendesk-style and Stripe-style event ingestion |
| **MCP Tool Servers** | Modular billing, CRM, access, ticketing, and knowledge base tools |
| **Offline Evaluation Suite** | 30 policy scenarios + LLM-judged RAG benchmark |

---

## System Architecture

```
+-------------------------------------------------------------+
|                    Next.js Frontend (port 3000)              |
|  Dashboard · Tickets · Approvals · Audit · Analytics ···    |
+------------------------+------------------------------------+
                         | /api proxy
                         v
+-------------------------------------------------------------+
|                 FastAPI Backend (port 8000)                   |
|                                                             |
|  +------------------------------------------------+         |
|  |         LangGraph Workflow (11 nodes)           |         |
|  |                                                 |         |
|  |  START → intake → classify → verify_identity    |         |
|  |       → gather_context → plan_action            |         |
|  |       → policy_check -+- auto -------> execute  |         |
|  |                       +- approval -> interrupt  |         |
|  |                       +- forbidden -> escalate  |         |
|  |       → verify_outcome → draft_reply → close    |         |
|  +------------------------------------------------+         |
|                                                             |
|  classify / plan_action / draft_reply  -------> Groq LLM   |
|  policy_check  --------------------------------> rules.yaml |
|  execute  -------------------------------------> Policy     |
|                                                  Gateway    |
|                                                  (12 steps) |
|                                                  |          |
|                                                  v          |
|                              MCP Tool Servers               |
|                   billing · crm · access · ticketing · kb   |
+-----------------------------------+--------------------------+
                                    |
                                    v
              +-------------------------------------+
              |   Hash-chained audit_log (SQLite /  |
              |           PostgreSQL)               |
              +-------------------------------------+
```

### Routing Logic After `policy_check`

```
policy_check result
       |
       +-- any "forbidden" decision --> escalate ticket, close run
       |
       +-- any "approval" decision --> approval_interrupt node
       |                               workflow PAUSES, writes to DB
       |                               human reviews on /approvals
       |                               human decides
       |                               resume --> execute --> close
       |
       +-- all "auto" decisions -----> execute --> verify_outcome --> close
```

---

## AI and Agentic Stack

### LangGraph Workflow — 11 Nodes

Each node is individually instrumented with timing and Langfuse spans:

| Node | Role | Uses LLM |
|---|---|---|
| `intake` | Parse raw ticket data, attach run metadata | No |
| `classify` | Categorize ticket type and urgency | Yes — Groq fast model |
| `verify_identity` | Check requester against authorized CRM contacts | No |
| `gather_context` | Fetch account, invoice, subscription data + RAG policy docs | No |
| `plan_action` | Generate structured resolution proposal with tool calls | Yes — Groq primary model |
| `policy_check` | Run every proposed tool call through `rules.yaml` | No |
| `approval_interrupt` | Persist pending approval to DB, pause workflow | No |
| `execute` | Dispatch approved tool calls through 12-step gateway | No |
| `verify_outcome` | Validate executed results match proposal | No |
| `draft_reply` | Write customer-facing reply using outcomes | Yes — Groq primary model |
| `close` | Finalize ticket status, update DB | No |

### Groq LLM Integration

- **Primary model** (`GROQ_MODEL_PRIMARY`): Used for `plan_action` and `draft_reply` — complex reasoning tasks
- **Fast model** (`GROQ_MODEL_FAST`): Used for `classify` — quick classification
- Per-run budgets enforced: `MAX_LLM_CALLS_PER_RUN`, `MAX_TOOL_CALLS_PER_RUN`, `MAX_REPLANS_PER_RUN`
- Exponential backoff with `tenacity` retries on API failures

### Hybrid RAG — Knowledge Base Retrieval

The `gather_context` node retrieves relevant policy documents before planning:

```
Query
  |
  +---> Dense embedding (BAAI/bge-small-en-v1.5 via fastembed)
  |       Qdrant vector search (or in-memory fallback)
  |
  +---> Lexical BM25 search (rank-bm25)
          |
          v
    Reciprocal Rank Fusion (RRF)
          |
          v
    FlashRank cross-encoder reranking (top-5 from top-20)
          |
          v
    RAG results injected into plan_action context
```

- 18 sample policy documents across billing, access, subscriptions, security
- Re-indexable via `POST /api/policies/reindex`
- Policy documents are **informational** — enforcement comes only from `rules.yaml`

### AI Copilot (`/api/copilot/chat`)

RAG-powered operational assistant that combines:
- Live database queries (tickets, accounts, invoices, approvals)
- Policy knowledge base retrieval
- Multi-turn conversation history
- Example queries: "Find tickets for jane@acme.com", "What is the refund limit?", "Show pending approvals"

---

## Policy and Governance Engine

### Policy Rules (`policy/rules.yaml` — v3)

The policy engine evaluates **every proposed tool call** against YAML rules before execution. The LLM cannot override these rules.

Three tiers, evaluated from most to least restrictive:

```
forbidden  >  approval  >  auto
```

**Complete rule table:**

| Rule ID | Tool | Condition | Tier | Escalates To |
|---|---|---|---|---|
| `TKT-001` | `ticketing.add_internal_note` | Always | auto | — |
| `TKT-002` | `ticketing.send_public_reply` | Always | approval — support_agent | — |
| `REF-001` | `billing.issue_refund` | amount <= $50, non-strategic, non-hold | approval — support_agent | — |
| `REF-002` | `billing.issue_refund` | amount $50–$500 | approval — support_lead | — |
| `REF-099` | `billing.issue_refund` | amount > $500 | **forbidden** | Finance |
| `CRD-001` | `billing.issue_credit` | amount < $100 | approval — support_agent | — |
| `CRD-002` | `billing.issue_credit` | amount $100–$1000 | approval — support_lead | — |
| `ACC-001` | `access.grant_access` | viewer/member role, <= 30 days | approval — security_reviewer | — |
| `ACC-002` | `access.reset_mfa` | authorized contact | approval — security_reviewer | — |
| `ACC-099` | `access.grant_access` | admin/root/superuser/owner role | **forbidden** | Security |
| `SEC-001` | `*` all tools | injection.suspected = true | **forbidden** | Security |
| `GEN-001` | `*` all tools | account.legal_hold = true | **forbidden** | Legal |
| `GEN-002` | `billing.*` | account.strategic = true | approval — support_lead | — |

**Defaults:** Unknown tool → forbidden. Unverified requester → forbidden.

### 12-Step Policy Gateway

Every tool execution passes through all 12 steps in sequence:

```
Step  1:  Kill switch check (emergency halt)
Step  2:  Scoped HMAC JWT token validation
Step  3:  Schema validation against MCP tool registry
Step  4:  Argument provenance check (args match approved proposal)
Step  5:  Identity binding (caller is the ticket's run)
Step  6:  Policy re-evaluation (deterministic rules, not LLM)
Step  7:  Approval validation (hash-bound to run + tool + args; 24h expiry)
Step  8:  Idempotency check (prevent duplicate tool calls)
Step  9:  Per-run tool-call budget enforcement
Step 10:  Pre-execution audit log entry
Step 11:  Circuit-breaker dispatch with timeout read-back
Step 12:  Result audit log entry
```

---

## Frontend Pages

All pages are built with Next.js 16, React 19, Recharts, and Tailwind CSS 4.

### Dashboard (`/`)

The operations command center:

- **5 KPI metric cards**: Total tickets, Resolution rate, Approval acceptance rate, Median planning latency, Blocked/flagged actions
- **Approval Outcomes chart**: Bar chart of Approved / Rejected / Escalated / Expired approvals
- **Resolution Rate by Category chart**: Resolved percentage per ticket category group
- **Dependency health panel**: Real-time status of PostgreSQL, Redis, Qdrant with latency in ms
- **Live audit feed**: Last 6 hash-chained audit events with clickable ticket links
- **Pending approvals counter** with direct link to approval queue
- Auto-refreshes every 10 seconds

### Tickets (`/tickets`)

Full ticket management with live demo scenarios:

**8 Pre-built Test Scenarios:**

| Scenario | Badge | What It Demonstrates |
|---|---|---|
| Custom / Blank | CUSTOM TEST | Free-form testing with any inputs |
| Amount Mismatch | DISCREPANCY ($90 vs $30) | Flags discrepancy, halts unauthorized refund |
| Normal Refund | HAPPY PATH | REF-001 approval triggered (amount <= $50) |
| Prompt Injection | SECURITY ADVERSARY | Detected by SEC-001, escalated to Security |
| Wrong Requester | IDENTITY MISMATCH | Unauthorized contact blocked from mutations |
| Admin Access | FORBIDDEN PRIVILEGE | ACC-099 forbidden — admin role denied |
| Large Refund | VP APPROVAL | REF-099 forbidden — exceeds $500 threshold |
| Duplicate Refund | IDEMPOTENCY | Idempotency layer blocks duplicate payout |

**Ticket List Features:**
- Search by subject, requester email, or ticket ID
- Filter by status: open, awaiting approval, resolved, escalated
- Filter by category and urgency
- Real-time `awaiting_approval` run status badge
- Create custom tickets via modal form with account selector

**Ticket Detail (`/tickets/[id]`):**
- Full ticket body with requester info and account flags
- Live workflow run node timeline with per-node duration in ms
- Policy decisions display with tier (auto/approval/forbidden) and rule IDs
- Audit trail tab (all events for this ticket)
- Multi-turn reply interface: customer follow-up re-activates the LangGraph agent
- Toggle between Internal Note and Public Reply

### Approval Queue (`/approvals`)

Human-in-the-loop review interface:

- All pending approvals with tool name, proposed arguments, policy rule, and expiry time
- Filter tabs: All / Billing / Access
- Per-approval actions:
  - **Approve** — Gateway authorizes and resumes LangGraph workflow
  - **Reject** — Workflow closes, ticket is escalated
  - **Edit** — Modify arguments; new hash is bound to the edited args
  - **Escalate** — Bumps to higher authority (vp_support)
- Detail modal with full arguments JSON and policy context
- "All caught up" empty state when queue is clear

### Customers (`/customers`)

Enterprise account directory:

- 50 seeded accounts with ARR, plan tier, and CSM owner
- Filter by plan: Starter / Pro / Enterprise / Enterprise+
- Legal hold indicator — all actions are forbidden for these accounts
- Strategic account indicator — all billing requires support_lead approval
- Contact count and ticket count per account

### Knowledge Base (`/knowledge-base`)

Policy document management with inline editor:

- Browse 18 policy documents with version and status
- Full-text search across policy content
- Inline markdown editor — edit or create new documents directly in the browser
- Re-index button — triggers Qdrant/BM25 re-ingestion of all documents
- Status tracking: `active` or `deprecated`
- Split-pane content preview

### Audit Log (`/audit`)

Hash-chained, tamper-evident audit trail:

- All tool calls, policy decisions, approvals, and security events
- Filter by event type and actor type (agent / gateway / human)
- Full-text search by ticket ID or tool name
- Chain Verification button — validates SHA-256 hash chain integrity across all events
- Color-coded result badges: SUCCESS (green) / BLOCKED or FAILED (red)
- Per-ticket export as JSON download
- Columns: timestamp, event type, actor, tool, policy rule, result status

Audit event types: `received` · `proposed` · `policy_decision` · `approval_requested` · `approved` · `edited` · `rejected` · `executed` · `verified` · `failed` · `escalated` · `tool_call_start` · `tool_call_result` · `tool_call_denied`

### Analytics (`/analytics`)

Deep operational metrics dashboard:

- **Top KPIs**: Automation rate, Approval acceptance rate, Escalation rate, Median latency (p50/p95), Cost per ticket (USD)
- **Category Automation bar chart**: Resolution percentage by ticket category
- **Approval Outcomes pie chart**: Distribution of approval decisions
- **Security counters**: Injection attempts, blocked actions, gateway denials
- **RAG Benchmark panel**: Run and view RAGAS evaluation results (faithfulness, answer relevance, context precision, context recall)
- One-click benchmark trigger with live progress indicator

### Traces (`/traces`)

Workflow execution inspector:

- List of all workflow runs with status and total duration
- Node timeline: expand each run to see per-node timing and status
- State inspection: classification output, identity result, context fetched, policy decisions made
- LangGraph run status: running / awaiting_approval / done / failed
- Langfuse trace ID linking when Langfuse is configured

### Settings (`/settings`)

Governance controls:

- **Global Kill Switch** — toggles gateway to reject ALL tool executions immediately (emergency stop)
- **Dependency health panel** — PostgreSQL, Redis, Qdrant reachability with latency
- LLM model configuration display
- Backend connectivity indicator

---

## Backend API Reference

All endpoints are under `/api`. Interactive docs at `http://localhost:8000/docs`.

### Tickets

| Method | Path | Description |
|---|---|---|
| GET | `/api/tickets` | List tickets with pagination, filter by status/category |
| GET | `/api/tickets/{id}` | Ticket detail with messages, runs, approvals |
| POST | `/api/tickets` | Create a new ticket |
| POST | `/api/tickets/{id}/run` | Trigger LangGraph workflow for a ticket |
| POST | `/api/tickets/{id}/reply` | Send customer reply (re-activates agent) |

### Runs and Traces

| Method | Path | Description |
|---|---|---|
| GET | `/api/runs` | List active workflow runs with node timelines |
| GET | `/api/runs/{run_id}` | Detailed run state and node timeline |
| GET | `/api/traces/{run_id}` | Full trace with Langfuse span data |

### Approvals

| Method | Path | Description |
|---|---|---|
| GET | `/api/approvals` | List approvals (filterable by status) |
| POST | `/api/approvals/{id}/approve` | Approve: authorize in gateway, resume workflow |
| POST | `/api/approvals/{id}/reject` | Reject: close workflow |
| POST | `/api/approvals/{id}/edit` | Edit args: re-bind hash, approve, resume |
| POST | `/api/approvals/{id}/escalate` | Escalate to higher authority |

### Analytics

| Method | Path | Description |
|---|---|---|
| GET | `/api/analytics/overview` | Automation rate, approvals, latency, cost, categories |
| GET | `/api/analytics/security` | Injection counts, gateway denials, blocked actions |
| GET | `/api/analytics/ragas` | Latest RAG benchmark report |
| POST | `/api/analytics/ragas/run` | Trigger RAG benchmark evaluation |

### Audit

| Method | Path | Description |
|---|---|---|
| GET | `/api/audit` | Paginated audit events (filterable by event type, actor) |
| GET | `/api/audit/verify` | Verify SHA-256 hash chain integrity |
| GET | `/api/audit/tickets/{id}` | All events for a specific ticket |
| GET | `/api/audit/export/{id}` | Export ticket audit trail as JSON |

### Policies and Knowledge Base

| Method | Path | Description |
|---|---|---|
| GET | `/api/policies` | List policy documents |
| POST | `/api/policies` | Create new policy document |
| GET | `/api/policies/{id}` | Get policy document with full content |
| PUT | `/api/policies/{id}` | Update policy document content |
| POST | `/api/policies/reindex` | Re-ingest all documents into Qdrant/BM25 |

### Other

| Method | Path | Description |
|---|---|---|
| GET | `/api/customers` | List customer accounts with ARR, plan, contacts |
| GET | `/api/customers/{id}` | Customer detail with invoices, contacts |
| POST | `/api/copilot/chat` | RAG-powered AI assistant (multi-turn) |
| POST | `/api/webhooks/zendesk` | Ingest Zendesk-style webhook events |
| POST | `/api/webhooks/stripe` | Ingest Stripe-style webhook events |
| GET | `/api/admin/kill-switch` | Get kill switch status |
| POST | `/api/admin/kill-switch` | Toggle kill switch on/off |
| GET | `/health` | Liveness check |
| GET | `/ready` | Readiness check (DB, Redis, Qdrant) |

---

## Security Features

### Prompt Injection Detection

Deterministic regex-pattern scanner with no LLM involvement (making it immune to adversarial prompting):

- 30+ patterns covering: system overrides, false authority claims, bypass requests, privilege escalation, SQL/shell injection payloads, persona override attacks, fake approval claims, memory wipe attempts
- Risk scoring from 0.0 to 1.0 confidence per pattern
- A positive detection triggers `SEC-001` rule → forbidden tier → all tool calls blocked
- Scanned fields: ticket subject, ticket body, CRM notes

### Identity Verification

- Requester email must be an authorized contact in the CRM for the target account
- Account ownership verified before any mutation
- Cross-account action attempts are flagged and blocked
- Unverified requesters: all write operations are forbidden by default

### Audit Chain Integrity

```
row_hash = SHA256(prev_hash + timestamp + event + tool + args + result)
```

- Genesis block anchored with a known HMAC seed
- Every event chains from the previous event's hash
- Verification endpoint validates the entire chain in one request
- Emails and phone numbers are redacted before storage
- Tamper-evident within one database instance

### Approval Binding

Approvals are cryptographically bound to prevent substitution attacks:

```
approval.args_hash = SHA256(tool + ":" + sorted_json(args))
```

- At execution time the gateway recomputes the hash and rejects mismatches
- 24-hour expiry on all pending approvals
- Editing arguments invalidates the prior approval hash and creates a new one
- Each approval is bound to a specific run_id, ticket_id, tool, and argument set

---

## Tech Stack

| Layer | Technologies |
|---|---|
| **Backend** | Python 3.12, FastAPI, Uvicorn, async SQLAlchemy, Pydantic v2, httpx, tenacity, structlog |
| **Agentic Workflow** | LangGraph with MemorySaver checkpointer, conditional routing, 11 instrumented nodes |
| **LLM** | Groq API via httpx; openai/gpt-oss-120b for planning/replies, openai/gpt-oss-20b for classification |
| **RAG** | fastembed (BAAI/bge-small-en-v1.5), rank-bm25, FlashRank cross-encoder, qdrant-client |
| **Database** | PostgreSQL with asyncpg as primary; SQLite with aiosqlite as auto-detected fallback |
| **Caching** | Redis (readiness probe only in current version) |
| **Vector DB** | Qdrant (persistent); in-memory fallback when unavailable |
| **Observability** | structlog for structured JSON logs; Langfuse for optional trace spans |
| **Frontend** | Next.js 16, React 19, TypeScript, Tailwind CSS 4, Recharts, lucide-react |
| **Tooling** | pytest + pytest-asyncio, ruff for linting/formatting, ESLint, GitHub Actions CI |
| **Containerization** | Dockerfile for backend and frontend; docker-compose.yml with Postgres, Redis, Qdrant |

---

## Getting Started

### Prerequisites

- Python 3.12 or newer
- Node.js 20 or newer
- A Groq API key — required for agent ticket runs. Get one at [console.groq.com](https://console.groq.com)
- PostgreSQL, Qdrant, and Redis are optional — the backend auto-falls back to SQLite and in-memory equivalents

### 1. Clone and Set Up Backend

```bash
git clone https://github.com/your-username/ResolveOps.git
cd ResolveOps

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
# For development (tests + linting):
pip install -r requirements-dev.txt

# Configure environment
cp .env.example .env
# Edit .env and set GROQ_API_KEY=<your-key>

# Start backend (from repo root)
uvicorn app.main:app --app-dir backend --reload --port 8000
```

Backend starts at `http://localhost:8000`

- Health check: `http://localhost:8000/health`
- Interactive API docs: `http://localhost:8000/docs`
- On first start: SQLite database created at `backend/resolveops.db`, demo data seeded automatically (33 tickets, 20 audit events, 17 approvals, 19 workflow runs)

### 2. Start Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend starts at `http://localhost:3000`. All `/api` requests are proxied to the backend automatically.

### 3. Optional: Run Mock Services

The workflow calls these mock HTTP services and falls back to in-process stubs if they are unavailable:

```bash
# In separate terminals (from repo root):
python -m services.mocks.ticketing   # Ticketing mock  port 8001
python -m services.mocks.crm         # CRM mock        port 8002
python -m services.mocks.billing     # Billing mock    port 8003
```

### 4. Optional: Docker Compose

```bash
# Starts Postgres, Redis, Qdrant, backend, and frontend:
docker-compose up --build
```

Docker files are included as starting points but not verified in the latest environment.

### Quick Demo Walkthrough

1. Open `http://localhost:3000` — Dashboard shows live metrics
2. Go to **Tickets** — click a demo scenario (e.g., "Normal Refund") — click **Run Workflow**
3. Watch the node timeline execute in real time on the ticket detail page
4. If an approval is triggered — go to **Approvals** — Approve, Reject, or Edit
5. Check **Audit Log** to see the cryptographically-chained trace
6. Open **Analytics** to see updated automation rate and category breakdowns

---

## Configuration

All settings come from environment variables and the root `.env` file. Real environment variables always win over `.env`.

### Core Settings

| Variable | Default | Description |
|---|---|---|
| `GROQ_API_KEY` | empty | **Required** for ticket runs, copilot, and RAG benchmark |
| `GROQ_MODEL_PRIMARY` | `openai/gpt-oss-120b` | Model for plan_action and draft_reply |
| `GROQ_MODEL_FAST` | `openai/gpt-oss-20b` | Model for classify |
| `GROQ_MAX_TOKENS` | `4096` | Max tokens per LLM call |
| `GROQ_TIMEOUT_SECONDS` | `30` | LLM call timeout |
| `GROQ_MAX_RETRIES` | `3` | Retry count with exponential backoff |

### Database

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql://resolveops:resolveops@localhost:5432/resolveops` | Postgres URL; auto-falls back to SQLite |
| `DATABASE_POOL_SIZE` | `10` | Connection pool size |
| `SEED_DEMO_DATA` | `true` | Seed sample tickets, audit events, approvals, and workflow runs on startup |

### Infrastructure

| Variable | Default | Description |
|---|---|---|
| `QDRANT_URL` | `http://localhost:6333` | Vector DB URL; falls back to in-memory |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis URL; used by `/ready` check only |

### Observability

| Variable | Default | Description |
|---|---|---|
| `LANGFUSE_HOST` | `http://localhost:3000` | Langfuse tracing host |
| `LANGFUSE_PUBLIC_KEY` | empty | Langfuse public key |
| `LANGFUSE_SECRET_KEY` | empty | Langfuse secret key |

### Security and Limits

| Variable | Default | Description |
|---|---|---|
| `ENVIRONMENT` | `development` | Set to `production` to disable dev shortcuts and enforce secure secrets |
| `CORS_ORIGINS` | `http://localhost:3000,http://localhost:3001` | Allowed browser origins |
| `MAX_TOOL_CALLS_PER_RUN` | `20` | Per-run gateway budget |
| `MAX_LLM_CALLS_PER_RUN` | `10` | Per-run LLM call budget |
| `MAX_REPLANS_PER_RUN` | `2` | Max replanning iterations |
| `ZENDESK_WEBHOOK_SECRET` | empty | Webhook HMAC secret; unsigned webhooks accepted in dev when empty |
| `STRIPE_WEBHOOK_SECRET` | empty | Webhook HMAC secret; unsigned webhooks accepted in dev when empty |

### RAG

| Variable | Default | Description |
|---|---|---|
| `EMBEDDING_MODEL` | `BAAI/bge-small-en-v1.5` | Primary fastembed model |
| `EMBEDDING_FALLBACK_MODEL` | `all-MiniLM-L6-v2` | Fallback if primary unavailable |
| `RAG_TOP_K` | `20` | Candidates retrieved before reranking |
| `RAG_RERANK_TOP_N` | `5` | Final documents after reranking |

---

## Testing and Evaluation

```bash
# Lint
ruff check .

# Full test suite (102 tests, no network or Groq key needed)
python -m pytest -q

# Offline policy scenario evaluation (30 scenarios)
python -m evals.runner --no-write

# RAG benchmark (2 metrics are LLM-judged, needs GROQ_API_KEY)
python -m evals.rag_benchmark

# Frontend checks
cd frontend
npm run lint
npm run build

# Smoke test against running backend (port 8000)
python scripts/smoke_scenarios.py

# Run single ticket end-to-end (needs GROQ_API_KEY)
python scripts/run_single_ticket.py
```

### Policy Evaluation Suite (`evals/scenarios/` — 30 files)

Each scenario provides:
- Input: ticket text, requester identity, account flags, injection scan result
- Expected: policy tier (auto / approval / forbidden) and reason code
- The runner feeds scenarios through the **real policy engine** (not the LLM)
- Last run result: **28/30 scenarios resolved to expected tier**; 2 marked not-evaluable offline

### RAG Benchmark

Evaluates retrieval and generation quality across 18 policy documents:
- Retrieval metrics: hit rate, precision, recall
- LLM-judged metrics: faithfulness, answer relevance
- Reports written to `evals/reports/` (git-ignored)

### CI Pipeline (`.github/workflows/ci.yml`)

Runs on every push and pull request:
1. `ruff check .` — linting
2. `python -m pytest -q` — 102 unit and integration tests
3. `python -m evals.runner --no-write` — policy scenario validation
4. `npm run lint && npm run build` — frontend lint and build

---

## Project Structure

```
ResolveOps/
|
+-- backend/
|   +-- app/
|       +-- api/              FastAPI routers (tickets, runs, approvals, audit, analytics, ...)
|       +-- audit/            Hash-chain store, gateway sink, chain verification
|       +-- db/               SQLAlchemy models, session, seed data
|       +-- graph/            LangGraph workflow, 11 nodes, runner, TicketState
|       +-- llm/              Groq client with retry logic and cost tracking
|       +-- observability/    Langfuse client and telemetry helpers
|       +-- policy/           PolicyEngine that reads rules.yaml
|       +-- reliability/      Circuit breaker and timeout patterns
|       +-- config.py         Pydantic Settings loaded from env
|       +-- main.py           FastAPI app and lifespan startup
|
+-- services/
|   +-- gateway/              12-step policy gateway, HMAC JWT tokens, injection scanner
|   +-- mcp_billing/          Billing MCP tool server (refunds, credits, invoices)
|   +-- mcp_crm/              CRM MCP tool server (accounts, contacts)
|   +-- mcp_access/           Access MCP tool server (roles, MFA reset)
|   +-- mcp_ticketing/        Ticketing MCP tool server (notes, replies, tags)
|   +-- mcp_kb/               Knowledge base MCP tool server (policy search)
|   +-- mcp_registry.py       Tool capability metadata registry
|   +-- mocks/                Mock HTTP services (ticketing :8001, crm :8002, billing :8003)
|
+-- rag/
|   +-- documents/            18 sample policy Markdown documents
|   +-- embeddings/           fastembed model wrapper
|   +-- ingestion/            Document loading and chunking pipeline
|   +-- retrieval/            Dense + BM25 retrieval with RRF fusion
|   +-- reranking/            FlashRank cross-encoder reranking
|   +-- service.py            Public search_policies() interface
|
+-- policy/
|   +-- rules.yaml            Northwind Cloud AI Agent Policy Rules v3 (20 rules)
|
+-- frontend/
|   +-- app/
|   |   +-- dashboard/        Operations overview with charts and KPIs
|   |   +-- tickets/          Ticket list, detail, demo scenarios, reply UI
|   |   +-- approvals/        Human-in-the-loop approval queue
|   |   +-- customers/        Enterprise account directory
|   |   +-- knowledge-base/   Policy document browser and inline editor
|   |   +-- audit/            Hash-chained audit log with chain verification
|   |   +-- analytics/        Metrics charts and RAG benchmark runner
|   |   +-- traces/           Workflow run inspector with node timelines
|   |   +-- settings/         Kill switch and dependency status
|   +-- components/           Shared UI components (Badges, States, Sidebar, Copilot)
|   +-- lib/                  API client, TypeScript types, Zustand store, utils
|
+-- evals/
|   +-- scenarios/            30 policy evaluation scenario files (YAML)
|   +-- runner.py             Offline policy scenario runner
|   +-- rag_benchmark.py      RAG RAGAS benchmark runner
|
+-- tests/                    pytest suites (policy, gateway, audit, RAG, reliability, e2e)
+-- scripts/                  Manual helpers: run_single_ticket.py, smoke_scenarios.py
+-- docs/                     Architecture, permission model, failure modes, runbook, threat model
+-- policy/rules.yaml         Policy rules — single source of truth
+-- docker-compose.yml        Full stack Docker Compose
+-- .github/workflows/ci.yml  CI pipeline
```

---

## Known Limitations

| Limitation | Detail |
|---|---|
| **No API authentication** | `reviewer_id` is client-supplied; roles are recorded but not enforced server-side. Do not expose to untrusted networks. |
| **In-process gateway state** | Approval registry, idempotency store, budgets, and kill switch live in process memory and are lost on restart. |
| **Single-process only** | No horizontal scaling support in the current version. |
| **One approval action per run** | Saga compensation exists but is best-effort; failed executions are not fully rolled back. |
| **Audit chain is tamper-evident, not tamper-proof** | Chain verified within one database; not externally anchored (no blockchain or HSM). |
| **Pattern-based injection detection** | Can miss novel phrasings not covered by the 30+ regex patterns. |
| **Mock services only** | Billing, CRM, access, and ticketing are mock implementations — not connected to real external systems. |
| **Docker builds not verified** | Docker files are included as starting points but not validated in the latest environment. |

---

## Further Documentation

| Document | Description |
|---|---|
| [docs/architecture.md](docs/architecture.md) | Detailed system architecture and data flow diagrams |
| [docs/permission-model.md](docs/permission-model.md) | Permission tiers, reviewer roles, and escalation paths |
| [docs/failure-modes.md](docs/failure-modes.md) | Failure modes and fallback behaviors |
| [docs/runbook.md](docs/runbook.md) | Operational runbook for common tasks |
| [docs/threat-model.md](docs/threat-model.md) | Threat model and security design decisions |
| [docs/demo-script.md](docs/demo-script.md) | Step-by-step demo walkthrough |
| [frontend/README.md](frontend/README.md) | Frontend-specific notes |

---

<div align="center">

**ResolveOps** — A reference implementation for governed AI support operations.

*Northwind Cloud is a fictional company. All customer data, invoices, and policies are synthetic.*

</div>
