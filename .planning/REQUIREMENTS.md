# ResolveOps — Requirements

> Version: 1.0 | Status: APPROVED | Date: 2026-10-08

---

## 1. Functional Requirements

### 1.1 Ticket Processing

| ID | Requirement | Priority |
|---|---|---|
| FR-001 | System must accept support tickets via REST API | P0 |
| FR-002 | System must classify tickets by category, urgency, sentiment, and confidence using Groq fast model | P0 |
| FR-003 | System must verify requester identity against CRM authorized contacts | P0 |
| FR-004 | System must gather billing, CRM, and subscription context for every ticket | P0 |
| FR-005 | System must retrieve relevant policy documents via hybrid RAG | P0 |
| FR-006 | System must propose a typed, structured action using Groq primary model | P0 |
| FR-007 | System must evaluate every proposed action through the policy engine | P0 |
| FR-008 | System must route auto-tier actions directly to gateway execution | P0 |
| FR-009 | System must route approval-tier actions to human approval queue | P0 |
| FR-010 | System must block forbidden-tier actions and escalate | P0 |
| FR-011 | System must verify action outcomes after execution | P0 |
| FR-012 | System must draft a customer reply (pending human review) | P0 |
| FR-013 | System must write an audit record for every event | P0 |

### 1.2 Policy & Authorization

| ID | Requirement | Priority |
|---|---|---|
| FR-020 | Policy engine must evaluate rules from policy/rules.yaml | P0 |
| FR-021 | Policy must use default-deny for unknown tools | P0 |
| FR-022 | Policy must check account.strategic flag before any financial action | P0 |
| FR-023 | Policy must check account.legal_hold flag before any action | P0 |
| FR-024 | Policy must enforce per-rule approval role requirements | P0 |
| FR-025 | Policy must detect and surface contradictory policy versions | P0 |
| FR-026 | RAG must prefer active/latest policy version when conflict exists | P0 |

### 1.3 Gateway Security

| ID | Requirement | Priority |
|---|---|---|
| FR-030 | Gateway must authenticate every workflow run | P0 |
| FR-031 | Gateway must validate tool schemas via Pydantic | P0 |
| FR-032 | Gateway must validate provenance of all IDs in action arguments | P0 |
| FR-033 | Gateway must bind action to requester identity | P0 |
| FR-034 | Gateway must validate approval hash before executing approved actions | P0 |
| FR-035 | Gateway must enforce idempotency using hash-keyed execution store | P0 |
| FR-036 | Gateway must enforce per-run rate and budget limits | P0 |
| FR-037 | Gateway must write audit start and result events | P0 |
| FR-038 | Gateway must respect global kill switch | P0 |

### 1.4 Approval System

| ID | Requirement | Priority |
|---|---|---|
| FR-040 | Approval must be required for: refund, credit, plan change, seat change, subscription pause, access grant, MFA reset, public reply | P0 |
| FR-041 | Approval must be hash-bound to exact action arguments | P0 |
| FR-042 | Approval must expire after 24 hours | P0 |
| FR-043 | Reviewer must be able to Approve, Edit then approve, Reject, or Escalate | P0 |
| FR-044 | Editing an action must revalidate policy before re-execution | P0 |
| FR-045 | Account/ticket state changes must invalidate pending approvals | P0 |

### 1.5 Reliability

| ID | Requirement | Priority |
|---|---|---|
| FR-050 | Workflow state must be checkpointed to Postgres via LangGraph | P0 |
| FR-051 | Workflow must survive worker crash and resume from checkpoint | P0 |
| FR-052 | All writes must use idempotency keys | P0 |
| FR-053 | System must implement read-back verification for unknown-outcome writes | P0 |
| FR-054 | Multi-step actions must implement saga-style partial failure handling | P0 |
| FR-055 | Transient errors must retry with exponential backoff and jitter | P0 |
| FR-056 | Circuit breakers must trigger on repeated service failures | P0 |
| FR-057 | System must use Postgres outbox for atomic side-effect intent recording | P0 |

### 1.6 RAG

| ID | Requirement | Priority |
|---|---|---|
| FR-060 | RAG must ingest 15-25 policy documents | P0 |
| FR-061 | RAG must use section-aware chunking (not naive fixed-size) | P0 |
| FR-062 | RAG must store chunks in Qdrant with full metadata | P0 |
| FR-063 | RAG must use hybrid retrieval: dense + BM25 | P0 |
| FR-064 | RAG must rerank with FlashRank and return top 3-5 chunks | P0 |
| FR-065 | Every retrieved chunk must have traceable citation metadata | P0 |
| FR-066 | UI must display chunk citations with source document and section | P0 |
| FR-067 | RAG conflicts must be surfaced and flagged for human review | P0 |

### 1.7 Observability & Audit

| ID | Requirement | Priority |
|---|---|---|
| FR-070 | Langfuse must trace every workflow, node, LLM call, tool call, and decision | P0 |
| FR-071 | Audit log must be append-only with hash chaining for tamper evidence | P0 |
| FR-072 | PII must be redacted before logs and traces | P0 |
| FR-073 | Cost must be tracked per ticket (model, tokens, estimated cost) | P0 |
| FR-074 | Audit log must be exportable in JSON/CSV format | P1 |

---

## 2. Non-Functional Requirements

### 2.1 Performance

| ID | Requirement | Target |
|---|---|---|
| NFR-001 | Median proposal latency | < 20 seconds |
| NFR-002 | Dashboard page load | < 2 seconds |
| NFR-003 | Policy evaluation latency | < 100ms |
| NFR-004 | RAG retrieval latency | < 500ms |

### 2.2 Security

| ID | Requirement | Priority |
|---|---|---|
| NFR-010 | GROQ_API_KEY must never be exposed to frontend | P0 |
| NFR-011 | Secrets must never be committed to git | P0 |
| NFR-012 | Tools must not accept arbitrary SQL, Python, shell, or URLs | P0 |
| NFR-013 | Untrusted data (ticket body, CRM notes) must be treated as data, not instructions | P0 |
| NFR-014 | All numeric tool arguments must be bounded | P0 |
| NFR-015 | All role arguments must use enums | P0 |

### 2.3 Reliability

| ID | Requirement | Target |
|---|---|---|
| NFR-020 | Unsafe action rate | 0 |
| NFR-021 | Duplicate side-effect rate | 0 |
| NFR-022 | Workflow must recover from crash within | < 30 seconds |

### 2.4 Accessibility & UX

| ID | Requirement | Priority |
|---|---|---|
| NFR-030 | UI must support keyboard navigation | P1 |
| NFR-031 | UI must show skeleton loading states | P0 |
| NFR-032 | Destructive actions must require explicit confirmation | P0 |
| NFR-033 | Internal errors must never be shown raw to users | P0 |
| NFR-034 | Every page must handle: loading, empty, success, error, forbidden, approval, degraded states | P0 |

---

## 3. Evaluation Requirements

| ID | Requirement | Count |
|---|---|---|
| EVAL-001 | Auto-tier scenarios | 6 |
| EVAL-002 | Approval-tier scenarios | 8 |
| EVAL-003 | Forbidden-tier scenarios | 5 |
| EVAL-004 | Adversarial scenarios | 7 |
| EVAL-005 | Reliability scenarios | 4 |
| EVAL-006 | Total minimum scenarios | 30 |
| EVAL-007 | Each scenario run minimum times | 5 |
| EVAL-008 | Naive baseline for comparison | Required |
| EVAL-009 | Ablation tests for each security control | Required |

---

## 4. Documentation Requirements

| ID | Document | Location |
|---|---|---|
| DOC-001 | README with all 19 sections | README.md |
| DOC-002 | Architecture document with ADRs | docs/architecture.md |
| DOC-003 | Permission model | docs/permission-model.md |
| DOC-004 | Threat model | docs/threat-model.md |
| DOC-005 | Failure modes | docs/failure-modes.md |
| DOC-006 | Runbook | docs/runbook.md |
| DOC-007 | Demo script (5-minute) | docs/demo-script.md |

---

## 5. Demo Requirements

| Scenario | Expected Behavior |
|---|---|
| Normal Refund | Full happy path: classify → verify → gather → propose → approve → execute → verify → draft reply |
| Prompt Injection | injection_suspected flag → gateway denial → escalation → no financial write |
| Wrong Requester | Identity mismatch → no write → human verification |
| Admin Access | FORBIDDEN — admin roles not available to agent |
| Billing Timeout | Read-back → find by idempotency key → no duplicate refund |
| Stale Approval | Approval invalidated → new proposal required |

---

## 6. Cut Priority (If Time-Limited)

### Can Cut
1. Cloud deployment (Terraform, etc.)
2. Extra model comparisons
3. OPA/Rego integration
4. Advanced audit hashing visualization
5. Extra visual polish

### Must NOT Cut
- Policy Gateway
- Scenario suite (30+)
- Failure modes documentation
- Identity verification
- Idempotency
- Read-back verification
- Red-team tests
- Audit trail
