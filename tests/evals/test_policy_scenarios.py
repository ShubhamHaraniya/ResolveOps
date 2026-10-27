"""The offline policy-layer scenario suite must stay green, and its ablation must be meaningful."""
from evals import runner


def test_all_evaluable_scenarios_resolve_to_expected_tier():
    engine = runner.PolicyEngine()
    outcomes = [runner.run_scenario(s, engine) for s in runner.load_scenarios()]
    evaluated = [o for o in outcomes if not o.skipped]
    assert len(evaluated) >= 25
    assert [o.scenario_id for o in evaluated if not o.passed] == []
    assert not any(o.unsafe for o in evaluated)


def test_removing_each_control_exposes_at_least_one_scenario():
    engine = runner.PolicyEngine()
    ablations = runner.run_ablations(runner.load_scenarios(), engine)
    assert {a["control_removed"] for a in ablations} == set(runner.CONTROLS)
    assert all(a["scenarios_that_become_unsafe"] for a in ablations)
