# M6 — MCP Servers & Advanced Reliability · PLAN.md

> **Milestone:** M6 | **Status:** READY TO EXECUTE | **Created:** 2026-10-08  
> **Goal:** Standardized FastMCP tool servers with read/write/destructive/idempotent annotations, PostgreSQL Transactional Outbox pattern, Commit-Timeout Read-Back verification state machine, Circuit Breakers, and Multi-Step Saga compensation coordination.  
> **Tracer slice:** Implement `services/mcp_billing/server.py` with MCP annotations; execute `billing.issue_refund` via Gateway with commit-timeout read-back verification; prove 0 duplicate side effects on timeout.

---

## Execution Strategy

**Wave-parallelized** — independent tasks run in parallel within each wave. No wave starts until the prior wave's outputs are verified.

```
Wave 1  (MCP Servers)     ─── M6-P1: 5 Standardized FastMCP Protocol Servers in services/mcp_*
         ↓
Wave 2  (Outbox Engine)   ─── M6-P2: Transactional Outbox Pattern in backend/app/reliability/outbox.py
         ↓
Wave 3  (Read-Back & Saga)─── M6-P3: Commit-Timeout Read-Back ║ M6-P4: Circuit Breaker & Saga
         ↓
Wave 4  (Gateway Wiring)  ─── M6-P5: Policy Gateway Integration with MCP Servers & Reliability
         ↓
Wave 5  (Verification)    ─── M6-P6: Comprehensive Reliability Unit & Integration Tests (pytest)
```

---

## Pre-Flight Checklist

Before executing any task, confirm:
- [x] Python 3.11/3.12 active (`python --version`)
- [x] All 31 existing unit tests passing (`pytest tests/`)
- [x] All 30 evaluation scenarios passing (`python evals/runner.py`)
- [x] Database models `OutboxEvent` and `IdempotencyRecord` defined in `backend/app/db/models.py`
- [x] Policy Gateway 12-step validation active in `services/gateway/gateway.py`

---

## Wave 1 · Standardized FastMCP Protocol Servers (M6-P1)

**Goal:** Implement all 5 standardized MCP servers in `services/mcp_{name}/server.py` exposing typed schemas and Model Context Protocol annotations (`readOnlyHint`, `destructiveHint`, `idempotentHint`).

### 1.1 `services/mcp_ticketing/server.py`
- **Exposed Tools:**
  1. `get_ticket`: `{"ticket_id": str}` | `readOnlyHint=True, destructiveHint=False, idempotentHint=True`
  2. `list_requester_tickets`: `{"requester_email": str}` | `readOnlyHint=True, destructiveHint=False, idempotentHint=True`
  3. `add_internal_note`: `{"ticket_id": str, "body": str}` | `readOnlyHint=False, destructiveHint=False, idempotentHint=False`
  4. `set_tags`: `{"ticket_id": str, "tags": list[str]}` | `readOnlyHint=False, destructiveHint=False, idempotentHint=True`
  5. `send_public_reply`: `{"ticket_id": str, "body": str}` | `readOnlyHint=False, destructiveHint=True, idempotentHint=False`
- Standard functions: `list_tools() -> list[dict]`, `call_tool(name: str, arguments: dict) -> dict`.

### 1.2 `services/mcp_crm/server.py`
- **Exposed Tools:**
  1. `get_account`: `{"account_id": str}` | `readOnlyHint=True, destructiveHint=False, idempotentHint=True`
  2. `find_contact`: `{"email": str}` | `readOnlyHint=True, destructiveHint=False, idempotentHint=True`
  3. `get_account_notes`: `{"account_id": str}` | `readOnlyHint=True, destructiveHint=False, idempotentHint=True`
  4. `update_contact_email`: `{"contact_id": str, "email": str}` | `readOnlyHint=False, destructiveHint=True, idempotentHint=True`
- Standard functions: `list_tools() -> list[dict]`, `call_tool(name: str, arguments: dict) -> dict`.

### 1.3 `services/mcp_billing/server.py`
- **Exposed Tools:**
  1. `get_invoice`: `{"invoice_id": str}` | `readOnlyHint=True, destructiveHint=False, idempotentHint=True`
  2. `list_invoices`: `{"account_id": str}` | `readOnlyHint=True, destructiveHint=False, idempotentHint=True`
  3. `get_subscription`: `{"subscription_id": str}` | `readOnlyHint=True, destructiveHint=False, idempotentHint=True`
  4. `preview_plan_change`: `{"subscription_id": str, "target_plan": str}` | `readOnlyHint=True, destructiveHint=False, idempotentHint=True`
  5. `issue_refund`: `{"invoice_id": str, "amount_cents": int, "reason": str, "idempotency_key": str}` | `readOnlyHint=False, destructiveHint=True, idempotentHint=True`
  6. `issue_credit`: `{"account_id": str, "amount_cents": int, "reason": str}` | `readOnlyHint=False, destructiveHint=False, idempotentHint=True`
  7. `change_plan`: `{"subscription_id": str, "new_plan": str}` | `readOnlyHint=False, destructiveHint=True, idempotentHint=True`
  8. `pause_subscription`: `{"subscription_id": str, "pause_days": int}` | `readOnlyHint=False, destructiveHint=False, idempotentHint=True`
- Standard functions: `list_tools() -> list[dict]`, `call_tool(name: str, arguments: dict, headers: dict | None = None) -> dict`.

### 1.4 `services/mcp_access/server.py`
- **Exposed Tools:**
  1. `get_user`: `{"email": str}` | `readOnlyHint=True, destructiveHint=False, idempotentHint=True`
  2. `list_grants`: `{"account_id": str}` | `readOnlyHint=True, destructiveHint=False, idempotentHint=True`
  3. `grant_access`: `{"account_id": str, "user_email": str, "role": str, "expiry_days": int, "reason": str}` | `readOnlyHint=False, destructiveHint=True, idempotentHint=True` (strictly enforces allowed roles `viewer`, `member`, rejects `admin`)
  4. `reset_mfa`: `{"email": str, "account_id": str, "reason": str}` | `readOnlyHint=False, destructiveHint=True, idempotentHint=True`
- Standard functions: `list_tools() -> list[dict]`, `call_tool(name: str, arguments: dict) -> dict`.

### 1.5 `services/mcp_kb/server.py`
- Already active with `search_policy` tool (`readOnlyHint=True, destructiveHint=False, idempotentHint=True`).
- Verify input schema and full registration.

### 1.6 Unified MCP Registry (`services/mcp_registry.py`)
- Central hub mapping `prefix.tool_name` (e.g. `billing.issue_refund`, `ticketing.add_internal_note`, `kb.search_policy`) to the corresponding server and tool schema.
- Provides `list_all_tools() -> list[dict]`, `get_tool_metadata(tool_name: str) -> dict`, and `dispatch_tool(tool_name: str, args: dict, headers: dict | None = None) -> dict`.

---

## Wave 2 · Transactional Outbox Pattern (M6-P2)

**Goal:** Implement PostgreSQL Transactional Outbox in `backend/app/reliability/outbox.py` ensuring atomic persistence of workflow decisions and side-effect intent.

### 2.1 Outbox Storage & Lifecycle (`backend/app/reliability/outbox.py`)
- Employs `OutboxEvent` table from `backend/app/db/models.py`.
- **Core Methods:**
  - `record_intent(session, event_type: str, payload: dict) -> OutboxEvent`: Enqueues an outbox record inside the active DB transaction.
  - `fetch_pending_events(session, limit: int = 50) -> list[OutboxEvent]`: Retrieves unprocessed events ordered by `created_at`.
  - `mark_processed(session, event_id: str) -> None`: Updates status to `processed` and sets `processed_at = now_utc`.
  - `mark_failed(session, event_id: str, error: str, retry_count: int) -> None`: Updates status to `failed` or increments retry count with backoff.
- **Outbox Processor (`OutboxProcessor`):**
  - Background worker / async execution loop that iterates through pending events, dispatches them via Policy Gateway, and handles failures with exponential retry.
  - Guarantees: System crash between decision commit and external side-effect dispatch does NOT lose the intent.

---

## Wave 3 · Read-Back Verification & Circuit Breakers / Saga (M6-P3, M6-P4)

**Goal:** Implement advanced reliability patterns: commit-timeout read-back verification state machine, sliding-window circuit breakers, and multi-step saga compensation.

### 3.1 Commit-Timeout Read-Back Verification (`backend/app/reliability/readback.py`)
- Resolves Failure Mode #6: HTTP timeout occurs *after* backend has already committed the transaction.
- **`ReadBackVerifier` State Machine:**
  - States: `COMMITTED`, `NOT_COMMITTED`, `INDETERMINATE`.
  - Protocol on timeout:
    1. Intercept `httpx.TimeoutException` or simulated network drop on write operations (refund, credit, plan change).
    2. Instead of blind retry (which risks double debit), execute read-back probe:
       - Query invoice status or recent refunds via `billing.get_invoice` / `billing.list_invoices` matching `idempotency_key` or recent amount.
    3. If payment/refund is verified present $\rightarrow$ state = `COMMITTED`: synthesize success response, cache in idempotency store, proceed without re-executing.
    4. If definitely not applied $\rightarrow$ state = `NOT_COMMITTED`: safe to perform single controlled retry.
    5. If unconfirmed $\rightarrow$ state = `INDETERMINATE`: halt autonomous processing, flag ticket for human finance reconciliation (`requires_manual_reconciliation=True`).

### 3.2 Sliding-Window Circuit Breakers (`backend/app/reliability/circuit_breaker.py`)
- Prevents cascading failures and resource exhaustion across backends (`ticketing`, `crm`, `billing`, `iam`, `kb`).
- **States:**
  - `CLOSED`: Normal operation, calls pass through.
  - `OPEN`: Tripped after consecutive failure threshold (default: 5 consecutive 500s or timeouts). Calls fail immediately with `CircuitOpenError`.
  - `HALF_OPEN`: Trial state after recovery timeout (default: 30s). Probes system with limited calls (requires 3 consecutive successes to return to `CLOSED`).
- **Failover Action:**
  - When circuit is `OPEN`, gateway fails fast and routes new tickets affecting that backend to the human support queue with an operational alert note.

### 3.3 Multi-Step Saga Coordinator (`backend/app/reliability/saga.py`)
- Coordinates multi-service state changes (e.g. `billing.change_plan` + `crm.update_notes` + `ticketing.add_internal_note`).
- **Saga Engine:**
  - Maintains execution journal with forward actions and registered compensation handlers.
  - If step $N$ fails after retries:
    - Executes compensating transactions in reverse order (steps $N-1 \dots 1$).
    - If compensation succeeds: Ticket is cleanly rejected or reverted.
    - If compensation fails: Flags `manual_reconciliation_required=True` and emits high-priority audit event.

---

## Wave 4 · Policy Gateway Integration (M6-P5)

**Goal:** Wire `services/gateway/gateway.py` to use `services/mcp_registry.py`, `ReadBackVerifier`, and `CircuitBreaker`.

### 4.1 Update `services/gateway/gateway.py`
- Step 11 (`step11_execute`): Dispatch via `mcp_registry.dispatch_tool(...)` protected by the appropriate service `CircuitBreaker`.
- Wrap write tool calls with `ReadBackVerifier` to handle potential timeouts.
- Record intent in `OutboxEvent` for asynchronous / outbox-mode operations.

---

## Wave 5 · Comprehensive Reliability Test Suite (M6-P6)

**Goal:** Author and execute unit and integration test suites validating all M6 deliverables.

### 5.1 Test Files:
- `tests/reliability/test_mcp_servers.py`:
  - Validates `list_tools()` on all 5 MCP servers.
  - Verifies presence and correctness of `readOnlyHint`, `destructiveHint`, `idempotentHint` annotations.
  - Verifies that forbidden roles (`admin`, `prod-admin`) are rejected at the MCP access server level.
- `tests/reliability/test_outbox.py`:
  - Tests atomic `record_intent`.
  - Tests outbox processor event lifecycle (`pending` $\rightarrow$ `processed` / `failed`).
- `tests/reliability/test_readback.py`:
  - Tests `ReadBackVerifier` with simulated commit-then-timeout.
  - Verifies `COMMITTED` resolution avoids duplicate write.
- `tests/reliability/test_circuit_breaker.py`:
  - Tests `CLOSED` $\rightarrow$ `OPEN` transition after 5 errors.
  - Tests `OPEN` fast-fail behavior.
  - Tests `HALF_OPEN` recovery transition.
- `tests/reliability/test_saga.py`:
  - Tests successful multi-step execution.
  - Tests reverse compensation on partial failure.
  - Tests escalation when compensation fails.

---

## M6 Definition of Done Checklist

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
- [ ] `.planning/ROADMAP.md` and `.planning/STATE.md` updated with M6 results
