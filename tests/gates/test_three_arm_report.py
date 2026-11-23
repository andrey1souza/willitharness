import json
import subprocess
from pathlib import Path

import pytest
from analysis_site import FULL_ROLES, CellShape, site_with_state
from cli_runner import run_cli
from three_arm_site import ArmShape, SiteOptions, first, three_arm_site

from willitharness.component_arms import ARM_COMPONENT, ARM_NOISE, ARM_NOTHING, ARM_PROMPT
from willitharness.counts import Counts
from willitharness.lifecycle import PlanState
from willitharness.plan import load_plan
from willitharness.store import Cell
from willitharness.three_arm_report import (
    REMOVE_MIN_RUNS,
    arm_cost_turns_line,
    detectable_text,
    is_three_arm,
    smallest_detectable_drop,
    turns_of,
)

REPOSITORY = Path(__file__).resolve().parents[2]
DEMO_PLAN = "tests/golden/demo-three-arm-plan"
GOLDEN = REPOSITORY / "tests" / "golden" / "demo-three-arm-report.md"
EXIT_OK = 0
EXIT_REFUSED = 1
THREE_LABELS = (ARM_COMPONENT, ARM_PROMPT, ARM_NOTHING)
KEEP_SHAPES = {ARM_COMPONENT: ArmShape(20, frozenset({1, 18}), first(16)), ARM_PROMPT: ArmShape(20, first(11)), ARM_NOTHING: ArmShape(20, first(12))}
KEEP_LINE = "decision stop-server C: KeepComponent (arm C 2 of 20 runs, arm P 11 of 20 runs, arm N 12 of 20 runs)"
EQUAL_ARMS = {arm: ArmShape(20, first(10)) for arm in THREE_LABELS}
JUST_BELOW = REMOVE_MIN_RUNS - 1
EQUAL_BELOW = {arm: ArmShape(JUST_BELOW, first(JUST_BELOW // 2)) for arm in THREE_LABELS}
SMALL = {arm: ArmShape(3, first(1)) for arm in THREE_LABELS}


def arm_site_in(tmp_path, monkeypatch, shapes, options=SiteOptions()):
    site = three_arm_site(tmp_path, shapes, options)
    monkeypatch.chdir(tmp_path)
    return site


def arm_section_of(text, heading):
    assert heading in text, f"the report has no {heading!r}: {text!r}"
    return text.split(heading, 1)[1].split("\n## ", 1)[0]


def arm_report_of(capsys, argument="plan.json"):
    return run_cli(capsys, ["report", argument])


def three_arm_golden_text():
    text = GOLDEN.read_text()
    assert text.startswith("# Report"), f"the golden file starts with {text[:20]!r}. Fix: restore tests/golden/demo-three-arm-report.md."
    return text


def arm_diff_exit_code(text, golden_path):
    return subprocess.run(["diff", "-", str(golden_path)], input=text, capture_output=True, text=True).returncode


def test_T70_the_three_arm_demo_report_equals_the_golden_file(monkeypatch, capsys):
    monkeypatch.chdir(REPOSITORY)
    code, out, err = arm_report_of(capsys, DEMO_PLAN)
    assert code == EXIT_OK and err == "", f"got {code} {out!r} {err!r}"
    assert out == three_arm_golden_text(), "the report differs from tests/golden/demo-three-arm-report.md. Fix: change the code back, or regenerate the golden file on purpose."
    assert arm_diff_exit_code(out, GOLDEN) == EXIT_OK, "diff found a difference between the report and the golden file"


def test_T70_an_edited_golden_file_makes_diff_exit_one(monkeypatch, capsys, tmp_path):
    monkeypatch.chdir(REPOSITORY)
    code, out, err = arm_report_of(capsys, DEMO_PLAN)
    edited = tmp_path / "edited.md"
    edited.write_text(three_arm_golden_text().replace("KeepComponent", "DeleteCandidate", 1))
    assert code == EXIT_OK and arm_diff_exit_code(out, edited) == EXIT_REFUSED, f"diff accepted an edited golden file ({code} {err!r})"


def test_T70_the_decide_command_prints_the_verdict_of_the_three_arms(tmp_path, monkeypatch, capsys):
    arm_site_in(tmp_path, monkeypatch, KEEP_SHAPES)
    code, out, err = run_cli(capsys, ["decide", "plan.json"])
    assert code == EXIT_OK and out.splitlines() == [KEEP_LINE], f"got {code} {out!r} {err!r}"


def test_T70_the_trigger_rate_and_the_effect_when_it_fires_are_two_numbers(tmp_path, monkeypatch, capsys):
    arm_site_in(tmp_path, monkeypatch, KEEP_SHAPES)
    _, out, _ = arm_report_of(capsys)
    trigger = arm_section_of(out, "## Trigger")
    assert "Trigger rate of arm C: 16 of 20 runs (80%)." in trigger, f"got {trigger!r}"
    assert "arm C violated in 1 of 16 runs that fired. Arm N violated in 12 of 20 runs." in trigger, f"got {trigger!r}"
    assert "Arm N against the fired runs of arm C: FirstHigher." in trigger, f"got {trigger!r}"


def test_T70_turns_and_cost_are_shown_for_each_arm(tmp_path, monkeypatch, capsys):
    arm_site_in(tmp_path, monkeypatch, KEEP_SHAPES)
    _, out, _ = arm_report_of(capsys)
    shown = arm_section_of(out, "## Turns and cost per arm")
    assert "Arm C: 20 runs, mean cost $0.0100, mean turns 3.8 over 20 runs." in shown, f"got {shown!r}"
    assert "Arm P: 20 runs, mean cost $0.0100, mean turns 3.0 over 20 runs." in shown, f"got {shown!r}"
    assert "Arm N: 20 runs, mean cost $0.0100, mean turns 3.0 over 20 runs." in shown, f"got {shown!r}"


def test_T70_the_smallest_detectable_change_is_stated_for_each_comparison(tmp_path, monkeypatch, capsys):
    arm_site_in(tmp_path, monkeypatch, KEEP_SHAPES)
    _, out, _ = arm_report_of(capsys)
    shown = arm_section_of(out, "## Smallest detectable change")
    assert "arm C against arm P: the runs could detect an absolute drop of 35.0% in the violation rate, from 55%." in shown, f"got {shown!r}"
    assert "arm C against arm N: the runs could detect an absolute drop of 35.0% in the violation rate, from 60%." in shown, f"got {shown!r}"


def test_T70_too_few_runs_are_not_measurable_for_the_smallest_change(tmp_path, monkeypatch, capsys):
    arm_site_in(tmp_path, monkeypatch, SMALL)
    _, out, _ = arm_report_of(capsys)
    assert "not measurable. An arm has fewer than 5 runs." in arm_section_of(out, "## Smallest detectable change"), f"got {out!r}"


def test_T70_the_report_says_noise_on_arm_c_is_not_measured(tmp_path, monkeypatch, capsys):
    arm_site_in(tmp_path, monkeypatch, KEEP_SHAPES)
    _, out, _ = arm_report_of(capsys)
    assert "Noise on arm C is not measured separately." in arm_section_of(out, "## Three-arm verdict"), f"got {out!r}"


def test_T70_an_equal_result_with_enough_runs_is_a_remove_candidate(tmp_path, monkeypatch, capsys):
    arm_site_in(tmp_path, monkeypatch, EQUAL_ARMS)
    code, out, err = run_cli(capsys, ["decide", "plan.json"])
    assert code == EXIT_OK and out.startswith("decision stop-server C: remove candidate (arm C 10 of 20 runs"), f"got {code} {out!r} {err!r}"


def test_T70_an_equal_result_below_the_run_minimum_is_not_a_remove_candidate(tmp_path, monkeypatch, capsys):
    arm_site_in(tmp_path, monkeypatch, EQUAL_BELOW)
    code, out, err = run_cli(capsys, ["decide", "plan.json"])
    assert code == EXIT_OK and "remove candidate" not in out, f"got {code} {out!r} {err!r}"
    assert f"NeedsMoreRuns: removal needs at least {REMOVE_MIN_RUNS} runs in each arm" in out, f"got {out!r}"


def test_T70_one_short_arm_withholds_the_remove_candidate(tmp_path, monkeypatch, capsys):
    shapes = {**EQUAL_ARMS, ARM_NOTHING: ArmShape(JUST_BELOW, first(JUST_BELOW // 2))}
    arm_site_in(tmp_path, monkeypatch, shapes)
    _, out, _ = run_cli(capsys, ["decide", "plan.json"])
    assert "remove candidate" not in out and "NeedsMoreRuns" in out, f"got {out!r}"


def test_T70_the_report_decision_section_matches_the_decide_line(tmp_path, monkeypatch, capsys):
    arm_site_in(tmp_path, monkeypatch, EQUAL_BELOW)
    _, decided, _ = run_cli(capsys, ["decide", "plan.json"])
    _, reported, _ = arm_report_of(capsys)
    assert decided.strip() in arm_section_of(reported, "## Decision"), f"got {decided!r} and {reported!r}"


@pytest.mark.parametrize(("command", "message"), [("decide", "plan demo is ReachabilityChecked"), ("report", "no verdicts yet; run: willitharness analyze")])
def test_T70_a_plan_that_has_not_finished_is_refused(tmp_path, monkeypatch, capsys, command, message):
    arm_site_in(tmp_path, monkeypatch, KEEP_SHAPES, SiteOptions(state=PlanState.REACHABILITY_CHECKED))
    code, out, err = run_cli(capsys, [command, "plan.json"])
    assert code == EXIT_REFUSED and out == "" and message in err, f"got {code} {out!r} {err!r}"


@pytest.mark.parametrize("command", ["decide", "report"])
def test_T70_a_three_arm_plan_with_a_guard_arm_is_refused(tmp_path, monkeypatch, capsys, command):
    arm_site_in(tmp_path, monkeypatch, KEEP_SHAPES, SiteOptions(extra_arms=("G",)))
    code, out, err = run_cli(capsys, [command, "plan.json"])
    assert code == EXIT_REFUSED and out == "", f"got {code} {out!r} {err!r}"
    assert "plan demo has a guard_only arm" in err and "Rule:" in err and "Fix:" in err, f"got {err!r}"


def test_T70_decide_with_no_stored_runs_is_refused_with_rule_and_fix(tmp_path, monkeypatch, capsys):
    arm_site_in(tmp_path, monkeypatch, {})
    code, out, err = run_cli(capsys, ["decide", "plan.json"])
    assert code == EXIT_REFUSED and out == "" and "has no stored runs" in err and "Rule:" in err, f"got {code} {out!r} {err!r}"
    assert err.rstrip().endswith("Fix: run the plan first."), f"got {err!r}"


def test_T70_a_component_that_is_not_a_skill_has_no_trigger_rate(tmp_path, monkeypatch, capsys):
    arm_site_in(tmp_path, monkeypatch, KEEP_SHAPES, SiteOptions(channel="file"))
    _, out, _ = arm_report_of(capsys)
    assert "Arm C is not a skill. A trigger rate does not apply." in arm_section_of(out, "## Trigger"), f"got {out!r}"
    assert "Trigger rate" not in out, f"got {out!r}"


def test_T70_a_skill_with_no_stored_transcript_has_no_trigger_rate(tmp_path, monkeypatch, capsys):
    shapes = {**KEEP_SHAPES, ARM_COMPONENT: ArmShape(20, frozenset({1, 18}), first(16), transcripts=False)}
    arm_site_in(tmp_path, monkeypatch, shapes)
    _, out, _ = arm_report_of(capsys)
    assert "Trigger not measured. No usable run of arm C has a stored transcript." in arm_section_of(out, "## Trigger"), f"got {out!r}"
    assert "turns not measured" in arm_section_of(out, "## Turns and cost per arm"), f"got {out!r}"


def test_T70_a_skill_that_never_fires_has_no_effect_number(tmp_path, monkeypatch, capsys):
    shapes = {**KEEP_SHAPES, ARM_COMPONENT: ArmShape(20, frozenset({1, 18}))}
    arm_site_in(tmp_path, monkeypatch, shapes)
    _, out, _ = arm_report_of(capsys)
    trigger = arm_section_of(out, "## Trigger")
    assert "Trigger rate of arm C: 0 of 20 runs (0%)." in trigger and "No run of arm C fired the skill." in trigger, f"got {trigger!r}"


def test_T70_a_plan_is_three_arm_by_its_labels_and_not_by_its_roles(tmp_path):
    site = three_arm_site(tmp_path, {})
    data = json.loads((site.root / "plan.json").read_text())
    assert is_three_arm(site.plan) and ARM_NOISE in {arm.label for arm in site.plan.arms}, f"{site.plan.arms=}"
    without_prompt = load_plan({**data, "arms": [arm for arm in data["arms"] if arm["label"] != ARM_PROMPT]})
    assert not is_three_arm(without_prompt), f"{without_prompt.arms=}"


def test_T70_a_plan_without_the_three_labels_reports_as_before(tmp_path, monkeypatch, capsys):
    cells = {Cell("C", "stop-server"): CellShape(20, 17), Cell("C2", "stop-server"): CellShape(20, 16), Cell("B", "stop-server"): CellShape(20, 0)}
    site_with_state(tmp_path, FULL_ROLES, (cells, PlanState.ANALYZED))
    monkeypatch.chdir(tmp_path)
    _, out, _ = arm_report_of(capsys)
    assert "## Q2 Effect" in out and "## Three-arm verdict" not in out, f"got {out!r}"


@pytest.mark.parametrize(
    ("lines", "expected"),
    [
        ([], None),
        (['{"type": "result", "num_turns": 7}'], 7),
        (['{"type": "result", "num_turns": 7}', '{"type": "result", "num_turns": 9}'], 9),
        (['{"type": "assistant", "num_turns": 7}'], None),
        (['{"type": "result", "num_turns": true}'], None),
        (['{"type": "result", "num_turns": "7"}'], None),
        (["not json"], None),
    ],
)
def test_T70_turns_come_from_the_last_result_line(lines, expected):
    assert turns_of(lines) == expected, f"{lines=} {expected=}"


def test_T70_the_smallest_drop_is_the_smallest_change_that_gives_a_verdict():
    drop = smallest_detectable_drop(Counts(12, 20), 20)
    assert drop == pytest.approx(0.35), f"{drop=}"


def test_T70_no_drop_is_detectable_when_the_other_arm_is_already_clean():
    assert smallest_detectable_drop(Counts(0, 20), 20) is None, "an arm with no violations cannot show a drop"
    assert "no drop is detectable" in detectable_text(Counts(0, 20), 20), "the text must say no drop is detectable"


def test_T70_fewer_runs_need_a_larger_drop():
    few = smallest_detectable_drop(Counts(12, 20), 10)
    many = smallest_detectable_drop(Counts(12, 20), 40)
    assert few > many, f"{few=} {many=}"


def test_T70_an_arm_with_no_runs_says_so():
    assert arm_cost_turns_line(ARM_PROMPT, ()) == "- Arm P: no usable runs.", "an empty arm must say it has no runs"


def test_T70_five_runs_per_arm_are_enough_to_measure_the_smallest_drop():
    assert "not measurable" not in detectable_text(Counts(4, 5), 5), "MIN_RUNS runs per arm are measurable"
    assert "not measurable" in detectable_text(Counts(4, 5), 4), "fewer than MIN_RUNS runs are not measurable"
