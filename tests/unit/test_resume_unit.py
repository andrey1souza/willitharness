import math
from dataclasses import replace

import pytest
from lifecycle_site import SiteSpec, folder_of, stored_final_runs, costing_runner, edit_world, forget_validation, make_site, ready_site, run_setup, stop_at_budget, with_budget

from willitharness.lifecycle import (
    NOT_ENDED,
    LifecycleRefused,
    PlanState,
    ResumeRecord,
    abort_plan,
    execute_plan,
    move_to,
    read_reach,
    read_resume,
    read_state,
    resume_if_stopped,
    resume_plan,
    start_running,
    world_is_validated,
)
from willitharness.plan import plan_fingerprint
from willitharness.store import load_records, spent

SMALL = SiteSpec(arm_count=1, budget_usd=1.0, run_cap_usd=0.02, reps=2, max_retries=1)
TIGHT = SiteSpec(arm_count=1, budget_usd=0.05, run_cap_usd=0.02, reps=100, max_retries=0)


def stopped_site(tmp_path):
    return stop_at_budget(ready_site(tmp_path, TIGHT))


def site_in_state(tmp_path, state):
    site = stopped_site(tmp_path)
    if state is PlanState.COMPLETE:
        site = ready_site(tmp_path / "full", SMALL)
        execute_plan(run_setup(site), costing_runner(0.01))
    if state is PlanState.ANALYZED:
        move_to(folder_of(site), state)
    if state is PlanState.ABORTED:
        abort_plan(tmp_path, site.plan)
    assert read_state(folder_of(site)) is state, f"the plan must be {state}, got {read_state(folder_of(site))}"
    return site


def lifecycle_snapshot(site):
    return read_state(folder_of(site)), load_records(folder_of(site)), read_resume(folder_of(site))


def refusal_of(site, attempt):
    before = lifecycle_snapshot(site)
    with pytest.raises(LifecycleRefused) as raised:
        attempt(site)
    assert lifecycle_snapshot(site) == before, f"a refused resume changed the plan: {before} became {lifecycle_snapshot(site)}. Rule: a refusal leaves state, records and stored values unchanged."
    return str(raised.value)


def test_L10_the_first_run_stores_the_budget_and_the_fingerprint_without_the_budget(tmp_path):
    site = ready_site(tmp_path, SMALL)
    start_running(site)
    stored = read_resume(folder_of(site))
    assert stored == ResumeRecord(1.0, plan_fingerprint(site.plan), NOT_ENDED), f"got {stored}"
    start_running(with_budget(site, 5.0))
    assert read_resume(folder_of(site)) == stored, f"a second start rewrote the stored values: {read_resume(folder_of(site))}"


def test_L10_the_fingerprint_ignores_the_budget_and_follows_every_other_field(tmp_path):
    site = make_site(tmp_path, SMALL)
    assert plan_fingerprint(replace(site.plan, budget_usd=9.0)) == plan_fingerprint(site.plan), f"budget 9.0 changed the fingerprint of {site.plan.name}"
    assert plan_fingerprint(replace(site.plan, reps=3)) != plan_fingerprint(site.plan), f"reps 3 left the fingerprint of {site.plan.name} unchanged"
    assert plan_fingerprint(replace(site.plan, run_cap_usd=0.03)) != plan_fingerprint(site.plan), f"run cap 0.03 left the fingerprint of {site.plan.name} unchanged"


def test_L10_a_budget_stopped_plan_resumes_to_running_and_keeps_the_reachability_results(tmp_path):
    site = stopped_site(tmp_path)
    reach_before = read_reach(folder_of(site))
    resumed = resume_plan(with_budget(site, 0.10))
    assert resumed is PlanState.RUNNING and read_state(folder_of(site)) is PlanState.RUNNING, f"got {resumed} and {read_state(folder_of(site))}"
    assert read_reach(folder_of(site)) == reach_before and len(reach_before) == 1, f"reachability changed from {reach_before} to {read_reach(folder_of(site))}"
    assert math.isclose(read_resume(folder_of(site)).budget_usd, 0.10), f"the stored budget is {read_resume(folder_of(site)).budget_usd}, expected 0.1"


def test_L10_a_resumed_plan_keeps_its_records_and_runs_on_the_new_budget(tmp_path):
    site = stopped_site(tmp_path)
    first_runs = stored_final_runs(site)
    raised = with_budget(site, 0.10)
    resume_plan(raised)
    outcome = execute_plan(run_setup(raised), costing_runner(0.01))
    assert outcome is PlanState.BUDGET_STOPPED, f"the raised budget must stop again, got {outcome}"
    assert len(first_runs) == 4 and len(stored_final_runs(site)) == 9, f"expected 4 then 9 runs, got {len(first_runs)} then {len(stored_final_runs(site))}"
    assert math.isclose(spent(stored_final_runs(site)), 0.09), f"nine runs at 0.01 must cost 0.09, got {spent(stored_final_runs(site))} for {len(stored_final_runs(site))} runs. Rule: the raised budget allows runs up to 0.09 spent."


@pytest.mark.parametrize("state", [PlanState.COMPLETE, PlanState.ANALYZED, PlanState.ABORTED])
def test_L10_a_plan_that_is_not_budget_stopped_cannot_resume(tmp_path, state):
    site = with_budget(site_in_state(tmp_path, state), 5.0)
    message = refusal_of(site, resume_plan)
    assert f"plan is {state}; only a BudgetStopped plan resumes" in message, f"got {message!r}"
    assert "Rule: L10" in message and "Fix:" in message, f"the message needs a Rule and a Fix, got {message!r}"


def test_L10_a_changed_world_blocks_the_resume_and_asks_for_a_new_validation(tmp_path):
    site = stopped_site(tmp_path)
    edit_world(site)
    message = refusal_of(with_budget(site, 0.10), resume_plan)
    assert "must be validated again" in message, f"got {message!r}"
    assert "Rule: L10" in message and "Fix:" in message, f"the message needs a Rule and a Fix, got {message!r}"


def test_L10_a_world_that_was_never_validated_blocks_the_resume(tmp_path):
    site = stopped_site(tmp_path)
    forget_validation(site)
    message = refusal_of(with_budget(site, 0.10), resume_plan)
    assert "must be validated again" in message, f"got {message!r}"
    assert not world_is_validated(site), f"the world {site.world_dir} still counts as validated after its record was removed"


def test_A_FP_a_plan_that_differs_in_more_than_the_budget_cannot_resume(tmp_path):
    site = stopped_site(tmp_path)
    changed = with_budget(replace(site, plan=replace(site.plan, reps=site.plan.reps + 1)), 0.10)
    message = refusal_of(changed, resume_plan)
    assert "A-FP" in message and "only the budget" in message, f"got {message!r}"
    assert "Fix:" in message, f"the message needs a Fix, got {message!r}"


@pytest.mark.parametrize("budget", [0.05, 0.04])
def test_L11_a_budget_that_is_not_higher_cannot_resume(tmp_path, budget):
    site = stopped_site(tmp_path)
    message = refusal_of(with_budget(site, budget), resume_plan)
    assert "Rule: L11" in message and "Fix:" in message, f"got {message!r}"
    assert math.isclose(read_resume(folder_of(site)).budget_usd, 0.05), f"the stored budget changed to {read_resume(folder_of(site)).budget_usd}"


def test_L12_the_ended_marker_follows_the_plan_and_resume_resets_it(tmp_path):
    site = stopped_site(tmp_path)
    assert read_resume(folder_of(site)).ended_by == "BudgetStopped", f"got {read_resume(folder_of(site))}"
    resume_plan(with_budget(site, 0.10))
    assert read_state(folder_of(site)) is PlanState.RUNNING and read_resume(folder_of(site)).ended_by == NOT_ENDED, f"got {read_state(folder_of(site))} and {read_resume(folder_of(site))}"


def test_L12_a_plan_that_runs_to_the_end_is_marked_with_how_it_ended(tmp_path):
    site = ready_site(tmp_path, SMALL)
    execute_plan(run_setup(site), costing_runner(0.01))
    assert read_resume(folder_of(site)).ended_by == "Complete", f"got {read_resume(folder_of(site))}"
    assert read_state(folder_of(site)) is PlanState.COMPLETE, f"got {read_state(folder_of(site))}"


def test_L10_run_on_a_complete_plan_says_there_is_nothing_to_resume(tmp_path):
    site = site_in_state(tmp_path, PlanState.COMPLETE)
    message = refusal_of(site, resume_if_stopped)
    assert "nothing to resume" in message, f"got {message!r}"
    assert read_state(folder_of(site)) is PlanState.COMPLETE, f"got {read_state(folder_of(site))}"

