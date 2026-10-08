---
document_id: proration-policy
title: Subscription Proration Policy
version: 1
status: active
effective_date: "2025-01-01"
owner: billing@northwindcloud.com
---

# Subscription Proration Policy

## 1. Overview
This policy details the exact proration mathematics and rules governing mid-cycle seat additions, seat removals, and tier changes for Northwind Cloud subscriptions.

## 2. Mid-Cycle Seat Additions
When a customer adds user seats during an active billing cycle:
- Charges are prorated to the exact remaining second of the cycle.
- The formula applied is: `prorated_charge = (seat_price / cycle_days) * remaining_days`.
- Seat additions take effect immediately upon execution.

## 3. Plan Upgrades
Upgrading between plans (e.g., Starter to Pro, or Pro to Enterprise):
- Unused balance of the existing plan is credited immediately against the new plan invoice.
- The new tier features unlock immediately.
- Annual contracts require support lead verification before proration credit is finalized.

## 4. Mid-Cycle Downgrades
Downgrading to a lower plan tier or reducing seat quantity:
- Takes effect at the end of the current billing cycle (no mid-cycle cash refunds).
- Downgrades do not generate refund payouts; credit balances roll over to the next invoice.
