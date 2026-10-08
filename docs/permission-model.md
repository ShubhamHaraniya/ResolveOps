# ResolveOps — Permission Model & Capability Matrix

> Customer: Northwind Cloud  
> Version: 2026.10  
> Security Posture: Zero Trust / Default Deny

---

## 1. Tool Capability Classification

Every MCP tool exposed to the ResolveOps agent is categorized into one of four deterministic permission tiers:

| Tier | Policy Behavior | Human Involvement | Examples |
|---|---|---|---|
| **Tier 1: Safe Read-Only** | Auto-executed | None | `billing.get_invoice`, `crm.get_account`, `kb.search` |
| **Tier 2: Low-Risk Write** | Approval Required | Support Agent | `billing.issue_refund` (&le; $100), `ticket.add_note` |
| **Tier 3: High-Risk Write** | Approval Required | Support Lead / Security Lead | `billing.issue_refund` (&gt; $100), `iam.reset_mfa` |
| **Tier 4: Permanently Forbidden** | Hard Block (403) | None (Agent blocked) | `iam.grant_role` (`prod-admin`, `admin`), `billing.refund` (&gt; $50k) |

---

## 2. Granular Authorization Matrix

| Tool Invocations | Pre-conditions | Evaluation Rule | Required Role | Risk Assessment |
|---|---|---|---|---|
| `billing.get_invoice` | Verified tenant | READ-001 | Autonomous | Zero side-effect |
| `crm.get_account` | Requester domain match | READ-002 | Autonomous | Zero side-effect |
| `ticket.add_internal_note` | Active ticket | NOTE-001 | Autonomous | Internal documentation only |
| `billing.issue_refund` (&le; $100) | Duplicate charge verified | REF-001 | Support Agent | Low financial liability |
| `billing.issue_refund` ($101 - $1,000) | Invoice valid | REF-002 | Support Lead | Moderate financial liability |
| `billing.issue_refund` (&gt; $50,000) | Any | REF-999 | FORBIDDEN | Catastrophic financial risk |
| `iam.reset_mfa` | Hardware MFA verified contact | IAM-002 | Security Reviewer | Account takeover mitigation |
| `iam.grant_role` (`prod-admin`) | Any | ACC-099 | FORBIDDEN | Privilege escalation risk |
| `crm.update_plan` | Strategic / Legal hold | GEN-001 | FORBIDDEN | Compliance violation risk |

---

## 3. Residual Risk Analysis

1. **Compromised Authorized Contact:** If an attacker compromises an authorized user's primary SSO credentials, they can request refunds up to $100.  
   *Mitigation:* Anomaly detection on ticket volume, daily refund caps per tenant ($500), and mandatory human review before dispatch.
2. **Reviewer Rubber-Stamping:** Human reviewers approving actions without reading the exact arguments.  
   *Mitigation:* The UI forces preview of exact financial amounts, invoice dates, and risk badges before enabling the "Approve" button.
