---
document_id: mfa-policy
title: Multi-Factor Authentication (MFA) Reset Policy
version: 1
status: active
effective_date: "2025-01-01"
owner: security@northwindcloud.com
---

# Multi-Factor Authentication (MFA) Reset Policy

## 1. Overview
Mandates verification thresholds and workflow procedures before resetting multi-factor authentication (MFA) credentials on customer accounts.

## 2. Self-Service Reset
- Primary path: Users locked out of their authenticator app should use their emergency recovery codes or secondary verified email OTP.
- Self-service does not involve agent action.

## 3. Agent-Assisted Reset
When an account user requests support-assisted MFA reset:
- Requester must match an authorized contact on file in the CRM with high identity confidence (score >= 0.95).
- If requester email is unverified or domain differs from account domain, reset is FORBIDDEN.
- A reset requires Human Approval from a Security Reviewer before execution.
- Resetting MFA triggers a 24-hour sensitive operation cooldown on the affected account.
