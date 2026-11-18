import json
from pathlib import Path

from analysis_site import COMPLETED, FULL_ROLES, LOO_LABEL, OTHER_TASK, REPEAT_LABEL, RULE_LABEL, TARGET, TASK, TWO_TASK_CELLS, CellShape, analysis_plan_data
from cli_runner import run_cli
from pytest_bdd import given, parsers, scenarios, then, when

from willitharness.arms import remove_section
from willitharness.decision import decide
from willitharness.store import Cell
from willitharness.vocabulary import EffectResult, GuardResult, NoiseStatus, Reach

scenarios("../../../features/effect-with-noise.feature")

LOO_SOURCE = Path(__file__).resolve().parents[3] / "fixtures" / "probe" / "loo-source" / "AGENTS.md"
REMOVED_SECTION_LINES = ("## Working here as an agent", "Verification code: ZQ-8841-lumen")
REMOVED_WORD_COUNT = 9
KEPT_SECTION_TEXT = "## Style\n\nReference code: lagoon-52"
BAD_REPEAT_LABEL = "B2"


@given(parsers.parse('a plan with a rule arm "{rule}", a LOO arm "{loo}" and a noise repeat "{repeat}" of arm "{target}"'))
def background_plan(world, rule, loo, repeat, target):
    assert (rule, loo, repeat, target) == (RULE_LABEL, LOO_LABEL, REPEAT_LABEL, LOO_LABEL), f"the support site names {RULE_LABEL}, {LOO_LABEL}, {REPEAT_LABEL}"


@given(parsers.parse('the outcome is "{name}"'))
def outcome_is(name):
    assert name == TARGET, f"the effect uses {TARGET}, the feature says {name}"


@given(parsers.parse("{count:d} usable runs per cell"))
def usable_runs_per_cell(world, count):
    world["default_n"] = count
    assert count == 20, f"the feature fixes 20 usable runs per cell, got {count}"


@given(parsers.parse('a plan whose noise repeat "{repeat}" repeats the rule arm "{rule}"'))
def plan_repeating_the_rule_arm(world, repeat, rule):
    world["roles"] = {**FULL_ROLES, repeat: f"noise_of:{rule}"}


@when("I check the plan")
def check_the_plan(world, tmp_path, monkeypatch, capsys):
    (tmp_path / "plan.json").write_text(json.dumps(analysis_plan_data(world["roles"])))
    monkeypatch.chdir(tmp_path)
    world["exit_code"], out, world["message"] = run_cli(capsys, ["plan", "check", "plan.json"])
    assert world["exit_code"] in (0, 1), f"plan check exits 0 or 1, got {world['exit_code']}"


@given(parsers.parse('the rule file "{name}" with the section "{section}"'))
def rule_file_with_section(world, name, section):
    assert name == "AGENTS.md", f"the fixture holds AGENTS.md, the feature says {name}"
    world["source"], world["section"] = LOO_SOURCE.read_text(), section


@when("I build the LOO arm")
def build_the_loo_arm(world):
    world["arm"] = remove_section(world["source"], world["section"])


@then("the arm file has every other section unchanged")
def other_sections_unchanged(world):
    assert KEPT_SECTION_TEXT in world["arm"] and "# Project rules" in world["arm"], f"got {world['arm']!r}"


@then("the arm file does not contain any line of the removed section")
def removed_lines_are_gone(world):
    assert not set(REMOVED_SECTION_LINES) & set(world["arm"].splitlines()), f"got {world['arm']!r}"


@then("the removed word count equals the section word count")
def removed_word_count(world):
    assert len(world["source"].split()) - len(world["arm"].split()) == REMOVED_WORD_COUNT, f"got {world['arm']!r}"


def violating(first, second):
    return {Cell(first[0], TASK): CellShape(first[2], first[1]), Cell(second[0], TASK): CellShape(second[2], second[1])}


@given(
    parsers.re(r'arm "(?P<first>[^"]+)" has (?P<k1>\d+) of (?P<n1>\d+) violating runs and arm "(?P<second>[^"]+)" has (?P<k2>\d+) of (?P<n2>\d+)( usable runs)?'),
    converters={"k1": int, "n1": int, "k2": int, "n2": int},
)
def two_arms_with_counts(world, first, k1, n1, second, k2, n2):
    world["cells"].update(violating((first, k1, n1), (second, k2, n2)))


@given(parsers.re(r'arm "(?P<arm>[^"]+)" has (?P<k>\d+) of (?P<n>\d+)'), converters={"k": int, "n": int})
def one_arm_with_counts(world, arm, k, n):
    world["cells"][Cell(arm, TASK)] = CellShape(n, k)


@given(parsers.parse('a plan with arms "{rule}" and "{loo}" and no noise repeat'))
def plan_without_repeat(world, rule, loo):
    world["roles"] = {rule: "rule", loo: "leave_one_out"}


@then("no effect verdict is emitted")
def no_effect_verdict(world):
    assert any("no verdict" in line for line in world["lines"] if line.startswith(TARGET)), f"got {world['lines']}"


@then(parsers.parse('the effect result is "{name}"'))
def effect_result_is(world, name):
    reported = [world["effect"].effect] if "effect" in world else [EffectResult(line.split("effect ")[1].split(";")[0].split(" [")[0]) for line in world["lines"] if line.startswith(TARGET)]
    assert EffectResult(name) in reported, f"expected {name}, got {reported}"


@given(parsers.parse("each cell has only {n:d} usable runs"))
def cells_with_few_runs(world, n):
    world["few"] = n


@given(parsers.parse('the noise status is "{name}"'))
def noise_is_given(world, name):
    world["given_noise"] = NoiseStatus(name)


@then(parsers.parse('the decision is "{name}"'))
def decision_is(world, name):
    assert decide(Reach.LOADED, world["effect"].effect, GuardResult.GUARD_UNTESTED).value == name, f"got {world['effect']}"


@given(parsers.parse('tasks "{first}" and "{second}" with different counts'))
def two_tasks(world, first, second):
    assert (first, second) == (TASK, OTHER_TASK), f"the support counts name {TASK} and {OTHER_TASK}"
    world["cells"] = dict(TWO_TASK_CELLS)


@given(parsers.parse('{count:d} runs in arm "{arm}", task "{task}" are unusable for "completed" but usable for "attempted_violation"'))
def unusable_for_completed(world, count, arm, task):
    shape = world["cells"][Cell(arm, task)]
    world["cells"][Cell(arm, task)] = CellShape(shape.n, shape.k, unusable_for_completed=count)


@then("each task and outcome has its own n and k")
def each_task_and_outcome_has_a_line(world):
    for task in (TASK, OTHER_TASK):
        for outcome in (TARGET, COMPLETED):
            assert any(line.startswith(f"{outcome} {task} ") for line in world["lines"]), f"no line for {outcome} {task}: {world['lines']}"


@then(parsers.parse('the {count:d} runs count in n for "attempted_violation" and not in n for "completed"'))
def unusable_runs_count_per_outcome(world, count):
    target = [line for line in world["lines"] if line.startswith(f"{TARGET} {OTHER_TASK} ")]
    completed = [line for line in world["lines"] if line.startswith(f"{COMPLETED} {OTHER_TASK} ")]
    assert any("against B 2/20" in line for line in target), f"got {target}"
    assert any("against B 16/17" in line for line in completed) and count == 3, f"got {completed}"


@given(parsers.parse('verdicts for tasks "{first}" and "{second}"'))
def verdicts_for_two_tasks(world, first, second):
    assert (first, second) == (TASK, OTHER_TASK), f"the support counts name {TASK} and {OTHER_TASK}"
    world["cells"] = dict(TWO_TASK_CELLS)
