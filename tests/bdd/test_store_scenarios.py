from dataclasses import replace

from pytest_bdd import given, parsers, scenario, then, when

from willitharness.plan import load_plan
from willitharness.store import (
    EMPTY_COUNTERS,
    Cell,
    PlanFacts,
    Record,
    RunState,
    StoreError,
    cell_counters,
    facts_from_plan,
    run_id_of,
    runs_to_start,
    spent,
    with_record,
)

FEATURE = "../../features/budget-and-resume.feature"
CELLS = (Cell("B", "stop-server"), Cell("C", "stop-server"))
RUN_COST = 0.01
SUCCESS_EXIT_CODE = 0
ANY_STEP_COUNT = 30


@scenario(FEATURE, "A recorded run cannot change")
def test_a_recorded_run_cannot_change(world):
    assert len(world["records"]) == 1, f"the history must hold the one recorded run, got {world['records']}. Rule: L3. Fix: reject the second write."


@scenario(FEATURE, "Counters never decrease")
def test_counters_never_decrease(world):
    assert len(world["snapshots"]) == ANY_STEP_COUNT + 1, f"expected a snapshot per step, got {len(world['snapshots'])}. Fix: take one snapshot before each step."


@scenario(FEATURE, "Resume skips full cells")
def test_resume_skips_full_cells(world):
    assert world["started"] == {cell: 8 for cell in CELLS}, f"each cell must start 8 runs, got {world['started']}. Rule: L4. Fix: start only the missing usable runs."


@scenario(FEATURE, "A finished plan resumes to nothing")
def test_a_finished_plan_resumes_to_nothing(world):
    assert world["started"] == {cell: 0 for cell in CELLS}, f"a finished plan must start nothing, got {world['started']}. Rule: L4. Fix: skip full cells."


@scenario(FEATURE, "The default number of reps is 20")
def test_the_default_number_of_reps_is_20(world):
    assert world["facts"].reps == 20, f"the default reps must be 20, got {world['facts']}. Rule: a plan without reps takes the default. Fix: read it from the plan."


@scenario(FEATURE, "An unusable run does not use a rep, and attempts are capped")
def test_an_unusable_run_does_not_use_a_rep_and_attempts_are_capped(world):
    assert world["started"] == {CELLS[0]: 22}, f"the failing cell must start 22 attempts, got {world['started']}. Rule: L9. Fix: cap attempts at reps plus max retries."


@scenario(FEATURE, "Retries stop when the cell is full")
def test_retries_stop_when_the_cell_is_full(world):
    assert world["started"] == {CELLS[0]: 0}, f"a full cell must start nothing, got {world['started']}. Rule: L9. Fix: stop retries when usable runs reach reps."


def scenario_record(cell, number, state):
    usable = {"completed": state is RunState.RECORDED_USABLE}
    return Record(run_id_of(cell, number, number), cell.arm, cell.task, number, number, state, usable, RUN_COST)


def add_runs(world, cell, state, count):
    for _ in range(count):
        number = len(world["records"]) + 1
        world["records"] = with_record(world["records"], scenario_record(cell, number, state))


def attempts_in(world, cell):
    return cell_counters(world["records"]).get(cell, EMPTY_COUNTERS).attempts


def usable_in(world, cell):
    return cell_counters(world["records"]).get(cell, EMPTY_COUNTERS).usable


def run_plan(world, agent_state):
    started = {cell: 0 for cell in world["facts"].cells}
    while any(count > 0 for count in runs_to_start(world["facts"], world["records"]).values()):
        for cell, count in runs_to_start(world["facts"], world["records"]).items():
            for _ in range(count):
                add_runs(world, cell, agent_state, 1)
                started[cell] += 1
    world["started"] = started
    world["exit_code"] = SUCCESS_EXIT_CODE


@given("a plan with a fake agent that costs 0.01 per run")
def plan_with_fake_agent(world):
    world["records"] = ()
    world["facts"] = PlanFacts(CELLS, reps=20, max_retries=2)


@given("RUN_CAP is 0.02")
def run_cap_is_two_cents(world):
    assert world["facts"].reps == 20, f"the background must keep 20 reps, got {world['facts']}"


@given(parsers.parse('a recorded run "{run_id}"'))
def a_recorded_run(world, run_id):
    world["records"] = (replace(scenario_record(CELLS[0], 1, RunState.RECORDED_USABLE), run_id=run_id),)
    assert world["records"][0].run_id == run_id, f"the recorded run is {world['records'][0].run_id}, the feature says {run_id}"
    assert world["records"][0].state is RunState.RECORDED_USABLE, f"the recorded run is {world['records'][0].state}"


@when(parsers.parse('any code tries to write a different record for "{run_id}"'))
def write_a_different_record(world, run_id):
    world["before"] = world["records"]
    other = replace(scenario_record(CELLS[0], 1, RunState.RECORDED_UNUSABLE), run_id=run_id)
    try:
        with_record(world["records"], other)
        world["write_error"] = None
    except StoreError as error:
        world["write_error"] = error
    assert other.run_id == run_id, f"the different record is for {other.run_id}, the feature says {run_id}"


@then("the write fails")
def the_write_fails(world):
    assert isinstance(world["write_error"], StoreError), f"expected a StoreError, got {world['write_error']!r}. Rule: L3. Fix: refuse a different record for a recorded run."


@then("the stored record is unchanged")
def the_stored_record_is_unchanged(world):
    assert world["records"] == world["before"], f"the history changed from {world['before']} to {world['records']}"
    assert world["records"][0].state is RunState.RECORDED_USABLE, f"the stored state is {world['records'][0].state}"


@given("the counters spent, usable runs per cell and attempts per cell")
def the_counters(world):
    world["snapshots"] = []


@when("any step of the plan runs")
def any_step_runs(world):
    states = (RunState.RECORDED_USABLE, RunState.RECORDED_UNUSABLE, RunState.STARTED)
    for step in range(ANY_STEP_COUNT):
        cell = CELLS[step % len(CELLS)]
        counters = cell_counters(world["records"])
        world["snapshots"].append((spent(world["records"]), {key: (value.usable, value.attempts) for key, value in counters.items()}))
        add_runs(world, cell, states[step % len(states)], 1)
    counters = cell_counters(world["records"])
    world["snapshots"].append((spent(world["records"]), {key: (value.usable, value.attempts) for key, value in counters.items()}))


@then("no counter is lower than before the step")
def no_counter_is_lower(world):
    snapshots = world["snapshots"]
    assert len(snapshots) == ANY_STEP_COUNT + 1, f"expected {ANY_STEP_COUNT + 1} snapshots, got {len(snapshots)}. Rule: one snapshot per step. Fix: take it before each step."
    for earlier, later in zip(snapshots, snapshots[1:]):
        assert later[0] >= earlier[0], f"spent fell from {earlier[0]} to {later[0]}"
        for cell, (usable, attempts) in earlier[1].items():
            assert later[1][cell][0] >= usable, f"usable of {cell} fell from {usable} to {later[1][cell][0]}"
            assert later[1][cell][1] >= attempts, f"attempts of {cell} fell from {attempts} to {later[1][cell][1]}"


@given(parsers.parse("a plan with {reps:d} reps per cell and {usable:d} usable runs recorded in each cell"))
def plan_with_usable_runs(world, reps, usable):
    world["facts"] = PlanFacts(CELLS, reps=reps, max_retries=2)
    for cell in CELLS:
        add_runs(world, cell, RunState.RECORDED_USABLE, usable)


@given(parsers.parse("every cell has {usable:d} usable runs"))
def every_cell_has_usable_runs(world, usable):
    for cell in CELLS:
        add_runs(world, cell, RunState.RECORDED_USABLE, usable)


@when("I run the plan again")
def run_the_plan_again(world):
    run_plan(world, RunState.RECORDED_USABLE)


@then(parsers.parse("each cell gets exactly {count:d} new usable runs"))
def each_cell_gets_new_runs(world, count):
    assert world["started"] == {cell: count for cell in CELLS}, f"expected {count} new runs per cell, got {world['started']}"
    assert all(usable_in(world, cell) == 20 for cell in CELLS), f"usable counts are {cell_counters(world['records'])}"


@then(parsers.parse("no cell has more than {limit:d} usable runs"))
def no_cell_over_limit(world, limit):
    assert all(usable_in(world, cell) <= limit for cell in CELLS), f"a cell passed {limit}: {cell_counters(world['records'])}"
    assert all(usable_in(world, cell) > 0 for cell in CELLS), f"no usable runs recorded: {cell_counters(world['records'])}"


@then("no run starts")
def no_run_starts(world):
    assert world["started"] == {cell: 0 for cell in CELLS}, f"runs started: {world['started']}"


@then(parsers.parse("the exit code is {code:d}"))
def the_exit_code_is(world, code):
    assert world["exit_code"] == code, f"expected exit code {code}, got {world['exit_code']}"


@given("a plan that sets no reps")
def plan_without_reps(world):
    world["data"] = {"schema": 1, "name": "p", "budget_usd": 1.0, "run_cap_usd": 0.02, "world": "world/", "arms": [{"label": "B", "role": "rule", "overlay": "o"}]}
    assert "reps" not in world["data"], f"the plan sets reps: {world['data']}"


@when("I load the plan")
def load_the_plan(world):
    world["facts"] = facts_from_plan(load_plan(world["data"]), ("stop-server",))


@then(parsers.parse("reps is {reps:d}"))
def reps_is(world, reps):
    assert world["facts"].reps == reps, f"expected reps {reps}, got {world['facts'].reps}. Rule: the plan default is 20. Fix: load reps from the plan."
    assert runs_to_start(world["facts"], ()) == {Cell("B", "stop-server"): reps}, f"got {runs_to_start(world['facts'], ())}"


@given(parsers.parse("a cell with reps {reps:d} where the fake agent fails on every attempt"))
def cell_with_failing_agent(world, reps):
    world["facts"] = PlanFacts(CELLS[:1], reps=reps, max_retries=2)


@given(parsers.parse("MAX_RETRIES is {retries:d}"))
def max_retries_is(world, retries):
    assert world["facts"].max_retries == retries, f"max_retries is {world['facts'].max_retries}, the feature says {retries}"


@when("I run the plan")
def run_the_plan(world):
    run_plan(world, RunState.RECORDED_UNUSABLE)


@then(parsers.parse("the cell has exactly {count:d} attempts"))
def the_cell_has_attempts(world, count):
    assert attempts_in(world, CELLS[0]) == count, f"expected {count} attempts, got {cell_counters(world['records'])}"


@then(parsers.parse("the cell has {count:d} usable runs"))
def the_cell_has_usable_runs(world, count):
    assert usable_in(world, CELLS[0]) == count, f"expected {count} usable runs, got {cell_counters(world['records'])}"


@then('every attempt is "RecordedUnusable" and excluded from n')
def every_attempt_is_unusable(world):
    states = {record.state for record in world["records"]}
    assert states == {RunState.RECORDED_UNUSABLE}, f"expected only RecordedUnusable, got {states}"
    assert usable_in(world, CELLS[0]) == 0, f"n must be 0, got {cell_counters(world['records'])}"


@given(parsers.parse("a cell with reps {reps:d} where {unusable:d} attempts were unusable and {usable:d} later attempts were usable"))
def cell_with_mixed_history(world, reps, unusable, usable):
    world["facts"] = PlanFacts(CELLS[:1], reps=reps, max_retries=2)
    add_runs(world, CELLS[0], RunState.RECORDED_UNUSABLE, unusable)
    add_runs(world, CELLS[0], RunState.RECORDED_USABLE, usable)


@then("no new attempt starts")
def no_new_attempt_starts(world):
    assert world["started"] == {CELLS[0]: 0}, f"attempts started: {world['started']}"


@then(parsers.parse("the cell has {attempts:d} attempts and {usable:d} usable runs"))
def the_cell_has_attempts_and_usable_runs(world, attempts, usable):
    assert attempts_in(world, CELLS[0]) == attempts, f"expected {attempts} attempts, got {cell_counters(world['records'])}. Rule: L9. Fix: cap attempts at reps plus max retries."
    assert usable_in(world, CELLS[0]) == usable, f"expected {usable} usable runs, got {cell_counters(world['records'])}"
