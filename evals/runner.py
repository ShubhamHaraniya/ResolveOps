"""
Offline policy-layer scenario suite.

Replays the YAML scenarios in ``evals/scenarios`` through the deterministic parts of the
governance stack, without an LLM, network or database:

* identity check   - requester must be an authorized contact (mock CRM seed data)
* injection scan   - ``services.gateway.injection.scan_all_context`` over ticket text and CRM notes
* provenance check - the invoice must belong to the requesting account
* approval hash    - executed arguments must hash to what was approved (``make_args_hash``)
* policy engine    - ``PolicyEngine`` over ``policy/rules.yaml``

For every scenario it compares the resulting tier (auto / approval / forbidden) with the
``expected_tier`` declared in the YAML. It then re-runs the suite with each control switched off
("ablation") to show which scenarios would stop being blocked.

What this is NOT: it does not run the LangGraph workflow, the Groq model, the full 12-step
gateway or any tool. It cannot measure latency, cost or LLM behaviour. Runtime behaviour
(idempotency, read-back, approval flow, webhooks, audit chain) is covered by ``pytest``.

Usage:  python -m evals.runner [--scenario EVAL-007] [--no-write]
Exit status is non-zero if any scenario resolves to a less restrictive tier than expected,
or to any tier different from the expected one.
"""
import argparse
import json
import sys
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, FrozenSet, List, Optional

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
SCENARIOS_DIR = Path(__file__).parent / "scenarios"
REPORTS_DIR = Path(__file__).parent / "reports"

for _p in (REPO_ROOT, REPO_ROOT / "backend", REPO_ROOT / "services" / "mocks"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from app.policy.engine import PolicyContext, PolicyEngine  # noqa: E402
from seed_data import ACCOUNTS, CONTACTS, INVOICES  # noqa: E402
from services.gateway.injection import scan_all_context  # noqa: E402
from services.gateway.tokens import make_args_hash  # noqa: E402

CONTROLS = ("identity", "injection", "provenance", "approval_hash", "legal_hold")
TIER_RANK = {"forbidden": 0, "approval": 1, "auto": 2}
# Tool probed when a scenario names no expected action: a low-risk write, so that only a control
# (not default-deny of an unknown tool) can make the outcome "forbidden".
PROBE_TOOL = "ticketing.add_internal_note"


@dataclass
class Outcome:
    scenario_id: str
    category: str
    description: str
    expected_tier: str
    actual_tier: Optional[str] = None
    decided_by: Optional[str] = None
    approver_role: Optional[str] = None
    skipped: bool = False
    skip_reason: Optional[str] = None
    passed: bool = False
    unsafe: bool = False          # resolved to a LESS restrictive tier than expected
    problems: List[str] = field(default_factory=list)


def load_scenarios() -> List[Dict[str, Any]]:
    scenarios = []
    for f in sorted(SCENARIOS_DIR.glob("*.yaml")):
        text = f.read_bytes().lstrip(b"\xef\xbb\xbf").decode("utf-8")
        scenarios.append(yaml.safe_load(text))
    return scenarios


def evaluate(scenario: Dict[str, Any], engine: PolicyEngine, disabled: FrozenSet[str] = frozenset()) -> Dict[str, Any]:
    """Resolve one scenario to a tier. ``disabled`` switches individual controls off."""
    seed = scenario.get("seed_state", {})
    ticket = scenario.get("ticket", {})
    account_id = seed.get("account_id", "")
    email = seed.get("requester_email", "")

    account = dict(ACCOUNTS.get(account_id, {}))
    contact = dict(CONTACTS.get(email, {}))
    if "legal_hold" in disabled:
        account["is_legal_hold"] = False

    tool = scenario.get("expected_action")
    tool = PROBE_TOOL if not tool or tool == "none" else tool
    args = dict(scenario.get("expected_arguments") or {})

    invoice_id = seed.get("target_foreign_invoice") or seed.get("invoice_id") or args.get("invoice_id")
    invoice = dict(INVOICES.get(invoice_id, {})) if invoice_id else None
    if invoice and invoice.get("invoice_date"):
        inv_date = datetime.fromisoformat(str(invoice["invoice_date"]).replace("Z", "+00:00"))
        if inv_date.tzinfo is None:
            inv_date = inv_date.replace(tzinfo=UTC)
        invoice["age_days"] = (datetime.now(UTC) - inv_date).days

    # --- controls ---------------------------------------------------------------------------
    flags: List[str] = []
    if "injection" not in disabled:
        notes = [seed["injected_note"]] if seed.get("injected_note") else []
        scan = scan_all_context(ticket.get("body", ""), ticket.get("subject", ""), notes)
        if scan.suspected:
            flags.append("injection_suspected")

    blockers: List[str] = []
    if "identity" not in disabled and not contact.get("is_authorized", False):
        blockers.append("identity")
    if "provenance" not in disabled and invoice_id and INVOICES.get(invoice_id, {}).get("account_id") != account_id:
        blockers.append("provenance")
    if "approval_hash" not in disabled and seed.get("mutated_amount_cents") is not None:
        executed = {**args, "amount_cents": seed["mutated_amount_cents"]}
        if make_args_hash(tool, executed) != make_args_hash(tool, args):
            blockers.append("approval_hash")

    decision = engine.evaluate(PolicyContext(
        tool=tool,
        args=args,
        account=account,
        requester={**contact, "is_authorized": contact.get("is_authorized", False)},
        invoice=invoice,
        flags=flags,
    ))

    if blockers:
        return {"tier": "forbidden", "decided_by": f"control:{blockers[0]}", "approver_role": None}
    return {"tier": decision.tier, "decided_by": f"policy:{decision.rule_id}", "approver_role": decision.approver_role}


def run_scenario(scenario: Dict[str, Any], engine: PolicyEngine) -> Outcome:
    out = Outcome(
        scenario_id=scenario["scenario_id"],
        category=scenario.get("category", "general"),
        description=scenario.get("description", ""),
        expected_tier=scenario.get("expected_tier", "unknown"),
    )
    if scenario.get("offline") is False:
        out.skipped = True
        out.skip_reason = scenario.get("offline_note", "not evaluable by the offline policy layer")
        return out

    res = evaluate(scenario, engine)
    out.actual_tier, out.decided_by, out.approver_role = res["tier"], res["decided_by"], res["approver_role"]
    out.passed = out.actual_tier == out.expected_tier
    if not out.passed:
        out.problems.append(f"expected tier {out.expected_tier}, got {out.actual_tier} ({out.decided_by})")
    expected_role = scenario.get("expected_approver_role")
    if out.passed and expected_role and out.approver_role != expected_role:
        out.passed = False
        out.problems.append(f"expected approver role {expected_role}, got {out.approver_role}")
    out.unsafe = TIER_RANK.get(out.actual_tier, -1) > TIER_RANK.get(out.expected_tier, 99)
    return out


def run_ablations(scenarios: List[Dict[str, Any]], engine: PolicyEngine) -> List[Dict[str, Any]]:
    """For each control: which scenarios become less restrictive than expected when it is removed."""
    results = []
    for control in CONTROLS:
        newly_unsafe = []
        for sc in scenarios:
            if sc.get("offline") is False:
                continue
            tier = evaluate(sc, engine, frozenset({control}))["tier"]
            if TIER_RANK[tier] > TIER_RANK.get(sc.get("expected_tier"), 99):
                newly_unsafe.append(sc["scenario_id"])
        results.append({"control_removed": control, "scenarios_that_become_unsafe": newly_unsafe})
    return results


def render_markdown(outcomes: List[Outcome], ablations: List[Dict[str, Any]], generated: str) -> str:
    evaluated = [o for o in outcomes if not o.skipped]
    passed = sum(o.passed for o in evaluated)
    lines = [
        "# Offline policy-layer scenario report",
        "",
        f"Generated {generated}. Scenarios in `evals/scenarios` replayed through the identity, injection, "
        "provenance, approval-hash and policy-engine checks (no LLM, no network). Tier decisions only: "
        "latency, cost and LLM behaviour are not measured here.",
        "",
        f"- Scenarios evaluated: {len(evaluated)} (skipped: {len(outcomes) - len(evaluated)})",
        f"- Resolved to the expected tier: {passed}/{len(evaluated)}",
        f"- Resolved to a less restrictive tier than expected: {sum(o.unsafe for o in evaluated)}",
        "",
        "## Scenarios",
        "",
        "| ID | Category | Expected | Actual | Decided by | Result |",
        "|---|---|---|---|---|---|",
    ]
    for o in outcomes:
        if o.skipped:
            lines.append(f"| {o.scenario_id} | {o.category} | {o.expected_tier} | - | - | skipped: {o.skip_reason} |")
        else:
            lines.append(
                f"| {o.scenario_id} | {o.category} | {o.expected_tier} | {o.actual_tier} | {o.decided_by} | "
                f"{'pass' if o.passed else 'FAIL: ' + '; '.join(o.problems)} |"
            )
    lines += ["", "## Ablation: control removed", "",
              "Scenarios that would resolve to a less restrictive tier than expected if the control were absent.", "",
              "| Control removed | Scenarios that become unsafe |", "|---|---|"]
    for a in ablations:
        ids = ", ".join(a["scenarios_that_become_unsafe"]) or "none"
        lines.append(f"| {a['control_removed']} | {ids} |")
    return "\n".join(lines) + "\n"


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Offline policy-layer scenario suite")
    parser.add_argument("--scenario", help="Run a single scenario by ID")
    parser.add_argument("--no-write", action="store_true", help="Do not write reports to evals/reports")
    args = parser.parse_args(argv)

    scenarios = load_scenarios()
    if args.scenario:
        scenarios = [s for s in scenarios if s["scenario_id"] == args.scenario]
    engine = PolicyEngine()

    outcomes = [run_scenario(s, engine) for s in scenarios]
    ablations = run_ablations(scenarios, engine)

    for o in outcomes:
        if o.skipped:
            print(f"[SKIP] {o.scenario_id:<9} {o.description}  ({o.skip_reason})")
        else:
            print(f"[{'PASS' if o.passed else 'FAIL'}] {o.scenario_id:<9} {o.expected_tier:>9} -> {o.actual_tier:<9} {o.decided_by}")
            for p in o.problems:
                print(f"         {p}")
    evaluated = [o for o in outcomes if not o.skipped]
    print(f"\n{sum(o.passed for o in evaluated)}/{len(evaluated)} evaluated scenarios resolved to the expected tier "
          f"({len(outcomes) - len(evaluated)} skipped); {sum(o.unsafe for o in evaluated)} resolved less restrictively than expected.")

    if not args.no_write:
        generated = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
        REPORTS_DIR.mkdir(exist_ok=True)
        (REPORTS_DIR / "policy_scenarios.json").write_text(
            json.dumps({"generated_at": generated, "outcomes": [asdict(o) for o in outcomes], "ablations": ablations}, indent=2),
            encoding="utf-8",
        )
        (REPORTS_DIR / "policy_scenarios.md").write_text(render_markdown(outcomes, ablations, generated), encoding="utf-8")

    return 0 if all(o.passed for o in evaluated) else 1


if __name__ == "__main__":
    sys.exit(main())
