# Threat model

Scope: the controls that exist in this repository and the gaps that remain. The system is a reference implementation
with mock backends, not a hardened production service.

## Assets

Money-moving and access-granting tool calls (refunds, credits, plan changes, access grants, MFA resets), customer data
in tickets and CRM records, and the audit trail.

## Threats and controls

| Threat | Control in this repo | Gap |
|---|---|---|
| Prompt injection in ticket text or CRM notes | Deterministic pattern scanner (`services/gateway/injection.py`) sets a flag; policy rule SEC-001 forbids all actions when it is set. The LLM never makes the authorization decision. | Pattern matching only: novel phrasings can be missed. Detection flags, authorization is enforced by the policy engine. |
| Agent invents or swaps identifiers | Gateway step 3: every `*_id` / `email` argument must appear in the trusted context gathered from real tool results. | Trusted context is built by the backend nodes; compromise of those is out of scope. |
| Wrong or spoofed requester | `verify_identity` node and gateway step 4 compare the requester email with the account's authorized contacts; writes fail closed without a contact list. | Email From-address is taken as given: no SPF/DKIM verification. |
| Over-privileged actions | Default-deny policy; admin-type access roles forbidden (ACC-099); refunds over $500 forbidden (REF-099); legal-hold accounts forbidden (GEN-001). | Rules are only as good as `rules.yaml`; the offline eval suite checks tiers only. |
| Approval tampering / reuse | Approval is bound to run, ticket, tool and argument hash, expires after 24 h; edited arguments invalidate it. | Reviewer identity and role are not authenticated (see below). |
| Replay of a tool call | Scoped JWT bound to run/ticket/tool/args hash with expiry; idempotency store. | Idempotency store is in memory. |
| Runaway agent | Per-run tool-call budget; kill switch. | Both in-process only; kill switch resets on restart. |
| Forged webhooks | Stripe and Zendesk signature schemes verified when secrets are configured; events de-duplicated. | Unsigned requests are accepted in `ENVIRONMENT=development`. |
| Audit tampering | Hash-chained `audit_log`, `GET /api/audit/verify`; emails and phone-like numbers masked before storage. | A database administrator can rewrite the whole chain; the head hash is not anchored externally. |
| PII leakage to the LLM | None beyond the audit-log masking. | Ticket and CRM text are sent to Groq as-is. |

## Known gaps

- **No authentication or authorization on the REST API.** Anyone who can reach the API can create tickets, approve
  actions (with any `reviewer_id`) and toggle the kill switch. `approver_role` is recorded, not enforced.
- Gateway state is per-process and in memory.
- Backends are mock services and seed data.
- `is_authorized_contact` on ticket creation is a development-only convenience and is ignored outside
  `ENVIRONMENT=development`.
- `GATEWAY_JWT_SECRET` has an insecure default; `ENVIRONMENT=production` refuses to start with the default.
