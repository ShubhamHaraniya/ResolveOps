# ResolveOps — Failure Modes Analysis & Mitigations

> Engineering Assessment: 12 Real-World Failure Scenarios & Self-Healing Behaviors

---

### 1. Hallucinated Entity Identifiers
* **Mode:** The LLM invents an invoice number (e.g. `INV-999-FAKE`) not present in the customer record.
* **Mitigation:** Gateway Step 3 (`validate_provenance`) checks database existence before routing. Halts with `PROVENANCE_ERROR`.

### 2. Stale Approval Invalidation
* **Mode:** Human approves an action after 25 hours, or the customer enters strategic/legal-hold status while approval is pending.
* **Mitigation:** Approvals expire after 24 hours. The gateway re-evaluates `account.is_legal_hold` and `account.is_strategic` at execution time.

### 3. Outdated RAG Policy Documents
* **Mode:** Knowledge base contains legacy v2.0 policy and active v3.1 policy.
* **Mitigation:** Cross-document conflict detector flags discrepancies and defaults to the highest semantic version timestamp.

### 4. Network Timeout During Write Commit
* **Mode:** Billing service commits a $30 refund, but the network connection drops before HTTP 200 is delivered.
* **Mitigation:** Read-back verification queries the billing ledger by `Idempotency-Key` to verify status before returning.

### 5. Groq Rate Limiting (HTTP 429 / 503)
* **Mode:** High ticket burst causes Groq API throttling.
* **Mitigation:** `groq_client.py` implements exponential backoff with jitter and automated fallback to the fast model (`openai/gpt-oss-20b`).

### 6. Infinite Re-Planning Loops
* **Mode:** Agent encounters unexpected errors and repeatedly attempts to replan without progressing.
* **Mitigation:** Hard limit of `max_replans=2` and `max_tool_calls=20` enforced by Gateway Step 8. Exceeding limits halts and escalates to a human manager.

### 7. Approval Queue Starvation
* **Mode:** Human support agents do not review pending approvals within SLA window.
* **Mitigation:** Approvals feature countdown timers (amber &lt; 2h, red &lt; 30m) and automatic escalation to on-call Support Leads.

### 8. Partial Saga Execution Failure
* **Mode:** Tool A succeeds (plan change in CRM), but Tool B fails (invoice generation in Stripe).
* **Mitigation:** Saga coordinator executes compensating transactions (reverts CRM plan change) to maintain system consistency.

### 9. Redis Cache Outage
* **Mode:** Redis instance storing the emergency kill switch flag becomes unreachable.
* **Mitigation:** Gateway falls back to PostgreSQL persistent configuration table, maintaining default-deny security.

### 10. Accidental PII Leakage in Audit Trails
* **Mode:** Customer tickets contain personal emails, credit cards, or passwords.
* **Mitigation:** PII redaction engine regex-masks all emails (`s***@acme.com`), SSNs, and payment card numbers before database write.

### 11. Tampered Audit Ledger
* **Mode:** Malicious insider attempts to modify past audit events directly in PostgreSQL.
* **Mitigation:** Every audit record incorporates `row_hash = SHA256(prev_hash + row_content)`. The verification script detects broken chain links immediately.

### 12. Circuit Breaker Flapping
* **Mode:** Flaky third-party service causes circuit breaker to alternate between OPEN and HALF-OPEN.
* **Mitigation:** Sliding window circuit breaker requires 5 consecutive healthy responses before transitioning to CLOSED state.
