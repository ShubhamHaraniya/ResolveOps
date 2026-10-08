# ResolveOps — System Architecture & Architecture Decision Records (ADRs)

> Platform: Governed AI Agent for Support Operations  
> Fictional Engagement: Northwind Cloud (400-person SaaS, ~1,800 tickets/month)

---

## 1. System Architecture Overview

ResolveOps is structured around a strict separation of concerns: **Intelligence** is provided by fast LLMs, **Workflow & State** are governed by a stateful LangGraph cyclical engine, **Grounding** is provided by dense RAG policy retrieval, **Integration** is standardized via Model Context Protocol (MCP), and **Execution** is strictly bounded by a deterministic 12-step Policy Gateway.

```
                    ┌────────────────────────┐
                    │ Customer Ticket Stream │
                    │   (Zendesk / Webhook)  │
                    └───────────┬────────────┘
                                │
                                ▼
                    ┌────────────────────────┐
                    │    LangGraph Engine    │
                    │ (11-Node Stateful Loop)│
                    └───────────┬────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        ▼                       ▼                       ▼
┌───────────────┐       ┌───────────────┐       ┌───────────────┐
│  Groq Engine  │       │  Qdrant RAG   │       │ Policy Engine │
│gpt-oss-120b/20b│       │(Policy Chunks)│       │  rules.yaml   │
└───────────────┘       └───────────────┘       └───────┬───────┘
                                                        │
                                                        ▼
                                            ┌───────────────────────┐
                                            │ Human-in-the-Loop     │
                                            │ Interrupt (if needed) │
                                            └───────────┬───────────┘
                                                        │
                                                        ▼
                                            ┌───────────────────────┐
                                            │ 12-Step Policy Gateway│
                                            │  (Primary Boundary)   │
                                            └───────────┬───────────┘
                                                        │
        ┌───────────────────────┼───────────────────────┼───────────────────────┐
        ▼                       ▼                       ▼                       ▼
┌───────────────┐       ┌───────────────┐       ┌───────────────┐       ┌───────────────┐
│ Ticketing MCP │       │    CRM MCP    │       │  Billing MCP  │       │  Access MCP   │
└───────────────┘       └───────────────┘       └───────────────┘       └───────────────┘
```

---

## 2. The 12-Step Policy Gateway Sequence

No component inside the AI workflow has network access or credentials to touch backend systems directly. The Policy Gateway is the single enforcement boundary:

1. **`authenticate_run()`**: Validates run-scoped cryptographic JWT (ticket_id, tool, run_id, exp).
2. **`validate_schema()`**: Strict Pydantic tool parameter schema enforcement (`extra="forbid"`).
3. **`validate_provenance()`**: All entity IDs (invoices, accounts, subscriptions) must originate from trusted database records, never LLM hallucinations.
4. **`bind_identity()`**: Requester email is bound to target tenant CRM domain via SPF/DKIM/SSO verification.
5. **`evaluate_policy()`**: Evaluates 25 deterministic rules in `rules.yaml` (`auto`, `approval`, `forbidden`).
6. **`validate_approval()`**: For approval-required actions, verifies `SHA256(ticket_id + ":" + tool + ":" + sorted_json(args))`.
7. **`check_idempotency()`**: Consults idempotency cache. If request was previously committed, returns cached result.
8. **`check_limits()`**: Enforces per-run execution budget (`max_tool_calls=20`, `max_llm_calls=10`, `max_replans=2`).
9. **`audit_start()`**: Emits immutable pre-execution audit record.
10. **`check_kill_switch()`**: Verifies emergency Redis kill switch flag. Short-circuits immediately if tripped.
11. **`execute()`**: Dispatches call to corresponding isolated MCP server.
12. **`audit_result()`**: Records execution outcome and updates tamper-evident SHA-256 hash chain.

---

## 3. Architecture Decision Records (ADRs)

### ADR-001: Deterministic Policy Gateway vs. LLM Self-Governance
* **Decision:** All security boundaries, permission gates, and side-effects must be evaluated by deterministic Python code outside the LLM context.
* **Rationale:** LLMs are vulnerable to prompt injection, jailbreaking, and hallucination. Safety cannot rely on system prompts alone.

### ADR-002: LangGraph Stateful Checkpointing vs. Stateless ReAct Agents
* **Decision:** Use LangGraph with Postgres checkpointers to persist conversation state across asynchronous human approval interrupts.
* **Rationale:** Enterprise ticket resolution requires human-in-the-loop sign-off. Workflows must safely pause for hours without memory loss.

### ADR-003: Model Context Protocol (MCP) Standard for Integrations
* **Decision:** Wrap Ticketing, CRM, Billing, and IAM backends as decoupled MCP microservices.
* **Rationale:** Standardizes tool contracts, enables mock backend swapping in test suites, and enforces principle of least privilege.

### ADR-004: Groq Hardware Acceleration for Inference
* **Decision:** Primary reasoning: `openai/gpt-oss-120b`; Fast classification: `openai/gpt-oss-20b`.
* **Rationale:** Delivers sub-5s proposal latency for multi-step reasoning, minimizing queue time for customers.

### ADR-005: Cryptographically Hash-Bound Human Approvals
* **Decision:** Human approvals bind to `SHA256(ticket_id + tool + normalized_args)`. Any modification invalidates the hash.
* **Rationale:** Prevents TOCTOU (Time-of-Check to Time-of-Use) attacks where an approved $30 refund is manipulated to $300 before execution.

### ADR-006: Mandatory Idempotency and Read-Back Verification
* **Decision:** Every mutating MCP tool requires an `Idempotency-Key`. Unknown or timed-out responses trigger read-back queries.
* **Rationale:** Prevents duplicate charges or double refunds caused by transient network timeouts.

### ADR-007: Tamper-Evident SHA-256 Audit Log Hash Chain
* **Decision:** Each audit record contains `row_hash = SHA256(prev_hash + row_content)`.
* **Rationale:** Guarantees cryptographic immutability and verifiable tamper detection for compliance audits.

### ADR-008: Default-Deny Policy Rule Engine
* **Decision:** Any tool invocation not explicitly permitted by a matching rule in `rules.yaml` defaults to `FORBIDDEN`.
* **Rationale:** Eliminates zero-day tool exposure and prevents unintended capabilities from being triggered.

### ADR-009: Decoupled Next.js 14 / React 19 Frontend
* **Decision:** Build a responsive TypeScript frontend with Tailwind CSS and TanStack Query connecting to the FastAPI backend.
* **Rationale:** Provides operations engineers and compliance leads with rich visual inspection of real-time telemetry, approval queues, and LangGraph traces.
