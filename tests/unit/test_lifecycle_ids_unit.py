import pytest
from lifecycle_site import SiteSpec, costing_runner, edit_world, ready_site, run_setup, stored_final_runs, folder_of, success_transcript

from willitharness.lifecycle import (
    Job,
    PlanState,
    RunContext,
    begin_run,
    claim_next_job,
    conclude,
    finish_job,
    ledger_from_records,
    start_running,
)
from willitharness.store import Cell

SMALL = SiteSpec(arm_count=1, budget_usd=1.0, run_cap_usd=0.02, reps=2, max_retries=1)
CELL = Cell("A", "stop-server")
ONE_REP = SiteSpec(arm_count=1, budget_usd=1.0, run_cap_usd=0.02, reps=1, max_retries=0)
BUDGET_FOR_ONE_RUN = SiteSpec(arm_count=1, budget_usd=0.02, run_cap_usd=0.02, reps=2, max_retries=0)
TWO_REPS_AND_BUDGET = SiteSpec(arm_count=1, budget_usd=1.0, run_cap_usd=0.02, reps=2, max_retries=0)


def ledgered_context(site):
    ledger = ledger_from_records(site.plan, stored_final_runs(site))
    return RunContext(run_setup(site), costing_runner(0.01), ledger)


def concluded_after_world_edit(tmp_path, spec):
    site = ready_site(tmp_path, spec)
    start_running(site)
    context = ledgered_context(site)
    finish_job(context, claim_next_job(context), success_transcript(0.01))
    edit_world(site)
    return conclude(context)


def test_L3_a_run_id_is_never_started_twice(tmp_path):
    site = ready_site(tmp_path, SMALL)
    start_running(site)
    begin_run(folder_of(site), Job(CELL, 1, 1))
    with pytest.raises(AssertionError) as raised:
        begin_run(folder_of(site), Job(CELL, 1, 1))
    assert "run id A/stop-server/1#1 is already stored" in str(raised.value), f"got {raised.value}"
    assert "Fix: claim the next attempt with claim_next_job" in str(raised.value), f"the message must name the fix, got {raised.value}"
    assert [run.run_id for run in stored_final_runs(site)] == ["A/stop-server/1#1"], "the refused start must store nothing"


def test_L3_two_claims_in_one_cell_get_two_run_ids(tmp_path):
    site = ready_site(tmp_path, SMALL)
    start_running(site)
    context = ledgered_context(site)
    first = claim_next_job(context)
    second = claim_next_job(context)
    assert (first, second) == (Job(CELL, 1, 1), Job(CELL, 2, 2)), f"each claim needs its own rep and attempt, got {first} and {second}"
    assert sorted(run.run_id for run in stored_final_runs(site)) == ["A/stop-server/1#1", "A/stop-server/2#2"], "two Started runs, two ids"


def test_T2_a_plan_with_nothing_pending_is_complete_even_when_the_world_changed(tmp_path):
    outcome = concluded_after_world_edit(tmp_path, ONE_REP)
    assert outcome is PlanState.COMPLETE, f"got {outcome}. Rule: T2, a world change blocks starts, not the end of a plan with no pending run. Fix: decide Complete from the pending runs only."


def test_T2_a_plan_the_budget_blocks_is_budget_stopped_even_when_the_world_changed(tmp_path):
    outcome = concluded_after_world_edit(tmp_path, BUDGET_FOR_ONE_RUN)
    assert outcome is PlanState.BUDGET_STOPPED, f"got {outcome}. Rule: T2, the budget decides BudgetStopped, not the world. Fix: test the budget in conclude."


def test_T2_a_plan_with_pending_runs_and_budget_left_stays_running_while_the_world_is_changed(tmp_path):
    outcome = concluded_after_world_edit(tmp_path, TWO_REPS_AND_BUDGET)
    assert outcome is PlanState.RUNNING, f"got {outcome}. Rule: W3, a changed world blocks starts and the plan waits for a new validation. Fix: keep Running while budget is left."
