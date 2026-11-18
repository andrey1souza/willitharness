from hypothesis import given, settings
from hypothesis import strategies as st

from willitharness.store import (
    EMPTY_COUNTERS,
    Cell,
    PlanFacts,
    Record,
    RunState,
    StoreError,
    cell_counters,
    run_id_of,
    runs_to_start,
    spent,
    with_record,
)

EXAMPLES = 300
CELLS = (Cell("A", "t1"), Cell("B", "t1"))
property_settings = settings(max_examples=EXAMPLES, deadline=None)


@st.composite
def records(draw):
    cell = draw(st.sampled_from(CELLS))
    rep = draw(st.integers(min_value=1, max_value=3))
    attempt = draw(st.integers(min_value=1, max_value=3))
    state = draw(st.sampled_from(list(RunState)))
    cost = draw(st.integers(min_value=0, max_value=5)) / 100
    return Record(run_id_of(cell, rep, attempt), cell.arm, cell.task, rep, attempt, state, {"completed": state is RunState.RECORDED_USABLE}, cost)


def admitted(history, record):
    try:
        return with_record(history, record)
    except StoreError:
        return history


def counter_view(history):
    counters = cell_counters(history)
    return {cell: (counters.get(cell, EMPTY_COUNTERS).usable, counters.get(cell, EMPTY_COUNTERS).attempts) for cell in CELLS}


@property_settings
@given(st.lists(records(), max_size=40))
def test_L3_counters_never_decrease_for_any_record_sequence(sequence):
    history = ()
    for record in sequence:
        before, before_spent = counter_view(history), spent(history)
        history = admitted(history, record)
        after = counter_view(history)
        assert all(after[cell][0] >= before[cell][0] for cell in CELLS), f"usable fell from {before} to {after} on {record}"
        assert all(after[cell][1] >= before[cell][1] for cell in CELLS), f"attempts fell from {before} to {after} on {record}"
        assert spent(history) >= before_spent, f"spent fell from {before_spent} to {spent(history)} on {record}"


@property_settings
@given(st.lists(records(), max_size=40), st.integers(min_value=1, max_value=6), st.integers(min_value=0, max_value=4))
def test_L4_L9_runs_to_start_never_pass_reps_or_attempt_cap_from_any_history(sequence, reps, max_retries):
    history = ()
    for record in sequence:
        history = admitted(history, record)
    facts = PlanFacts(CELLS, reps, max_retries)
    counters = cell_counters(history)
    for cell, count in runs_to_start(facts, history).items():
        seen = counters.get(cell, EMPTY_COUNTERS)
        assert count == 0 or seen.usable + seen.in_flight + count <= reps, f"{cell}: {count} starts pass {reps} reps over {seen}"
        assert count == 0 or seen.attempts + count <= reps + max_retries, f"{cell}: {count} starts pass the cap over {seen}, retries {max_retries}"


@property_settings
@given(st.lists(st.booleans(), min_size=1, max_size=60), st.integers(min_value=1, max_value=6), st.integers(min_value=0, max_value=4))
def test_L4_L9_a_simulated_plan_never_passes_the_limits(outcomes, reps, max_retries):
    facts = PlanFacts(CELLS[:1], reps, max_retries)
    cell = CELLS[0]
    history = ()
    for usable in outcomes:
        if runs_to_start(facts, history)[cell] == 0:
            break
        seen = cell_counters(history).get(cell, EMPTY_COUNTERS)
        attempt = seen.attempts + 1
        started = Record(run_id_of(cell, attempt, attempt), cell.arm, cell.task, attempt, attempt, RunState.STARTED, {}, 0)
        state = RunState.RECORDED_USABLE if usable else RunState.RECORDED_UNUSABLE
        ended = Record(started.run_id, cell.arm, cell.task, attempt, attempt, state, {"completed": usable}, 0.01)
        history = with_record(with_record(history, started), ended)
        now = cell_counters(history)[cell]
        assert now.usable + now.in_flight <= reps, f"usable {now.usable} passed reps {reps}"
        assert now.attempts <= reps + max_retries, f"attempts {now.attempts} passed {reps} + {max_retries}"
