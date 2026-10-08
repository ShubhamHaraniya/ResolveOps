# ResolveOps — Operational Runbook

> Audience: Site Reliability Engineers, Support Leads, and Security Incident Responders

---

## 1. Emergency Kill Switch Activation

When anomalous agent behavior, novel adversarial attacks, or external backend outages occur:

1. **Via Web Dashboard:**
   - Click the **Kill Switch (Standby)** button in the top navigation.
   - Confirm the modal prompt: "Confirm Emergency Halt".
   - The status banner will turn red across all client sessions.
2. **Via Backend CLI:**
   ```bash
   python -c "from app.reliability.kill_switch import set_kill_switch; set_kill_switch(True)"
   ```
3. **Verification:**
   - All subsequent outgoing tool calls will immediately abort at Gateway Step 10 with a `GATEWAY_HALTED` audit log entry.
   - Read-only actions continue to be served if permitted.

---

## 2. Reconciling Unknown Write Outcomes

If a network timeout occurs during a write to the Billing or CRM MCP service:

1. Locate the `run_id` and `ticket_id` from the Alert in `/audit`.
2. Retrieve the `Idempotency-Key` associated with the request:
   ```bash
   python -c "from app.audit.ledger import get_events_for_ticket; print(get_events_for_ticket('TICK-105'))"
   ```
3. Execute read-back verification against the billing ledger:
   ```bash
   python -c "from app.reliability.readback import verify_charge_status; print(verify_charge_status('idem-hash-123'))"
   ```
4. If the write succeeded, confirm the state match; if it failed, re-submit through the standard gateway pipeline.

---

## 3. Deploying Policy Rule Updates

1. Edit `policy/rules.yaml`.
2. Run the policy regression test suite:
   ```bash
   python -m pytest tests/policy/ -v
   ```
3. Run the evaluation scenario safety gate:
   ```bash
   python -m evals.runner
   ```
4. Verify that `unsafe_action_rate == 0.0%` and `duplicate_side_effect_rate == 0.0%`.
5. Deploy changes to production.

---

## 4. Verifying Audit Ledger Integrity

To ensure that the append-only audit trail has not been modified or truncated:

```bash
python -c "from app.audit.ledger import verify_hash_chain; print(verify_hash_chain())"
```
*Expected Output:* `{"status": "VALID", "records_verified": 482, "tamper_detected": false}`
