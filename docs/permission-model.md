# Permission model

Authorization is decided by deterministic code (`policy/rules.yaml` + `backend/app/policy/engine.py`) and enforced
by the gateway (`services/gateway/gateway.py`). The LLM only proposes actions.

## Tiers

| Tier | Meaning |
|---|---|
| `auto` | May execute without a human. |
| `approval` | Requires a human reviewer's approval of the exact arguments. |
| `forbidden` | Never executes; the run is escalated. |

If several proposed actions get different tiers, the most restrictive wins. A tool with no matching rule is `forbidden`.

## Rules in `policy/rules.yaml` (version 3)

| Rule | Tool | Condition | Tier |
|---|---|---|---|
| TKT-001 | `ticketing.add_internal_note` | — | auto |
| TKT-002 | `ticketing.send_public_reply` | — | approval (support_agent) |
| TKT-003 | `ticketing.set_tags` | — | auto |
| REF-001 | `billing.issue_refund` | ≤ $50, not strategic, no legal hold, invoice ≤ 30 days old | approval (support_agent) |
| REF-002 | `billing.issue_refund` | $50–$500, no legal hold | approval (support_lead) |
| REF-099 | `billing.issue_refund` | > $500 | forbidden → finance |
| CRD-001 | `billing.issue_credit` | ≤ $100, no legal hold | approval (support_agent) |
| CRD-002 | `billing.issue_credit` | $100–$1000, no legal hold | approval (support_lead) |
| PLN-001 | `billing.change_plan` | no legal hold | approval (support_agent) |
| PLN-002 | `billing.pause_subscription` | no legal hold | approval (support_lead) |
| ACC-001 | `access.grant_access` | role viewer/member, expiry ≤ 30 days, requester is an authorized contact | approval (security_reviewer) |
| ACC-002 | `access.reset_mfa` | requester is an authorized contact | approval (security_reviewer) |
| ACC-099 | `access.grant_access` | role admin / prod-admin / owner / superuser / root / administrator | forbidden → security |
| SEC-001 | any (`*`) | injection suspected | forbidden → security (priority 1100) |
| GEN-001 | any (`*`) | account on legal hold | forbidden → legal (priority 1000) |
| GEN-002 | `billing.*` | strategic account | approval (support_lead) (priority 900) |
| RD-001 … RD-009 | `billing.get_invoice`, `billing.get_subscription`, `billing.list_invoices`, `billing.preview_plan_change`, `crm.get_account`, `crm.find_contact`, `access.get_user`, `access.list_grants`, `kb.search_policy` | — | auto |

Refund and credit amounts are in cents in the rule conditions.

## Approvals

When a run reaches `approval_interrupt` an approval record is created holding the tool, the arguments, an argument
hash, and a 24-hour expiry. Reviewers use `POST /api/approvals/{id}/approve | reject | edit | escalate`.
At execution the gateway requires that the approval belongs to the same run, ticket and tool, has status `approved`,
is not expired, and that its hash matches the arguments being executed — editing arguments after approval
invalidates it.

Limitations to be aware of:

- The REST API has no authentication. `approver_role` is stored with the approval but is **not enforced**, and
  `reviewer_id` is whatever the client sends.
- Approval records and the other gateway state are in-memory (see [failure-modes.md](failure-modes.md)).
- One approval-tier action per run is supported.
