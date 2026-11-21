import pytest
from lifecycle_site import SiteSpec, costing_runner, edit_world, ready_site, run_setup, stored_final_runs, folder_of, success_transcript, validate_site

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
from willitharness.store import UNKNOWN_WORLD, Cell
from willitharness.world import HASH_LENGTH

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
    begin_run(folder_of(site), Job(CELL, 1, 1), UNKNOWN_WORLD)
    with pytest.raises(AssertionError) as raised:
        begin_run(folder_of(site), Job(CELL, 1, 1), UNKNOWN_WORLD)
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


@pytest.mark.parametrize(
    "spec, expected",
    [(ONE_REP, PlanState.COMPLETE), (BUDGET_FOR_ONE_RUN, PlanState.BUDGET_STOPPED), (TWO_REPS_AND_BUDGET, PlanState.RUNNING)],
    ids=["nothing-pending", "budget-blocks", "pending-and-budget-left"],
)
def test_T2_a_changed_world_blocks_starts_but_the_plan_still_ends_by_pending_work_and_budget(tmp_path, spec, expected):
    outcome = concluded_after_world_edit(tmp_path, spec)
    assert outcome is expected, f"got {outcome}, expected {expected}. Rule: T2 and W3, a changed world blocks starts and never the end of a plan. Fix: decide the end from the pending runs and the budget only."


def test_T62_a_run_stores_the_validated_world_hash_it_started_under(tmp_path):
    site = ready_site(tmp_path, SMALL)
    start_running(site)
    context = ledgered_context(site)
    first = claim_next_job(context)
    finish_job(context, first, success_transcript(0.01))
    edit_world(site)
    validate_site(site)
    claim_next_job(context)
    runs = sorted(stored_final_runs(site), key=lambda run: run.run_id)
    hashes = [run.world_hash for run in runs]
    assert len(hashes[0]) == HASH_LENGTH and len(hashes[1]) == HASH_LENGTH and hashes[0] != hashes[1], f"two worlds must give two hashes, got {hashes}. Rule: T62. Fix: pass the stored hash to begin_run."


def test_T62_runs_of_one_unedited_world_share_one_hash(tmp_path):
    site = ready_site(tmp_path, SMALL)
    start_running(site)
    context = ledgered_context(site)
    claim_next_job(context)
    claim_next_job(context)
    hashes = {run.world_hash for run in stored_final_runs(site)}
    assert len(hashes) == 1 and "" not in hashes, f"one world must give one non-empty hash, got {hashes}"
