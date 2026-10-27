# Failure modes

What the code does when things go wrong, and what it does not do.

| Situation | Behavior |
|---|---|
| `GROQ_API_KEY` missing or Groq unreachable | LLM calls raise after `GROQ_MAX_RETRIES` attempts (tenacity retries); the run fails. There is no fallback model and no canned output. |
| PostgreSQL unreachable at startup | The app falls back to a local SQLite file (`backend/resolveops.db`). |
| Qdrant unreachable | RAG falls back to an in-memory index built from `rag/documents/`. |
| Redis unreachable | Only `/ready` reports it; nothing else uses Redis. |
| Embedding model cannot be loaded | A hash-based embedder is used (retrieval quality is lower). |
| Backend service call fails | The gateway returns 502 and records a failure on that service's circuit breaker; after repeated failures the breaker opens and calls return 503 until it recovers. |
| Write times out | The gateway attempts a read-back (`ReadBackVerifier`). Committed → treated as success; cannot be confirmed → 502 "manual reconciliation required"; not committed → 504. `execute` records the action as `unknown_timeout` and `verify_outcome` tries the read-back again by idempotency key. |
| An action fails during `execute` | The run stops at that action and is marked failed with the flag `execution_failed`. Earlier actions are **not** rolled back (there is no compensation/saga mechanism). |
| Identical tool call repeated | The gateway returns the cached result for the same idempotency key (in-memory store). |
| Too many tool calls in one run | Step 8 rejects calls beyond `MAX_TOOL_CALLS_PER_RUN`. |
| Kill switch on | Step 10 rejects every tool call. State is held in process memory and resets on restart. |
| Server restart | In-memory gateway state (approvals registry, idempotency, budgets, kill switch) and the active-run cache are lost. Approval records are re-registered from the database when a reviewer acts; LangGraph checkpoints are in memory only. |
| Unsigned webhook | With a secret configured, a bad signature is rejected (401). With no secret configured, the request is accepted only when `ENVIRONMENT=development`; otherwise it is rejected (503). |

Not provided: automatic retries of failed business actions, rollback of partial execution, distributed locking, or
multi-process consistency.
