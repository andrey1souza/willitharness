from dataclasses import replace

import pytest
from lifecycle_site import SiteSpec, costing_runner, edit_world, ready_site, run_setup, stored_final_runs, folder_of, success_transcript, validate_site

from willitharness.budget import ledger_from_records
from willitharness.lifecycle import (
    Job,
    PlanState,
    RunContext,
    begin_run,
    claim_next_job,
    conclude,
    finish_job,
    read_resume,
    start_running,
)
from willitharness.world_facts import world_facts
from willitharness.store import UNKNOWN_MODEL, UNKNOWN_WORLD, Cell, record_from_line
from willitharness.world import HASH_LENGTH, claimed_world_hash, stored_hash, world_hash

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
    begin_run(folder_of(site), Job(CELL, 1, 1), UNKNOWN_WORLD, UNKNOWN_MODEL)
    with pytest.raises(AssertionError) as raised:
        begin_run(folder_of(site), Job(CELL, 1, 1), UNKNOWN_WORLD, UNKNOWN_MODEL)
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


def test_T65_a_claim_records_the_hash_of_the_files_now_not_the_validated_hash(tmp_path):
    site = ready_site(tmp_path, SMALL)
    edit_world(site)
    claimed = claimed_world_hash(site.world_dir)
    assert claimed == world_hash(site.world_dir) and claimed != stored_hash(site.root, site.world_dir), f"got {claimed}. Rule: T65. Fix: hash the world files at the claim."


def test_T65_the_world_facts_name_the_validated_hash_a_run_left(tmp_path):
    site = ready_site(tmp_path, SMALL)
    start_running(site)
    edit_world(site)
    begin_run(folder_of(site), Job(CELL, 1, 1), claimed_world_hash(site.world_dir), UNKNOWN_MODEL)
    facts = world_facts(site.root, site.plan)
    left = stored_final_runs(site)[0].world_hash
    assert facts.validated_hash == stored_hash(site.root, site.world_dir) and left != facts.validated_hash, f"got {facts} and a run in {left}"


@pytest.mark.parametrize("edited, expected", [(True, True), (False, False)], ids=["edited", "unedited"])
def test_T65_conclude_records_whether_the_plan_ended_in_a_changed_world(tmp_path, edited, expected):
    site = ready_site(tmp_path, ONE_REP)
    start_running(site)
    context = ledgered_context(site)
    finish_job(context, claim_next_job(context), success_transcript(0.01))
    if edited:
        edit_world(site)
    ended = conclude(context)
    assert ended is PlanState.COMPLETE, f"one rep done, nothing pending, got {ended}"
    assert read_resume(folder_of(site)).ended_in_changed_world is expected, f"got {read_resume(folder_of(site))}. Rule: T65, a plan that ended in a changed world says so."
    assert world_facts(site.root, site.plan).ended_in_changed_world is expected, f"world_facts must carry the stored fact {expected}, got {world_facts(site.root, site.plan)}"


def test_T73_a_claim_stores_the_model_of_the_run_setup(tmp_path):
    site = ready_site(tmp_path, SMALL)
    start_running(site)
    context = ledgered_context(site)
    claim_next_job(RunContext(replace(context.setup, model="sonnet"), context.runner, context.ledger))
    models = {run.model for run in stored_final_runs(site)}
    assert models == {"sonnet"}, f"got {models}. Rule: T73, a claim stores the model. Fix: pass setup.model to begin_run."


def test_T73_a_record_written_before_T73_loads_with_no_model():
    old_line = '{"arm": "B", "attempt": 1, "cost_usd": 0.0, "denials": 0, "outcome": {}, "rep": 1, "run_id": "B/t/1#1", "state": "Started", "task": "t", "usable": {}, "world_hash": "aa"}'
    assert record_from_line(old_line).model == UNKNOWN_MODEL, "an old line has no model and still loads"
