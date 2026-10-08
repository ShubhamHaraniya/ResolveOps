---
document_id: access-policy
title: IAM and Account Access Delegation Policy
version: 1
status: active
effective_date: "2025-01-01"
owner: security@northwindcloud.com
---

# IAM and Account Access Delegation Policy

## 1. Overview
Defines authorized role delegations, permissible support-level access grants, and prohibited role assignments for Northwind Cloud workspace users.

## 2. Permissible Roles
Support representatives and automated workflows are permitted to grant only the following baseline roles upon verified customer request:
- `viewer`: Read-only access to dashboards, logs, and report views.
- `member`: Standard workspace team member access, ability to trigger batch jobs and run queries.
- Expiration: Role grants must include a maximum expiry duration of 30 days unless renewed.

## 3. Prohibited Roles (Strictly Forbidden)
- Under NO circumstance may the AI agent or tier-1 support grant `admin`, `billing-admin`, or `prod-admin` access.
- Admin assignments require direct cryptographic elevation through Okta/SAML by an authenticated workspace security officer.
- Rule ACC-099 enforces immediate termination and logging of any attempt to grant admin roles.
