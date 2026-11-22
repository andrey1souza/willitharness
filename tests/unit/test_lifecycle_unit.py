import math
import threading
from dataclasses import replace

import pytest
from lifecycle_site import SiteSpec, folder_of, stored_final_runs, costing_runner, edit_world, make_site, ready_site, reach_every_arm, run_setup, success_transcript, validate_site

from willitharness.lifecycle import (
    TIMED_OUT,
    Job,
    LifecycleRefused,
    PlanState,
    RunContext,
    abort_plan,
    analyze_gate,
    begin_run,
    claim_next_job,
    finish_job,
    finished,
    lifecycle_dir,
    ledger_from_records,
    move_to,
    read_reach,
    read_state,
    record_reachability,
    refresh_state,
    execute_plan,
    start_running,
    write_state,
)
from willitharness.store import UNKNOWN_WORLD, Cell, Record, RunState, append_record, cell_counters, in_flight_runs, latest_by_run, load_records, spent
from willitharness.vocabulary import Reach

SMALL = SiteSpec(arm_count=1, budget_usd=1.0, run_cap_usd=0.02, reps=2, max_retries=1)
FOUR_ARMS = SiteSpec(arm_count=4, budget_usd=1.0, run_cap_usd=0.02, reps=1, max_retries=0)
TIGHT = SiteSpec(arm_count=1, budget_usd=0.05, run_cap_usd=0.02, reps=100, max_retries=0)
CELL = Cell("A", "stop-server")
ALL_STATES = tuple(PlanState)
LEGAL_PAIRS = {
    ("Drafted", "WorldValidated"),
    ("Drafted", "Aborted"),
    ("WorldValidated", "ReachabilityChecked"),
    ("WorldValidated", "Drafted"),
    ("WorldValidated", "Aborted"),
    ("ReachabilityChecked", "Running"),
    ("ReachabilityChecked", "Drafted"),
    ("ReachabilityChecked", "Aborted"),
    ("Running", "Complete"),
    ("Running", "BudgetStopped"),
    ("Running", "Aborted"),
    ("Complete", "Analyzed"),
    ("Complete", "Aborted"),
    ("BudgetStopped", "Analyzed"),
    ("BudgetStopped", "Aborted"),
    ("BudgetStopped", "Running"),
    ("Analyzed", "Reported"),
}


def stored_run(index, state, cost):
    return Record(f"A/stop-server/{index}#{index}", "A", "stop-server", index, index, state, {"completed": True}, cost)


def context_for(site, runner):
    ledger = ledger_from_records(site.plan, stored_final_runs(site))
    return RunContext(run_setup(site), runner, ledger)


@pytest.mark.parametrize("source", ALL_STATES)
@pytest.mark.parametrize("target", ALL_STATES)
def test_L1_a_move_between_two_states_is_legal_only_when_the_contract_allows_it(tmp_path, source, target):
    write_state(tmp_path, source)
    legal = (source.value, target.value) in LEGAL_PAIRS or source is target
    if legal:
        assert move_to(tmp_path, target) is target, f"{source} to {target} must be legal"
    else:
        with pytest.raises(LifecycleRefused):
            move_to(tmp_path, target)
    assert read_state(tmp_path) is (target if legal else source), f"after {source} to {target} the state is {read_state(tmp_path)}"


def test_a_plan_with_no_state_file_is_drafted(tmp_path):
    site = make_site(tmp_path, SMALL)
    assert read_state(folder_of(site)) is PlanState.DRAFTED, f"got {read_state(folder_of(site))}"


def test_the_state_is_stored_under_the_plan_name_next_to_the_run_store(tmp_path):
    site = ready_site(tmp_path, SMALL)
    assert (tmp_path / ".willitharness" / "demo" / "state.json").read_text() == '{"state": "ReachabilityChecked"}', "state.json must hold the state"
    assert (tmp_path / ".willitharness" / "demo" / "reach.json").is_file(), "reach.json must sit next to the state file"
    assert folder_of(site) == (tmp_path / ".willitharness" / "demo").resolve(), f"got {folder_of(site)}"


def test_L1_a_validated_world_without_reachability_is_world_validated(tmp_path):
    site = make_site(tmp_path, FOUR_ARMS)
    validate_site(site)
    assert refresh_state(site) is PlanState.WORLD_VALIDATED, f"got {refresh_state(site)}"


def test_L1_an_unvalidated_world_stays_drafted_even_with_every_reachability_result(tmp_path):
    site = make_site(tmp_path, FOUR_ARMS)
    observed = reach_every_arm(site, Reach.LOADED)
    assert observed is PlanState.DRAFTED, f"reachability alone cannot lift a plan out of Drafted; got {observed}, expected PlanState.DRAFTED"
    assert read_state(folder_of(site)) is PlanState.DRAFTED, f"got {read_state(folder_of(site))}"


def test_L1_reachability_for_every_arm_makes_the_plan_reachability_checked(tmp_path):
    site = make_site(tmp_path, FOUR_ARMS)
    validate_site(site)
    states = [record_reachability(site, arm.label, Reach.LOADED) for arm in site.plan.arms]
    assert [state.value for state in states] == ["WorldValidated", "WorldValidated", "WorldValidated", "ReachabilityChecked"], f"got {states}"


def test_L1_a_reachability_result_of_unknown_counts_as_recorded(tmp_path):
    site = make_site(tmp_path, FOUR_ARMS)
    validate_site(site)
    observed = reach_every_arm(site, Reach.UNKNOWN)
    assert observed is PlanState.REACHABILITY_CHECKED, f"Unknown must count as recorded; got {observed}, expected PlanState.REACHABILITY_CHECKED"
    observed = start_running(site)
    assert observed is PlanState.RUNNING, f"a plan whose arms are all Unknown can start; got {observed}, expected PlanState.RUNNING"
    assert {arm: reach.value for arm, reach in read_reach(folder_of(site)).items()} == {"A": "Unknown", "B": "Unknown", "C": "Unknown", "D": "Unknown"}, "the results are kept"


def test_L1_reachability_for_an_unknown_arm_is_refused(tmp_path):
    site = make_site(tmp_path, SMALL)
    with pytest.raises(AssertionError) as raised:
        record_reachability(site, "Z", Reach.LOADED)
    assert "Z is not an arm" in str(raised.value), f"got {raised.value}"


def test_L1_the_run_refuses_to_start_naming_the_arm_with_no_reachability_result(tmp_path):
    site = make_site(tmp_path, FOUR_ARMS)
    validate_site(site)
    for label in "ABD":
        record_reachability(site, label, Reach.LOADED)
    with pytest.raises(LifecycleRefused) as raised:
        start_running(site)
    assert "arm C" in str(raised.value), f"the refusal must name arm C, got {raised.value}"
    assert read_state(folder_of(site)) is PlanState.WORLD_VALIDATED, f"got {read_state(folder_of(site))}"


def test_L1_the_run_refuses_to_start_on_a_world_never_validated(tmp_path):
    site = make_site(tmp_path, SMALL)
    with pytest.raises(LifecycleRefused) as raised:
        start_running(site)
    assert str(raised.value).startswith("world not validated; run: willitharness world check. Rule:"), f"got {raised.value}"
    assert stored_final_runs(site) == (), "no run may exist"


def test_W3_the_run_refuses_to_start_on_a_changed_world(tmp_path):
    site = ready_site(tmp_path, SMALL)
    edit_world(site)
    with pytest.raises(LifecycleRefused) as raised:
        start_running(site)
    assert str(raised.value).startswith("world changed since validation; run: willitharness world check. Rule:"), f"got {raised.value}"
    assert stored_final_runs(site) == (), "no run may exist"


@pytest.mark.parametrize("reached", [False, True])
def test_W3_a_world_change_returns_the_plan_to_drafted_and_keeps_reachability(tmp_path, reached):
    site = make_site(tmp_path, FOUR_ARMS)
    validate_site(site)
    if reached:
        reach_every_arm(site, Reach.MASKED)
    else:
        record_reachability(site, "A", Reach.MASKED)
    edit_world(site)
    assert refresh_state(site) is PlanState.DRAFTED, f"got {refresh_state(site)}"
    observed = read_reach(folder_of(site))["A"]
    assert observed is Reach.MASKED, f"reachability results are kept; got {observed}, expected Reach.MASKED"


def test_W3_validating_the_changed_world_again_restores_the_plan(tmp_path):
    site = ready_site(tmp_path, SMALL)
    edit_world(site)
    refresh_state(site)
    validate_site(site)
    observed = refresh_state(site)
    assert observed is PlanState.REACHABILITY_CHECKED, f"the kept reachability results make the plan ready again; got {observed}, expected PlanState.REACHABILITY_CHECKED"
    observed = start_running(site)
    assert observed is PlanState.RUNNING, f"the plan can start again; got {observed}, expected PlanState.RUNNING"


def test_W3_a_running_plan_stays_running_with_starts_blocked(tmp_path):
    site = ready_site(tmp_path, SMALL)
    start_running(site)
    edit_world(site)
    assert refresh_state(site) is PlanState.RUNNING, f"got {refresh_state(site)}"
    context = context_for(site, costing_runner(0.01))
    observed = claim_next_job(context)
    assert observed is None, f"no run may start on a changed world; got {observed}, expected None"
    assert stored_final_runs(site) == (), "no run may be stored"
    with pytest.raises(LifecycleRefused):
        execute_plan(run_setup(site), costing_runner(0.01))
    observed = read_state(folder_of(site))
    assert observed is PlanState.RUNNING, f"the plan stays Running; got {observed}, expected PlanState.RUNNING"


@pytest.mark.parametrize("finished_state", [PlanState.COMPLETE, PlanState.BUDGET_STOPPED, PlanState.ABORTED])
def test_a_finished_plan_cannot_start_again(tmp_path, finished_state):
    site = ready_site(tmp_path, SMALL)
    start_running(site)
    move_to(folder_of(site), finished_state)
    with pytest.raises(LifecycleRefused) as raised:
        start_running(site)
    assert f"plan is {finished_state}" in str(raised.value), f"got {raised.value}"


def test_L1_a_start_is_refused_unless_the_plan_is_running_and_stores_nothing(tmp_path):
    site = make_site(tmp_path, SMALL)
    validate_site(site)
    refresh_state(site)
    with pytest.raises(LifecycleRefused) as raised:
        begin_run(folder_of(site), Job(CELL, 1, 1), UNKNOWN_WORLD)
    assert "plan is WorldValidated" in str(raised.value), f"got {raised.value}"
    assert stored_final_runs(site) == (), "no run record may exist"


def test_L1_a_start_in_running_stores_a_started_record(tmp_path):
    site = ready_site(tmp_path, SMALL)
    start_running(site)
    begin_run(folder_of(site), Job(CELL, 1, 1), UNKNOWN_WORLD)
    assert [(run.run_id, run.state.value) for run in stored_final_runs(site)] == [("A/stop-server/1#1", "Started")], "one Started run"


def test_L2_the_budget_stops_the_plan_after_exactly_four_runs(tmp_path):
    site = ready_site(tmp_path, TIGHT)
    outcome = execute_plan(run_setup(site), costing_runner(0.01))
    records = stored_final_runs(site)
    assert outcome is PlanState.BUDGET_STOPPED, f"got {outcome}"
    assert len(records) == 4, f"exactly 4 runs start, got {len(records)}"
    assert math.isclose(spent(records), 0.04), f"spend is 0.04, got {spent(records)}"
    observed = read_state(folder_of(site))
    assert observed is PlanState.BUDGET_STOPPED, f"the state is persisted; got {observed}, expected PlanState.BUDGET_STOPPED"


def test_T2_a_plan_with_room_for_every_run_ends_complete_with_every_cell_full(tmp_path):
    site = ready_site(tmp_path, replace(FOUR_ARMS, reps=3))
    outcome = execute_plan(run_setup(site), costing_runner(0.01))
    counters = cell_counters(stored_final_runs(site))
    assert outcome is PlanState.COMPLETE, f"got {outcome}"
    assert {cell.arm: item.usable for cell, item in counters.items()} == {"A": 3, "B": 3, "C": 3, "D": 3}, f"got {counters}"
    left_in_flight = in_flight_runs(stored_final_runs(site))
    assert not left_in_flight, f"T1: every run is recorded, got in flight {left_in_flight}"


def test_L9_retries_that_run_out_still_end_complete_with_attempts_at_the_cap(tmp_path):
    site = ready_site(tmp_path, SiteSpec(1, 1.0, 0.02, 1, 2))
    outcome = execute_plan(run_setup(site), lambda cell, rep, attempt: finished(()))
    counters = cell_counters(stored_final_runs(site))[CELL]
    assert outcome is PlanState.COMPLETE, f"got {outcome}"
    assert (counters.usable, counters.attempts) == (0, 3), f"1 rep and 2 retries allow 3 attempts and no usable run, got {counters}"


def test_L4_a_failed_run_does_not_use_up_a_rep(tmp_path):
    site = ready_site(tmp_path, SiteSpec(1, 1.0, 0.02, 2, 1))
    answers = {1: finished(()), 2: success_transcript(0.01), 3: success_transcript(0.01)}
    outcome = execute_plan(run_setup(site), lambda cell, rep, attempt: answers[attempt])
    counters = cell_counters(stored_final_runs(site))[CELL]
    assert outcome is PlanState.COMPLETE, f"got {outcome}"
    assert (counters.usable, counters.attempts) == (2, 3), f"the failed first run is retried, got {counters}"


def test_T1_a_timed_out_run_is_unusable_and_charges_the_full_run_cap(tmp_path):
    site = ready_site(tmp_path, SiteSpec(1, 1.0, 0.02, 1, 0))
    release = threading.Event()
    setup = replace(run_setup(site), timeout_seconds=0.05)
    outcome = execute_plan(setup, lambda cell, rep, attempt: release.wait() and TIMED_OUT)
    release.set()
    records = stored_final_runs(site)
    assert outcome is PlanState.COMPLETE, f"got {outcome}"
    assert [(run.state.value, run.cost_usd) for run in records] == [("RecordedUnusable", 0.02)], f"got {records}"


def test_T1_a_runner_that_reports_a_timeout_is_recorded_unusable_at_the_full_run_cap(tmp_path):
    site = ready_site(tmp_path, SiteSpec(1, 1.0, 0.02, 1, 0))
    execute_plan(run_setup(site), lambda cell, rep, attempt: TIMED_OUT)
    assert [(run.state.value, run.cost_usd) for run in stored_final_runs(site)] == [("RecordedUnusable", 0.02)], "the flag charges RUN_CAP"


def test_L2_a_cost_above_the_cap_is_recorded_unusable_at_the_cap(tmp_path):
    site = ready_site(tmp_path, SiteSpec(1, 1.0, 0.02, 1, 0))
    execute_plan(run_setup(site), costing_runner(0.05))
    assert [(run.state.value, run.cost_usd) for run in stored_final_runs(site)] == [("RecordedUnusable", 0.02)], "an over-cap run is unusable at RUN_CAP"


def test_L2_a_cost_inside_the_cap_is_recorded_usable_at_its_real_cost(tmp_path):
    site = ready_site(tmp_path, SiteSpec(1, 1.0, 0.02, 1, 0))
    execute_plan(run_setup(site), costing_runner(0.015))
    assert [(run.state.value, run.cost_usd) for run in stored_final_runs(site)] == [("RecordedUsable", 0.015)], "the real cost replaces the reservation"


def test_L2_four_runners_work_at_the_same_time_and_no_more(tmp_path):
    site = ready_site(tmp_path, SiteSpec(1, 1.0, 0.02, 8, 0))
    gate = threading.Barrier(4, timeout=2)
    lock = threading.Lock()
    active = {"now": 0, "most": 0}

    def runner(cell, rep, attempt):
        with lock:
            active["now"] += 1
            active["most"] = max(active["most"], active["now"])
        if attempt <= 4:
            gate.wait()
        with lock:
            active["now"] -= 1
        return success_transcript(0.01)

    execute_plan(run_setup(site), runner)
    assert active["most"] == 4, f"exactly 4 runners work in parallel, got {active}"
    assert len(stored_final_runs(site)) == 8, "every planned run happened"


def test_L2_a_resumed_plan_reserves_run_cap_for_each_run_still_in_flight(tmp_path):
    site = ready_site(tmp_path, TIGHT)
    start_running(site)
    append_record(folder_of(site), stored_run(1, RunState.STARTED, 0.0))
    append_record(folder_of(site), stored_run(2, RunState.RECORDED_UNUSABLE, 0.02))
    outcome = execute_plan(run_setup(site), costing_runner(0.01))
    assert outcome is PlanState.BUDGET_STOPPED, f"got {outcome}"
    assert len(stored_final_runs(site)) == 2, "spent 0.02 plus reserved 0.02 plus RUN_CAP 0.02 is above 0.05, so no run starts"


def test_L2_a_resumed_plan_counts_the_cost_of_unusable_runs_as_spent(tmp_path):
    site = ready_site(tmp_path, TIGHT)
    start_running(site)
    append_record(folder_of(site), stored_run(1, RunState.RECORDED_UNUSABLE, 0.02))
    append_record(folder_of(site), stored_run(2, RunState.RECORDED_UNUSABLE, 0.02))
    execute_plan(run_setup(site), costing_runner(0.01))
    assert len(stored_final_runs(site)) == 2, "spent 0.04 leaves no room for another RUN_CAP of 0.02 in 0.05"


def test_L2_a_resumed_plan_counts_the_cost_of_usable_runs_as_spent(tmp_path):
    site = ready_site(tmp_path, TIGHT)
    start_running(site)
    append_record(folder_of(site), stored_run(1, RunState.RECORDED_USABLE, 0.02))
    append_record(folder_of(site), stored_run(2, RunState.RECORDED_USABLE, 0.02))
    execute_plan(run_setup(site), costing_runner(0.01))
    assert len(stored_final_runs(site)) == 2, "spent 0.04 leaves no room for another RUN_CAP of 0.02 in 0.05"


def test_L2_ledger_from_records_holds_spent_and_reserved_from_the_store(tmp_path):
    site = ready_site(tmp_path, SMALL)
    records = (stored_run(1, RunState.RECORDED_USABLE, 0.01), stored_run(2, RunState.STARTED, 0.0), stored_run(3, RunState.STARTED, 0.0))
    ledger = ledger_from_records(site.plan, records)
    assert (str(ledger.spent), str(ledger.reserved)) == ("0.01", "0.04"), (
        f"got spent {ledger.spent}, reserved {ledger.reserved}. Rule: L2, spent comes from recorded runs and reserved is RUN_CAP per Started run. Fix: rebuild both from the store."
    )


def test_T2a_abort_records_every_run_in_flight_as_unusable_and_charges_run_cap_for_each(tmp_path):
    site = ready_site(tmp_path, SMALL)
    start_running(site)
    append_record(folder_of(site), stored_run(1, RunState.RECORDED_USABLE, 0.10))
    for index in (2, 3, 4):
        append_record(folder_of(site), stored_run(index, RunState.STARTED, 0.0))
    outcome = abort_plan(tmp_path, site.plan)
    records = stored_final_runs(site)
    assert outcome is PlanState.ABORTED, f"got {outcome}"
    assert math.isclose(spent(records), 0.16), f"0.10 plus 3 times 0.02 is 0.16, got {spent(records)}"
    assert sorted(run.state.value for run in records if math.isclose(run.cost_usd, 0.02)) == ["RecordedUnusable"] * 3, f"got {records}"
    observed = read_state(folder_of(site))
    assert observed is PlanState.ABORTED, f"the state is persisted; got {observed}, expected PlanState.ABORTED"


def test_T2a_an_abort_during_a_run_ends_the_plan_aborted_with_nothing_in_flight(tmp_path):
    site = ready_site(tmp_path, SiteSpec(1, 1.0, 0.02, 40, 0))
    entered = threading.Event()
    release = threading.Event()

    def runner(cell, rep, attempt):
        entered.set()
        release.wait()
        return success_transcript(0.01)

    outcomes = []
    driver = threading.Thread(target=lambda: outcomes.append(execute_plan(run_setup(site), runner)))
    driver.start()
    entered.wait(timeout=2)
    abort_plan(tmp_path, site.plan)
    release.set()
    driver.join(timeout=10)
    records = stored_final_runs(site)
    assert outcomes == [PlanState.ABORTED], f"got {outcomes}"
    assert not in_flight_runs(records), f"runs still in flight: {in_flight_runs(records)}"
    assert all(run.state is RunState.RECORDED_UNUSABLE for run in records) and 1 <= len(records) <= 4, f"every run aborted unusable, got {records}"


def test_abort_after_the_plan_is_analyzed_is_refused_and_the_state_stays(tmp_path):
    site = ready_site(tmp_path, SMALL)
    start_running(site)
    for step in (PlanState.COMPLETE, PlanState.ANALYZED):
        move_to(folder_of(site), step)
    with pytest.raises(LifecycleRefused) as raised:
        abort_plan(tmp_path, site.plan)
    assert str(raised.value).startswith("plan already analyzed; abort is not possible. Rule:"), f"got {raised.value}"
    observed = read_state(folder_of(site))
    assert observed is PlanState.ANALYZED, f"an analyzed plan stays analyzed; got {observed}, expected PlanState.ANALYZED"


@pytest.mark.parametrize("path", [(), (PlanState.WORLD_VALIDATED,), (PlanState.WORLD_VALIDATED, PlanState.REACHABILITY_CHECKED), (PlanState.WORLD_VALIDATED, PlanState.REACHABILITY_CHECKED, PlanState.RUNNING)])
def test_abort_is_possible_from_every_state_before_analysis(tmp_path, path):
    site = make_site(tmp_path, SMALL)
    for step in path:
        move_to(folder_of(site), step)
    observed = abort_plan(tmp_path, site.plan)
    assert observed is PlanState.ABORTED, f"abort must work before analysis; got {observed}, expected PlanState.ABORTED"
    assert read_state(folder_of(site)) is PlanState.ABORTED, f"got {read_state(folder_of(site))}"


def test_L5_analyze_on_an_aborted_plan_says_no_verdict(tmp_path):
    site = make_site(tmp_path, SMALL)
    abort_plan(tmp_path, site.plan)
    with pytest.raises(LifecycleRefused) as raised:
        analyze_gate(tmp_path, site.plan)
    assert str(raised.value) == "plan aborted; no verdict", f"got {raised.value}"


def test_L5_analyze_on_a_running_plan_says_to_wait(tmp_path):
    site = ready_site(tmp_path, SMALL)
    start_running(site)
    with pytest.raises(LifecycleRefused) as raised:
        analyze_gate(tmp_path, site.plan)
    assert str(raised.value).startswith("plan still running; analyze after Complete or BudgetStopped. Rule:"), f"got {raised.value}"


@pytest.mark.parametrize("early", [(), (PlanState.WORLD_VALIDATED,), (PlanState.WORLD_VALIDATED, PlanState.REACHABILITY_CHECKED)])
def test_L5_analyze_before_the_plan_runs_is_refused(tmp_path, early):
    site = make_site(tmp_path, SMALL)
    for step in early:
        move_to(folder_of(site), step)
    with pytest.raises(LifecycleRefused) as raised:
        analyze_gate(tmp_path, site.plan)
    assert "analyze after Complete or BudgetStopped" in str(raised.value), f"got {raised.value}"


@pytest.mark.parametrize("allowed", [PlanState.COMPLETE, PlanState.BUDGET_STOPPED])
def test_L5_analyze_passes_the_gate_after_complete_or_budget_stopped(tmp_path, allowed):
    site = ready_site(tmp_path, SMALL)
    start_running(site)
    move_to(folder_of(site), allowed)
    assert analyze_gate(tmp_path, site.plan) is allowed, f"{allowed} must pass the gate"
    observed = read_state(folder_of(site))
    assert observed is allowed, f"the gate does not move the state; got {observed}, expected allowed"


def test_L3_a_run_finishing_after_an_abort_leaves_its_unusable_record_unchanged(tmp_path):
    site = ready_site(tmp_path, SMALL)
    start_running(site)
    context = context_for(site, costing_runner(0.01))
    job = claim_next_job(context)
    abort_plan(tmp_path, site.plan)
    before = load_records(folder_of(site))
    outcome = finish_job(context, job, success_transcript(0.01))
    assert outcome is None, f"a run that ends after the abort must be skipped; got {outcome}, expected None. Rule: L3. Fix: skip runs that are no longer Started."
    assert load_records(folder_of(site)) == before, f"the store changed after the abort: {before} became {load_records(folder_of(site))}. Rule: L3, a recorded run never changes."
