# Runbook

Operational procedures for a running ResolveOps backend. Commands assume the repository root as working directory
and an activated Python 3.12 environment with `requirements.txt` installed.

## Start and check

```bash
uvicorn app.main:app --app-dir backend --port 8000     # add --reload for development
curl localhost:8000/health        # liveness
curl localhost:8000/ready         # database / redis / qdrant status (redis and qdrant are optional)
```

Interactive API docs are served by FastAPI at `/docs`.

## Kill switch

Halts every gateway tool call (gateway step 10). Read the state, turn it on, turn it off:

```bash
curl localhost:8000/api/admin/kill-switch
curl -X POST localhost:8000/api/admin/kill-switch -H 'content-type: application/json' -d '{"active": true}'
curl -X POST localhost:8000/api/admin/kill-switch -H 'content-type: application/json' -d '{"active": false}'
```

The Settings page in the frontend has the same toggle and a banner is shown while it is active.
The state is in process memory: it applies to one backend process and resets on restart. The endpoint is
unauthenticated — do not expose the API publicly.

## Verify the audit chain

```bash
curl localhost:8000/api/audit/verify
```

Returns `valid`, event counts and the head hash. Use `GET /api/audit/tickets/{ticket_id}` for one ticket's events and
`GET /api/audit/export/{ticket_id}` for an export.

## Unknown write outcome (timeout)

If a write times out, the gateway tries a read-back. If it answers 502 "manual reconciliation required", check the
billing/CRM system for the operation using the idempotency key recorded in the audit events for the ticket
(`/api/audit/tickets/{ticket_id}`), then resolve the ticket manually. The workflow does not retry on its own.

## Changing policy rules

1. Edit `policy/rules.yaml` (or point `POLICY_FILE` at another file).
2. `python -m pytest tests/policy tests/evals -q`
3. `python -m evals.runner --no-write` — fails if a scenario resolves to a different tier than declared.
4. Restart the backend.

## Policy documents

`GET/POST/PUT /api/policies` manage the Markdown files in `rag/documents/`; `POST /api/policies/reindex` rebuilds the
index. These documents are informational context — editing them does not change what is allowed.

## Database

Tables are created at startup. There are no migrations: schema changes to existing databases need manual handling or
deleting the local SQLite file (`backend/resolveops.db`) in development. Set `SEED_DEMO_DATA=true` to also insert
synthetic sample tickets and audit history.
