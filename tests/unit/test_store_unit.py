import pytest

from willitharness.plan import load_plan
from willitharness.store import (
    Cell,
    CellCounters,
    PlanFacts,
    Record,
    RunState,
    StoreError,
    cell_counters,
    facts_from_plan,
    in_flight_runs,
    run_id_of,
    runs_to_start,
    spent,
    with_record,
)

CELL = Cell("B", "stop-server")
OTHER_CELL = Cell("C", "stop-server")
FACTS = PlanFacts(cells=(CELL, OTHER_CELL), reps=20, max_retries=2)
RUN_COST = 0.01


def unit_record(cell, attempt, state):
    usable = {"completed": state is RunState.RECORDED_USABLE}
    return Record(run_id_of(cell, attempt, attempt), cell.arm, cell.task, attempt, attempt, state, usable, RUN_COST)


def history(cell, usable=0, unusable=0, in_flight=0):
    states = [RunState.RECORDED_USABLE] * usable + [RunState.RECORDED_UNUSABLE] * unusable + [RunState.STARTED] * in_flight
    return tuple(unit_record(cell, number, state) for number, state in enumerate(states, start=1))


def test_run_id_names_arm_task_rep_and_attempt():
    assert run_id_of(Cell("B", "stop-server"), 7, 1) == "B/stop-server/7#1", "the run id must read arm/task/rep#attempt"
    assert run_id_of(Cell("C", "x"), 1, 3) == "C/x/1#3", "the attempt must follow the hash"


def test_a_different_record_for_a_recorded_run_fails_and_keeps_the_history():
    stored = history(CELL, usable=1)
    changed = Record(stored[0].run_id, "B", "stop-server", 1, 1, RunState.RECORDED_UNUSABLE, {"completed": False}, RUN_COST)
    with pytest.raises(StoreError) as caught:
        with_record(stored, changed)
    assert "L3" in str(caught.value), f"the error must name the rule L3, got {caught.value}"
    assert stored[0].state is RunState.RECORDED_USABLE, f"the stored record changed to {stored[0]}"


def test_the_same_record_again_adds_nothing():
    stored = history(CELL, usable=1)
    assert with_record(stored, stored[0]) == stored, f"a repeated record must be ignored, got {with_record(stored, stored[0])}"
    assert len(with_record(stored, stored[0])) == 1, "the repeat grew the history"


def test_a_started_run_may_end_once_and_then_never_change():
    started = history(CELL, in_flight=1)
    ended = Record(started[0].run_id, "B", "stop-server", 1, 1, RunState.RECORDED_USABLE, {"completed": True}, RUN_COST)
    done = with_record(started, ended)
    assert [item.state for item in done] == [RunState.STARTED, RunState.RECORDED_USABLE], f"unexpected history {done}"
    other_end = Record(started[0].run_id, "B", "stop-server", 1, 1, RunState.RECORDED_UNUSABLE, {"completed": False}, RUN_COST)
    with pytest.raises(StoreError):
        with_record(done, other_end)
    assert done[-1].state is RunState.RECORDED_USABLE, f"the ended run changed to {done[-1]}"


def test_a_started_run_cannot_end_as_another_cell():
    started = history(CELL, in_flight=1)
    moved = Record(started[0].run_id, "C", "stop-server", 1, 1, RunState.RECORDED_USABLE, {"completed": True}, RUN_COST)
    with pytest.raises(StoreError) as caught:
        with_record(started, moved)
    assert "B/stop-server/1#1" in str(caught.value), f"the error must name the run, got {caught.value}"


def test_counters_split_usable_unusable_and_in_flight_runs():
    records = history(CELL, usable=5, unusable=2, in_flight=3)
    assert cell_counters(records) == {CELL: CellCounters(usable=5, in_flight=3, attempts=10)}, f"got {cell_counters(records)}"


def test_a_run_that_started_and_ended_counts_as_one_attempt():
    started = history(CELL, in_flight=1)
    ended = Record(started[0].run_id, "B", "stop-server", 1, 1, RunState.RECORDED_USABLE, {"completed": True}, RUN_COST)
    counters = cell_counters(with_record(started, ended))
    assert counters == {CELL: CellCounters(usable=1, in_flight=0, attempts=1)}, f"got {counters}"


def test_spent_adds_only_recorded_costs():
    records = history(CELL, usable=2, unusable=1, in_flight=2)
    assert spent(records) == pytest.approx(0.03), f"spent must be 0.03 for three recorded runs, got {spent(records)}"
    assert spent(()) == 0, f"spent of no records must be 0, got {spent(())}"


def test_in_flight_runs_lists_started_runs_without_an_end():
    records = history(CELL, usable=1, in_flight=2)
    assert [run.run_id for run in in_flight_runs(records)] == ["B/stop-server/2#2", "B/stop-server/3#3"], f"got {in_flight_runs(records)}"
    assert in_flight_runs(history(CELL, usable=3)) == (), "a cell with no started run has none in flight"


def test_L4_twelve_usable_runs_of_twenty_resume_to_eight_more_in_each_cell():
    records = history(CELL, usable=12) + history(OTHER_CELL, usable=12)
    assert runs_to_start(FACTS, records) == {CELL: 8, OTHER_CELL: 8}, f"got {runs_to_start(FACTS, records)}"


def test_L4_a_finished_plan_resumes_to_nothing():
    records = history(CELL, usable=20) + history(OTHER_CELL, usable=20)
    assert runs_to_start(FACTS, records) == {CELL: 0, OTHER_CELL: 0}, f"got {runs_to_start(FACTS, records)}"


def test_a_plan_with_no_records_starts_every_rep():
    assert runs_to_start(FACTS, ()) == {CELL: 20, OTHER_CELL: 20}, f"got {runs_to_start(FACTS, ())}"


def test_runs_in_flight_take_a_rep_before_they_end():
    records = history(CELL, usable=10, in_flight=4)
    assert runs_to_start(FACTS, records)[CELL] == 6, f"20 reps - 10 usable - 4 in flight leaves 6, got {runs_to_start(FACTS, records)}"


def test_L9_an_unusable_run_does_not_use_a_rep():
    records = history(CELL, unusable=2)
    assert runs_to_start(FACTS, records)[CELL] == 20, f"two unusable runs must leave all 20 reps, got {runs_to_start(FACTS, records)}"


def test_L9_attempts_stop_at_reps_plus_max_retries():
    records = history(CELL, unusable=21)
    assert runs_to_start(FACTS, records)[CELL] == 1, f"21 attempts leave one of 22, got {runs_to_start(FACTS, records)}"
    assert runs_to_start(FACTS, history(CELL, unusable=22))[CELL] == 0, "22 attempts must end the cell"


def test_L9_retries_stop_when_the_cell_is_full():
    records = history(CELL, usable=20)
    assert runs_to_start(FACTS, records)[CELL] == 0, f"a full cell must not start, got {runs_to_start(FACTS, records)}"
    mixed = history(CELL, unusable=2) + tuple(unit_record(CELL, number, RunState.RECORDED_USABLE) for number in range(3, 23))
    assert runs_to_start(FACTS, mixed)[CELL] == 0, f"2 unusable and 20 usable must start nothing, got {runs_to_start(FACTS, mixed)}"


def test_attempts_in_flight_count_toward_the_attempt_cap():
    records = history(CELL, unusable=20, in_flight=1)
    assert runs_to_start(FACTS, records)[CELL] == 1, f"21 attempts, one in flight, leave one start, got {runs_to_start(FACTS, records)}"


def test_a_plan_without_reps_resumes_to_twenty_runs_per_cell():
    plan = load_plan({"schema": 1, "name": "p", "budget_usd": 1.0, "run_cap_usd": 0.02, "arms": [{"label": "B", "role": "rule", "overlay": "o"}]})
    facts = facts_from_plan(plan, ("stop-server",))
    assert facts.reps == 20, f"a plan with no reps must default to 20, got {facts.reps}"
    assert facts.max_retries == 2, f"a plan with no max_retries must default to 2, got {facts.max_retries}"
    assert runs_to_start(facts, ()) == {CELL: 20}, f"got {runs_to_start(facts, ())}"
