---
document_id: billing-policy
title: Master Billing & Payment Terms Policy
version: 1
status: active
effective_date: "2025-01-01"
owner: billing@northwindcloud.com
---

# Master Billing & Payment Terms Policy

## 1. Overview
Governs payment cycles, accepted payment methods, currency handling, and payment collection schedules across all Northwind Cloud tenant accounts.

## 2. Payment Terms
- Self-serve credit card accounts: Charged immediately on invoice creation date.
- Invoiced accounts: Standard Net 30 payment terms unless contracted otherwise in an Enterprise MSA.
- Default currency is USD ($). International transactions are processed in USD equivalent.

## 3. Dunning & Retry Schedule
In the event of a failed card charge:
- Retry 1: 3 days after initial failure.
- Retry 2: 5 days after Retry 1.
- Retry 3: 7 days after Retry 2.
- If all 3 automated retries fail, account transitions to Past Due status and grace period begins.

## 4. Grace Period and Account Suspension
- Accounts enjoy a 14-day grace period following final payment retry.
- After 14 days without resolution, account enters suspended state (read-only access).
- Automated agent cannot waive suspension without Finance approval.
