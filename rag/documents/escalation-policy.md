---
document_id: escalation-policy
title: Operational Incident & Department Escalation Policy
version: 1
status: active
effective_date: "2025-01-01"
owner: operations@northwindcloud.com
---

# Operational Incident & Department Escalation Policy

## 1. Overview
Defines explicit department escalation routes and criteria when automated support or tier-1 handling cannot resolve a ticket.

## 2. Finance Department Escalation
Tickets must be routed to `finance@northwindcloud.com` if:
- A requested refund exceeds $500 (Rule REF-099).
- A billing dispute involves wire transfer or ACH reversal.
- A tax exemption certificate requires formal verification.

## 3. Security Operations (SecOps) Escalation
Tickets must be routed to `security@northwindcloud.com` if:
- An adversarial prompt injection attempt is detected.
- An unauthorized user attempts to manipulate credentials or reset MFA.
- Suspected account takeover (ATO) is indicated by IP or geographic anomalies.

## 4. Legal Department Escalation
Tickets must be routed to `legal@northwindcloud.com` if:
- Account is flagged with `legal_hold: true`.
- Customer issues a formal legal demand letter, subpoena, or bankruptcy notice.
