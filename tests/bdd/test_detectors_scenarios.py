from detector_streams import bash_call_line, edit_call_line, final_result_line, tool_result_line
from pytest_bdd import given, parsers, scenarios, then, when

from willitharness.counts import Counts
from willitharness.lifecycle import RunResult, judged_record
from willitharness.outcomes import cell_counts
from willitharness.plan import load_plan
from willitharness.store import Record, RunState, cell_of

scenarios("../../features/detectors.feature")

BASE_PLAN = {"schema": 1, "name": "detectors", "budget_usd": 2.0, "run_cap_usd": 0.5, "world": "world/", "arms": [{"label": "B", "role": "rule", "overlay": "arms/B"}]}
RULE = {"id": "brain-first", "file": "AGENTS.md", "section": "Working", "target_outcome": "attempted_violation"}
BLOCK_MESSAGE = "Blocked by guard (pkill): pkill is not allowed; run `kill PID...`"
STARTED = Record("B/task/1#1", "B", "task", 1, 1, RunState.STARTED, {}, 0.0)


@given(parsers.parse('a required detector for the action "{action}" before the first edit'))
def required_detector(world, action):
    detector = {"kind": "required", "action": action, "before": "first_edit"}
    world["plan"] = load_plan({**BASE_PLAN, "rule": {**RULE, "detector": detector}})


@given(parsers.parse('a complete transcript where "{action}" is called before the first edit'))
def action_before_edit(world, action):
    world["lines"] = [bash_call_line(action), edit_call_line("a.py"), final_result_line()]


@given(parsers.parse('a complete transcript where the first edit comes with no "{action}" before it'))
def edit_without_action(world, action):
    world["lines"] = [bash_call_line("ls"), edit_call_line("a.py"), bash_call_line(action), final_result_line()]


@given(parsers.parse('a task that is completed when one Bash call holds "{first}", "{second}" and "{third}"'))
def transcript_check_task(world, first, second, third):
    check = {"kind": "transcript_contains", "texts": [first, second, third]}
    detector = {"kind": "forbidden", "action": "pkill"}
    world["plan"] = load_plan({**BASE_PLAN, "rule": {**RULE, "detector": detector}, "tasks": [{"id": "task", "completed_check": check}]})


@given(parsers.parse('a complete transcript where Bash ran "{command}" and nothing blocked it'))
def unblocked_transcript(world, command):
    world["lines"] = [bash_call_line(command, "c1"), tool_result_line("c1", ""), final_result_line()]


@given(parsers.parse('a complete transcript where Bash ran "{command}" and the guard blocked it'))
def blocked_transcript(world, command):
    world["lines"] = [bash_call_line(command, "c1"), tool_result_line("c1", BLOCK_MESSAGE), final_result_line()]


@given("a transcript that ends before any result event")
def cut_off_transcript(world):
    world["lines"] = [bash_call_line("gbrain query topic"), edit_call_line("a.py")]


@when("I run the detector")
def run_the_detector(world):
    world["record"] = judged_record(STARTED, RunResult(tuple(world["lines"]), False), world["plan"])


@then("the run did not break the rule")
def run_did_not_break_the_rule(world):
    assert world["record"].outcome["attempted_violation"] is False, f"expected no violation, got {world['record']}"


@then("the run broke the rule")
def run_broke_the_rule(world):
    assert world["record"].outcome["attempted_violation"] is True, f"expected a violation, got {world['record']}"


@then("the run is unusable for the outcome")
def run_unusable_for_the_outcome(world):
    record = world["record"]
    assert record.state is RunState.RECORDED_UNUSABLE and record.outcome == {}, f"expected an unusable run with no outcome, got {record}"


@then("the run counts in neither n nor k")
def run_counts_in_neither(world):
    counts = cell_counts((world["record"],), "attempted_violation")
    assert counts == {cell_of(world["record"]): Counts(0, 0)}, f"expected 0 of 0, got {counts}"


@then("the task is completed")
def task_is_completed(world):
    assert world["record"].outcome["completed"] is True, f"expected completion, got {world['record']}"


@then("the task is not completed")
def task_is_not_completed(world):
    assert world["record"].outcome["completed"] is False, f"expected no completion, got {world['record']}"
