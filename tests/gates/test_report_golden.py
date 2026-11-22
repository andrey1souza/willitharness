import re
import subprocess
from dataclasses import dataclass, replace
from pathlib import Path

import pytest
from analysis_site import FULL_ROLES, NO_PAIR_ROLES, CellShape, site_with_state
from cli_runner import run_cli

from willitharness import report
from willitharness.lifecycle import PlanState
from willitharness.store import Cell

REPOSITORY = Path(__file__).resolve().parents[2]
DEMO_PLAN = "tests/golden/demo-plan"
GOLDEN = REPOSITORY / "tests" / "golden" / "demo-report.md"
REPORT = ["report", DEMO_PLAN]
EXIT_OK = 0
EXIT_REFUSED = 1
STOP = "stop-server"
SECTIONS = ("## Q1 Reachability", "## Q2 Effect", "## Q3 Guard", "## Q4 Side effects", "## Decision", "## Warnings", "## Limits")
NO_VERDICTS = "no verdicts yet; run: willitharness analyze"
ABORTED = "plan aborted; no verdict"
LOWERS = {Cell("C", STOP): CellShape(20, 17), Cell("C2", STOP): CellShape(20, 16), Cell("B", STOP): CellShape(20, 0)}
SATURATED_NO_EFFECT = {Cell("C", STOP): CellShape(20, 0), Cell("C2", STOP): CellShape(20, 0), Cell("B", STOP): CellShape(20, 0)}
RAISES = {**LOWERS, Cell("C", STOP): CellShape(20, 1), Cell("C2", STOP): CellShape(20, 2), Cell("B", STOP): CellShape(20, 18)}
NOISY = {**LOWERS, Cell("C2", STOP): CellShape(20, 1)}
THIN_NOISE = {**LOWERS, Cell("C2", STOP): CellShape(3, 2)}
SENTENCE_BREAK = re.compile(r"(?<=[.!?])\s+|\n")
MAX_SENTENCE_WORDS = 20
MIN_SHORT_SHARE = 0.8


@dataclass(frozen=True)
class Scenario:
    roles: dict
    cells: dict
    state: PlanState = PlanState.ANALYZED


def golden_text():
    text = GOLDEN.read_text()
    assert text.startswith("# Report"), f"the golden file starts with {text[:20]!r}. Fix: restore tests/golden/demo-report.md."
    return text


def scenario_report(tmp_path, monkeypatch, capsys, scenario):
    site_with_state(tmp_path, scenario.roles, (scenario.cells, scenario.state))
    monkeypatch.chdir(tmp_path)
    return run_cli(capsys, ["report", "plan.json"])


def demo_report(monkeypatch, capsys):
    monkeypatch.chdir(REPOSITORY)
    code, out, err = run_cli(capsys, REPORT)
    assert code == EXIT_OK and err == "", f"got {code} {out!r} {err!r}"
    return out


def section_of(text, heading):
    assert heading in text, f"the report has no {heading!r}: {text!r}"
    return text.split(heading, 1)[1].split("\n## ", 1)[0]


def diff_exit_code(text, golden_path):
    result = subprocess.run(["diff", "-", str(golden_path)], input=text, capture_output=True, text=True)
    return result.returncode


def test_G6_2_the_demo_plan_report_equals_the_golden_file(monkeypatch, capsys):
    text = demo_report(monkeypatch, capsys)
    assert text == golden_text(), "the report differs from tests/golden/demo-report.md. Fix: change the code back, or regenerate the golden file on purpose."
    assert diff_exit_code(text, GOLDEN) == EXIT_OK, "diff found a difference between the report and the golden file"


def test_G6_2_an_edited_golden_file_makes_diff_exit_one(monkeypatch, capsys, tmp_path):
    text = demo_report(monkeypatch, capsys)
    edited = tmp_path / "edited.md"
    edited.write_text(golden_text().replace("Keep", "Delete", 1))
    assert edited.read_text() != golden_text(), "the edit changed nothing. Fix: edit text the golden file holds."
    assert diff_exit_code(text, edited) == EXIT_REFUSED, "diff accepted an edited golden file"


def test_G6_2_the_report_is_the_same_on_a_second_run(monkeypatch, capsys):
    assert demo_report(monkeypatch, capsys) == demo_report(monkeypatch, capsys), "two runs on the same plan data gave different reports"


def test_G6_2_the_report_has_every_section_and_each_states_its_value(monkeypatch, capsys):
    text = demo_report(monkeypatch, capsys)
    assert all(heading in text for heading in SECTIONS), f"a section is missing in {text!r}"
    assert "Arm B: Loaded." in section_of(text, "## Q1 Reachability"), f"Q1 lacks the reach value in {text!r}"
    assert "RuleLowersViolations" in section_of(text, "## Q2 Effect"), f"Q2 lacks the effect value in {text!r}"
    assert "GuardUntested" in section_of(text, "## Q3 Guard"), f"Q3 lacks the guard value in {text!r}"
    assert "git -C: B 4 of 8 runs, C 0 of 8 runs" in section_of(text, "## Q4 Side effects"), f"Q4 lacks the counts of the side-effect command in {text!r}"
    assert "Keep" in section_of(text, "## Decision"), f"the Decision section lacks the decision in {text!r}"


def test_G6_2_the_report_states_the_counts_the_model_the_cells_and_the_cost(monkeypatch, capsys):
    text = demo_report(monkeypatch, capsys)
    assert "attempts, not executed commands" in text, f"the report does not say what the counts mean in {text!r}"
    assert "model fake-model-1" in text, f"the report does not name the model in {text!r}"
    assert "- arm B, task stop-server: 8" in section_of(text, "## Usable runs per cell"), f"the report lacks the usable runs of a cell in {text!r}"
    assert "Total cost: $0.24." in text, f"the report lacks the total cost in {text!r}"
    assert "W-LOWN: arm B, task stop-server has 8 usable runs" in section_of(text, "## Warnings"), f"the report lacks the low-n warning in {text!r}"


def test_G6_2_the_limits_section_lists_the_three_limits(monkeypatch, capsys):
    limits = section_of(demo_report(monkeypatch, capsys), "## Limits")
    missing = [phrase for phrase in ("one model", "tasks written by the plan author", "the isolation flags used") if phrase not in limits]
    assert missing == [], f"the Limits section lacks {missing}"


def test_G6_2_at_least_eighty_percent_of_the_sentences_have_twenty_words_or_fewer():
    sentences = [part for part in SENTENCE_BREAK.split(golden_text()) if part.strip()]
    short = [sentence for sentence in sentences if len(sentence.split()) <= MAX_SENTENCE_WORDS]
    assert len(short) / len(sentences) >= MIN_SHORT_SHARE, f"only {len(short)} of {len(sentences)} sentences have {MAX_SENTENCE_WORDS} words or fewer"


def test_G6_2_a_plan_that_has_not_been_analyzed_is_refused(tmp_path, monkeypatch, capsys):
    code, out, err = scenario_report(tmp_path, monkeypatch, capsys, Scenario(FULL_ROLES, LOWERS, PlanState.COMPLETE))
    assert code == EXIT_REFUSED and out == "" and err.strip() == NO_VERDICTS, f"got {code} {out!r} {err!r}"


def test_G6_2_an_aborted_plan_is_refused(tmp_path, monkeypatch, capsys):
    code, out, err = scenario_report(tmp_path, monkeypatch, capsys, Scenario(FULL_ROLES, LOWERS, PlanState.ABORTED))
    assert code == EXIT_REFUSED and out == "" and err.strip() == ABORTED, f"got {code} {out!r} {err!r}"


def test_G6_2_a_plan_file_gives_the_same_decision_as_a_plan_folder(tmp_path, monkeypatch, capsys):
    code, out, err = scenario_report(tmp_path, monkeypatch, capsys, Scenario(FULL_ROLES, LOWERS))
    assert code == EXIT_OK and err == "", f"got {code} {out!r} {err!r}"
    assert "decision stop-server B: Keep (reach Loaded, effect RuleLowersViolations, guard GuardUntested); saturated: false" in out, f"got {out!r}"
    assert report.NO_TRANSCRIPTS_LINE in section_of(out, "## Q4 Side effects"), f"a plan with no stored transcripts must say side effects were not measured, got {out!r}"


def test_G6_2_a_folder_outside_the_project_is_refused_naming_it(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    code, out, err = run_cli(capsys, ["report", str(REPOSITORY)])
    assert code == EXIT_REFUSED and out == "" and str(REPOSITORY.resolve()) in err, f"got {code} {out!r} {err!r}"


@pytest.mark.parametrize(
    "cells, text",
    [
        (NOISY, "the two identical arms differed; do not trust this comparison"),
        (THIN_NOISE, "the noise pair has fewer than 5 usable runs on one side"),
    ],
)
def test_G6_2_a_noise_problem_is_explained_in_q2_and_the_decision_is_cannot_decide(tmp_path, monkeypatch, capsys, cells, text):
    code, out, err = scenario_report(tmp_path, monkeypatch, capsys, Scenario(FULL_ROLES, cells))
    assert code == EXIT_OK, f"got {code} {out!r} {err!r}"
    assert text in section_of(out, "## Q2 Effect"), f"Q2 lacks {text!r}: {out!r}"
    assert "CannotDecide" in section_of(out, "## Decision"), f"got {out!r}"


def test_G6_2_a_delete_candidate_carries_its_caveat_and_the_saturated_flag(tmp_path, monkeypatch, capsys):
    code, out, err = scenario_report(tmp_path, monkeypatch, capsys, Scenario(FULL_ROLES, SATURATED_NO_EFFECT))
    decision = section_of(out, "## Decision")
    assert code == EXIT_OK and "DeleteCandidate" in decision and "NoMeasurableEffect" in decision, f"got {code} {out!r} {err!r}"
    assert "not measurable at this n" in decision and "saturated: true" in decision, f"got {decision!r}"


def test_G6_2_a_delete_candidate_from_a_raised_rate_has_no_measurability_caveat(tmp_path, monkeypatch, capsys):
    code, out, err = scenario_report(tmp_path, monkeypatch, capsys, Scenario(FULL_ROLES, RAISES))
    decision = section_of(out, "## Decision")
    assert code == EXIT_OK and "DeleteCandidate" in decision and "RuleRaisesViolations" in decision, f"got {code} {out!r} {err!r}"
    assert "not measurable at this n" not in decision, f"the caveat belongs to NoMeasurableEffect only, got {decision!r}"


def test_G6_2_a_plan_with_a_guard_arm_is_refused_with_rule_and_fix(tmp_path, monkeypatch, capsys):
    code, out, err = scenario_report(tmp_path, monkeypatch, capsys, Scenario({**FULL_ROLES, "G": "guard_only"}, LOWERS))
    assert code == EXIT_REFUSED and out == "", f"got {code} {out!r} {err!r}"
    assert "plan demo has a guard_only arm" in err and "Rule:" in err and "Fix:" in err, f"got {err!r}"


def test_G6_2_a_missing_plan_file_is_refused_naming_the_file(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    code, out, err = run_cli(capsys, ["report", "absent.json"])
    assert code == EXIT_REFUSED and out == "" and "absent.json" in err, f"got {code} {out!r} {err!r}"


def test_G6_2_a_plan_with_no_noise_pair_is_explained_in_q2(tmp_path, monkeypatch, capsys):
    cells = {cell: shape for cell, shape in LOWERS.items() if cell.arm != "C2"}
    code, out, err = scenario_report(tmp_path, monkeypatch, capsys, Scenario(NO_PAIR_ROLES, cells))
    assert code == EXIT_OK and "no noise pair" in section_of(out, "## Q2 Effect"), f"got {code} {out!r} {err!r}"


def test_S2_the_decision_section_is_the_same_whatever_the_side_effect_report_says(tmp_path, monkeypatch, capsys):
    site = site_with_state(tmp_path, FULL_ROLES, (LOWERS, PlanState.ANALYZED))
    data = report.report_input(site.root, site.plan)
    busy = replace(data, side_effects=("git -C: B 22 of 60 runs, C 1 of 60 runs", "Write: B 3 of 60 runs, C 0 of 60 runs", "rm -r: B 9 of 60 runs, C 0 of 60 runs"))
    empty = replace(data, side_effects=(report.NO_TRANSCRIPTS_LINE,))
    assert section_of(report.report_text(busy), "## Decision") == section_of(report.report_text(empty), "## Decision"), f"a side-effect report changed the Decision section: {busy.side_effects!r} against {empty.side_effects!r}"
    assert report.report_text(busy) != report.report_text(empty), f"the side-effect lines never reached the report: {busy.side_effects!r} against {empty.side_effects!r}"


def test_G6_2_q2_shows_the_noise_of_each_outcome_on_its_own_line(tmp_path, monkeypatch, capsys):
    code, out, err = scenario_report(tmp_path, monkeypatch, capsys, Scenario(FULL_ROLES, NOISY))
    effect = section_of(out, "## Q2 Effect")
    assert code == EXIT_OK and "Noise: NoiseFloorTooHigh." in effect and "Noise on completed runs: NoiseOk." in effect, f"got {code} {effect!r} {err!r}"
