# ResolveOps — Governed AI Support Operations Platform

> **Governed AI Agent for Support Operations**

---

## Project Overview

**ResolveOps** is a production-style enterprise application demonstrating how an AI agent can safely operate across support, CRM, billing, access management, and internal policy systems while remaining governed by deterministic controls.

**Fictional Customer:** Northwind Cloud — a 400-person B2B SaaS company handling ~1,800 support tickets/month.

**Core Architectural Principle:**
> Groq provides intelligence. LangGraph controls workflow. RAG provides policy knowledge. MCP provides standardized integrations. The policy gateway determines authorization. Humans approve risky actions. Backend systems execute. Verification and audit prove what happened.

**Do not use prompts as the primary security mechanism.**

---

## Customer Problem

Northwind Cloud support agents currently move between ticketing, CRM, billing, access/IAM, and knowledge base/policy documents for routine requests such as:

- Refunds & credits
- Invoice questions
- Plan/seat changes
- Access requests & MFA resets
- Billing contact changes

**Objective:** Reduce handling time for routine support work without increasing financial, security, or customer-impact risk.

---

## Stakeholders

| Stakeholder | Needs | Vetoes |
|---|---|---|
| Support Lead | Faster handling, fewer copy-paste errors, agent control | Automatic outbound customer messages without review |
| Finance Controller | Refund limits, duplicate prevention, reconciliation | Uncontrolled financial writes |
| Security / IT | Least privilege, identity verification, auditability | Admin access, credentials inside prompts |
| Customer Success | Accurate communication, strategic-account protection | Automatic actions on strategic accounts |

---

## Success Criteria (Measurable)

| Metric | Target |
|---|---|
| Unsafe action rate | = 0 |
| Duplicate side-effect rate | = 0 |
| Median proposal latency | < 20 sec |
| Automation rate | >= 25-30% |
| Approval acceptance | > 85% |
| Every action | Reconstructable from audit |

> Do not invent results. Show N/A if not measured.

---

## Non-Goals (Hard Limits)

The agent must NOT automatically perform:
- Chargebacks
- Account deletion
- Data erasure
- Admin access
- Production access
- Large refunds (> $500 without Finance escalation)
- Bulk financial operations
- Actions on strategic accounts
- Actions on legal-hold accounts
- Unreviewed outbound customer communication

---

## Tech Stack

### Frontend
- Next.js (App Router), TypeScript, Tailwind CSS, shadcn/ui
- Lucide Icons, TanStack Query, React Hook Form, Zod, Recharts
- Desktop-first enterprise UI (1440x900)

### Backend
- Python 3.11, FastAPI, Pydantic v2, SQLAlchemy, Alembic
- PostgreSQL, Redis, Tenacity

### LLM (Groq API)
- Primary reasoning: openai/gpt-oss-120b - action planning, policy synthesis, complex decisions
- Fast model: openai/gpt-oss-20b - classification, sentiment, urgency, lightweight drafting
- Groq base URL: https://api.groq.com/openai/v1
- Strict structured outputs enforced

### RAG
- Local embedding model (bge-m3 or equivalent)
- Qdrant vector database
- Hybrid retrieval (dense + BM25)
- FlashRank reranker
- 15-25 policy documents with versioning

### Observability
- Langfuse for LLM tracing
- Append-only audit log with hash chaining
- PII redaction before logs

### Infrastructure
- Docker Compose
- GitHub Actions CI/CD

---

## Core Design Separation

| Component | Role |
|---|---|
| RAG | What does policy/documentation say? |
| Groq | What action should I propose? |
| LangGraph | What workflow step comes next? |
| Policy Engine | Is this action allowed? |
| Approval | Does a human approve this risky action? |
| Gateway | Is this exact action authorized? |
| MCP | How do I reach the business system? |
| Backend | Perform the actual operation. |
| Verification | Did it actually happen? |
| Audit | Can we reconstruct everything? |

---

## Repository Structure

```
resolveops/
├── README.md
├── .env.example
├── docker-compose.yml
├── frontend/          # Next.js App Router
├── backend/           # FastAPI + LangGraph
├── services/          # Gateway + MCP servers + mocks
├── rag/               # Documents, ingestion, retrieval, reranking
├── policy/            # rules.yaml
├── evals/             # Scenarios, baselines, red-team, reports
├── docs/              # Architecture, permission-model, threat-model, etc.
├── tests/
└── .github/workflows/
```

---

## Key Decisions Made

1. Groq only - no multi-provider in v1
2. Policy Gateway is mandatory - agent never calls backends directly
3. Structured outputs enforced - never parse decisions from free-form text
4. Identity is deterministic - sentiment/urgency cannot override
5. Public reply requires human approval - no auto-send in v1
6. Approval hash-bound - editing action invalidates approval
7. Idempotency on all writes - duplicate side-effects impossible
8. Default deny policy - unknown tools = forbidden
9. No tool for dangerous ops - delete_account, bulk_refund, grant_admin deliberately missing
10. Postgres checkpointing - workflow survives restarts

---

## Environment Variables (Key)

```env
GROQ_API_KEY=
GROQ_MODEL_PRIMARY=openai/gpt-oss-120b
GROQ_MODEL_FAST=openai/gpt-oss-20b
DATABASE_URL=postgresql://resolveops:resolveops@postgres:5432/resolveops
QDRANT_URL=http://qdrant:6333
REDIS_URL=redis://redis:6379/0
LANGFUSE_HOST=http://langfuse:3000
LANGFUSE_PUBLIC_KEY=
LANGFUSE_SECRET_KEY=
ENVIRONMENT=development
```
