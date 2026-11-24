from dataclasses import replace

from lifecycle_site import SiteSpec, make_site, start_refusal_of, tree_snapshot, validated_and_reached

from willitharness.lifecycle import PlanState, lifecycle_dir, read_state, start_running

SMALL = SiteSpec(arm_count=2, budget_usd=1.0, run_cap_usd=0.05, reps=1, max_retries=0)


def with_no_rule(site):
    return replace(site, plan=replace(site.plan, rule=None))


def test_T81_a_plan_with_no_rule_is_refused_with_a_rule_and_a_fix(tmp_path):
    message = start_refusal_of(with_no_rule(validated_and_reached(make_site(tmp_path, SMALL))))
    assert "plan demo has no rule." in message and "Rule: L1" in message and message.endswith("to the plan."), f"got {message!r}"
    assert "Fix: add a rule object with id, file, section, target_outcome and detector" in message, f"got {message!r}"


def test_T81_a_plan_with_a_rule_starts_the_run(tmp_path):
    site = validated_and_reached(make_site(tmp_path, SMALL))
    observed = start_running(site)
    assert observed is PlanState.RUNNING, f"a plan with a rule must start, got {observed} for plan {site.plan.name}"


def test_T81_a_restart_of_a_running_plan_is_refused_when_the_rule_is_gone(tmp_path):
    site = validated_and_reached(make_site(tmp_path, SMALL))
    start_running(site)
    message = start_refusal_of(with_no_rule(site))
    assert "has no rule" in message, f"got {message!r}"


def test_T81_a_refused_run_changes_no_file_and_no_state(tmp_path):
    site = with_no_rule(validated_and_reached(make_site(tmp_path, SMALL)))
    folder = lifecycle_dir(site.root, site.plan)
    state_before = read_state(folder)
    files_before = tree_snapshot(site.root)
    start_refusal_of(site)
    assert tree_snapshot(site.root) == files_before, f"a refused run changed files under {site.root}. Rule: L1, a refusal leaves records and stored values unchanged."
    assert read_state(folder) is state_before is PlanState.REACHABILITY_CHECKED, f"a refused run moved the state from {state_before} to {read_state(folder)}"
