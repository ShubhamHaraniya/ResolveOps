# Demo walkthrough

A short manual walkthrough of the running application. It requires a Groq API key, because the classify and plan
steps call the LLM.

## Setup

1. Create `.env` from `.env.example` and set `GROQ_API_KEY`.
2. Start the backend: `uvicorn app.main:app --app-dir backend --port 8000`
3. Start the frontend: `cd frontend && npm install && npm run dev` and open http://localhost:3000
4. Optional: start the mock services (`python -m services.mocks.ticketing`, `.crm`, `.billing`); otherwise the
   in-process tool servers are used.

The database starts with sample customers only — no tickets. Create tickets from the **Tickets** page with
**Create Test Ticket**; the form has presets (Custom / Blank, Amount Mismatch, Normal Refund, Prompt Injection,
Wrong Requester, Admin Access), a customer selector and a "Simulate as Authorized Admin" checkbox that only works when
`ENVIRONMENT=development`.

## Walkthrough

1. **Normal refund** — choose the *Normal Refund* preset and submit. The run should reach `policy_check` and pause for
   approval (rule REF-001). Open **Approvals**, review the exact arguments, approve. The ticket page shows execution,
   the drafted reply and the run's node timeline.
2. **Prompt injection** — choose *Prompt Injection*. The scanner flags the text, SEC-001 forbids the actions and the
   ticket is escalated; no money-moving call is made.
3. **Wrong requester** — choose *Wrong Requester* (an email not on the account's contact list). `verify_identity`
   stops the run.
4. **Admin access** — choose *Admin Access*. ACC-099 forbids it.
5. **Audit** — open **Audit Log**: events per run, with the hash-chain verification result. **Traces** shows each run's
   nodes and timings.
6. **Kill switch** — in **Settings**, turn the kill switch on and run another ticket: tool calls are refused by the
   gateway. Turn it off again.

Outcomes depend on the model's output for the free-text parts, so wording and sometimes proposed actions vary between
runs; the policy tier for a given proposed action does not.
