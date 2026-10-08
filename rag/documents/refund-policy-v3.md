---
document_id: refund-policy-v3
title: Refund Policy
version: 3
status: active
effective_date: "2025-01-01"
owner: finance@northwindcloud.com
supersedes: refund-policy-v2
---

# Refund Policy v3 (Active)

## 1. Overview

This policy governs all refund requests for Northwind Cloud subscriptions and invoices. Version 3 supersedes all previous versions effective 2025-01-01.

## 2. Refund Eligibility

All refund requests must be submitted within **30 days** of the invoice date.

Refunds will not be processed for invoices older than 30 days.

## 2.1 Eligible Refund Reasons

- Duplicate charge
- Service outage (as documented in status.northwindcloud.com)
- Billing error
- Cancellation within 30-day window

## 2.2 Ineligible Refund Reasons

- Change of mind after 30 days
- Partial usage
- Feature dissatisfaction without documented outage

## 3. Approval Thresholds

### 3.1 Tier 1 — Small Refunds (Support Agent Approval)

Refunds **up to $50** may be approved by a **support agent**.

Requirements:
- Invoice must be within 30-day window
- Account must not be on legal hold
- Account must not be flagged as strategic

### 3.2 Tier 2 — Medium Refunds (Support Lead Approval)

Refunds **between $50 and $500** require **support lead approval**.

Requirements:
- Account must not be on legal hold

### 3.3 Tier 3 — Large Refunds (Finance Escalation Required)

Refunds **exceeding $500** require **Finance Controller escalation**.

These refunds **cannot be processed by the support team** and must be escalated to finance@northwindcloud.com.

## 4. Strategic Accounts

All financial actions on **strategic accounts** require support lead approval, regardless of amount. See `strategic-account-policy.md`.

## 5. Legal Hold Accounts

**No refunds or financial actions** may be processed on accounts flagged as legal hold. All requests must be escalated to legal@northwindcloud.com.

## 6. Idempotency

All refund requests must include a unique idempotency key to prevent duplicate processing. The same idempotency key submitted twice returns the original result without creating a second refund.
