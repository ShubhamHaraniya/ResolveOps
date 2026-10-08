---
document_id: legal-hold-policy
title: Legal Hold Compliance Policy
version: 1
status: active
effective_date: "2025-01-01"
owner: legal@northwindcloud.com
---

# Legal Hold Compliance Policy

## 1. Overview
Mandatory operational rules governing accounts flagged with `legal_hold: true` due to pending litigation, regulatory subpoenas, or intellectual property disputes.

## 2. Strict Freeze of Write Operations
When an account has `legal_hold: true`:
- All automated write operations are strictly FORBIDDEN by Rule GEN-001 in the Policy Gateway.
- No refunds, credits, subscription modifications, user deletions, or access reassignments may be carried out.
- Support agents are prohibited from modifying account metadata.

## 3. Handling Customer Communications
- Acknowledge ticket inquiries neutrally without disclosing internal litigation details.
- Provide no timeline commitments for billing adjustments.
- Immediately escalate the ticket to `legal-escalations@northwindcloud.com`.
