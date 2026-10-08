# M3 — Frontend & Polish

> Milestone: 3 of 3 | Timeline: Week 3 | Status: ✓ COMPLETE

**Goal:** Full enterprise frontend, final security hardening, CI safety gates, complete documentation, demo-ready.

**Unlock condition:** M2 Definition of Done fully checked (COMPLETED).

**Design reference:** Linear, Stripe Dashboard, Intercom, Retool, Vercel  
**Design language:** Dark navy sidebar · White/light-gray content · Blue primary · Green success · Amber approval · Red forbidden · 8-12px radius · Dense information design

---

## Phases

### M3-P1 · Frontend Shell & Design System

**Status:** ✓ COMPLETE

**Deliverables:**
- [x] `frontend/` — Next.js 16 App Router project with TypeScript
- [x] Design tokens: colors (navy-900, navy-800, blue-600, green-500, amber-500, red-500), spacing, typography
- [x] Global layout: `app/layout.tsx` with header + sidebar + main
- [x] Sidebar: ResolveOps logo, 9 nav items, "Connected Systems" status row at bottom
- [x] Skeleton loading components: `SkeletonCard`, `SkeletonTable`
- [x] State components: `EmptyState`, `ErrorState`, `ForbiddenState`, `DegradedState`
- [x] Store & reactive state provider: `lib/store.tsx`
- [x] Domain types and utility library: `lib/types.ts`, `lib/utils.ts`

---

### M3-P2 · Dashboard Page

**Status:** ✓ COMPLETE

**Route:** `/dashboard`

**Deliverables:**
- [x] 5 KPI cards: Tickets Today, Automation Rate, Approval Acceptance, Median Proposal Time, Unsafe Actions
- [x] Chart 1 (Recharts): Tickets by Resolution Tier (stacked bar: auto/approval/forbidden/escalated)
- [x] Chart 2 (Recharts): Automation Trajectory trend (area)
- [x] Chart 3: System Health grid with ping latencies
- [x] Recent activity feed (live policy enforcement events with ticket links)
- [x] Kill switch status banner (red emergency banner when tripped)
- [x] DEMO MODE banner (persistent top bar)

---

### M3-P3 · Tickets List & Ticket Detail

**Status:** ✓ COMPLETE

**Routes:** `/tickets` (list) · `/tickets/[id]` (detail)

**Deliverables — List:**
- [x] Data table: Ticket #, Customer, Subject, Category, Priority, Tier badge, Status, Created, Confidence
- [x] Filter panel: Status, Category, Tier, Priority
- [x] Search bar: ticket ID, customer, subject (debounced)
- [x] Tier badges: auto=blue, approval=amber, forbidden=red, escalated=orange

**Deliverables — Detail (3-column layout):**
- [x] Left column: Customer profile card (Plan, ARR, Strategic badge, Legal Hold badge, Owner, CSM), Identity verification card, Invoices list
- [x] Center column: Conversation transcript, Evidence panel (CRM and Billing verified grounding data)
- [x] Right column: AI analysis card, Risk flags list, RAG citation cards, Proposed Action card with expandable API effect and SHA-256 hash
- [x] Action buttons: `Approve & Execute via Gateway`, `Edit`, `Reject`, `Escalate`

---

### M3-P4 · Approval Queue

**Status:** ✓ COMPLETE

**Route:** `/approvals`

**Deliverables:**
- [x] Header: "Approval Queue" + count badge
- [x] Category tabs: All, Financial, Security, Low Confidence, Conflicts
- [x] Table: Ticket, Customer, Action summary, Amount, Risk badge, Policy rule, Age, Expiration countdown
- [x] Inline actions: Inspect, Approve, Reject
- [x] Full approval modal: exact API effect, cryptographic SHA-256 hash, justification, approve/reject

---

### M3-P5 · Customers, Knowledge Base, Audit Pages

**Status:** ✓ COMPLETE

**Routes:** `/customers` · `/knowledge-base` · `/audit`

**Deliverables — Customers:**
- [x] Table: Customer, Plan, ARR, Governance tags (Strategic, Legal Hold), Owner, CSM, Status

**Deliverables — Knowledge Base:**
- [x] Document list: Name, Version, Status (active/deprecated), Owner, Last Updated
- [x] Policy conflict warning card (v2.0 vs v3.1 refund terms)
- [x] Document viewer with markdown content

**Deliverables — Audit:**
- [x] Filter bar: Actor, Event, Search
- [x] Full audit timeline with timestamps, actors, tools, policies, row hashes
- [x] CSV and JSON export buttons
- [x] Hash chain integrity indicator

---

### M3-P6 · Analytics, Traces, Settings

**Status:** ✓ COMPLETE

**Routes:** `/analytics` · `/traces` · `/traces/[runId]` · `/settings`

**Deliverables — Analytics:**
- [x] Metric cards: 12 KPIs
- [x] Chart: Automation by Category (grouped bar)
- [x] Chart: Approval Outcome (pie)
- [x] Chart: Failure Reasons (horizontal bar)
- [x] Chart: Cost Trend per ticket (area)

**Deliverables — Traces:**
- [x] Visual 11-node graph: `intake` &rarr; `classify` &rarr; `verify_identity` &rarr; `gather_context` &rarr; `plan_action` &rarr; `policy_check` &rarr; `approval_interrupt` &rarr; `execute_via_gateway` &rarr; `verify_readback` &rarr; `respond` &rarr; `update_ticket`
- [x] Node latency, Groq model (`openai/gpt-oss-120b`), token counts, estimated cost
- [x] Node inspector drawer: inputs, state transformations, outputs

**Deliverables — Settings:**
- [x] AI section: Primary & Fast Groq model information
- [x] Emergency Global Kill Switch toggle with confirmation modal
- [x] Integrations latency ping diagnostics

---

### M3-P7 · Demo Mode

**Status:** ✓ COMPLETE

**Deliverables:**
- [x] `DEMO MODE` banner with quick shortcut chips
- [x] Demo modal launcher for all 6 scenarios:
  1. Normal Refund ($30)
  2. Prompt Injection Attack
  3. Identity Spoofing Attempt
  4. Admin Role Escalation
  5. Billing Timeout & Read-Back
  6. Legal Hold Account Freeze

---

### M3-P8 · CI/CD Safety Gates + All Documentation

**Status:** ✓ COMPLETE

**Deliverables — CI:**
- [x] `.github/workflows/ci.yml` — full pipeline: lint & typecheck, policy tests, eval scenarios, hard safety gate

**Deliverables — Documentation:**
- [x] `README.md` — all 19 sections
- [x] `docs/architecture.md` — system diagram + 9 ADRs
- [x] `docs/permission-model.md` — capability matrix & residual risks
- [x] `docs/threat-model.md` — STRIDE threats & mitigations
- [x] `docs/failure-modes.md` — 12 failure modes analysis
- [x] `docs/runbook.md` — operational procedures & kill switch runbook
- [x] `docs/demo-script.md` — 5-minute live customer demonstration script

---

## M3 Completion Checklist

- [x] All 9 pages work with responsive layouts
- [x] Demo mode: all 6 scenarios work end-to-end
- [x] Kill switch: toggle &rarr; immediate stop &rarr; resume
- [x] CI: safety gate hard-fails on unsafe action simulation
- [x] README: all 19 sections present
- [x] All 6 docs complete in `docs/`
- [x] Zero build errors across Next.js 16 app
- [x] 100% eval scenario pass rate (0 unsafe actions, 0 duplicate writes)

**PROJECT COMPLETE: M1, M2, AND M3 FULLY DELIVERED & VERIFIED.**
