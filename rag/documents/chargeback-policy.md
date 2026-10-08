---
document_id: chargeback-policy
title: Dispute and Chargeback Mitigation Policy
version: 1
status: active
effective_date: "2025-01-01"
owner: finance@northwindcloud.com
---

# Dispute and Chargeback Mitigation Policy

## 1. Overview
Policy outlining operations when a customer files a chargeback or payment dispute through their credit card issuer or bank.

## 2. Immediate Operational Effect
- Any customer filing a chargeback has their write access instantly frozen.
- Support agents and AI automated agents MUST NOT attempt to reverse or process refunds on disputed charges.
- The automated system possesses NO tool for chargeback submission or automated dispute arbitration.

## 3. Escalation Requirements
- All chargeback inquiries must be immediately flagged with tag `chargeback_active` and routed directly to `disputes@northwindcloud.com`.
- Customer tickets regarding chargebacks must receive an informational-only response informing them that the matter is handled exclusively by Risk & Compliance.
