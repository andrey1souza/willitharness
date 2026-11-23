import subprocess
from pathlib import Path

import pytest
from cli_runner import run_cli
from three_arm_site import ArmShape, SiteOptions, first, three_arm_site

from willitharness.component_arms import ARM_COMPONENT, ARM_NOTHING, ARM_PLACEBO, ARM_PROMPT
from willitharness.three_arm_report import arm_cost_turns_line, has_placebo

REPOSITORY = Path(__file__).resolve().parents[2]
DEMO_PLAN = "tests/golden/demo-placebo-plan"
GOLDEN = REPOSITORY / "tests" / "golden" / "demo-placebo-report.md"
THREE_ARM_GOLDEN = REPOSITORY / "tests" / "golden" / "demo-three-arm-report.md"
EXIT_OK = 0
RUNS = 20
WITH_PLACEBO = SiteOptions(placebo=True)
CONTENT_HEADING = "## Content against filler"
ADDED_TEXT = {ARM_COMPONENT: ArmShape(RUNS, first(3)), ARM_PROMPT: ArmShape(RUNS, first(3)), ARM_NOTHING: ArmShape(RUNS, first(14)), ARM_PLACEBO: ArmShape(RUNS, first(3))}
ADDED_TEXT_LINE = "content stop-server C against PL: added text helps and the content does not (arm C 3 of 20 runs, arm PL 3 of 20 runs, arm N 14 of 20 runs)"
CONTENT_WINS = {**ADDED_TEXT, ARM_COMPONENT: ArmShape(RUNS, first(2)), ARM_PLACEBO: ArmShape(RUNS, first(12)), ARM_NOTHING: ArmShape(RUNS, first(12))}
FILLER_WINS = {**ADDED_TEXT, ARM_COMPONENT: ArmShape(RUNS, first(14)), ARM_PLACEBO: ArmShape(RUNS, first(3)), ARM_NOTHING: ArmShape(RUNS, first(14))}
NOTHING_HELPS = {arm: ArmShape(RUNS, first(10)) for arm in ADDED_TEXT}
ONLY_C_BEATS_NOTHING = {**ADDED_TEXT, ARM_COMPONENT: ArmShape(RUNS), ARM_PLACEBO: ArmShape(RUNS, first(3)), ARM_NOTHING: ArmShape(RUNS, first(8))}
PLACEBO_WITHOUT_RUNS = {arm: shape for arm, shape in ADDED_TEXT.items() if arm != ARM_PLACEBO}
KEEP_SHAPES = {ARM_COMPONENT: ArmShape(RUNS, frozenset({1, 18}), first(16)), ARM_PROMPT: ArmShape(RUNS, first(11)), ARM_NOTHING: ArmShape(RUNS, first(12))}


def placebo_site_in(tmp_path, monkeypatch, shapes, options):
    three_arm_site(tmp_path, shapes, options)
    monkeypatch.chdir(tmp_path)


def placebo_section_of(text, heading):
    assert heading in text, f"the report has no {heading!r}: {text!r}"
    return text.split(heading, 1)[1].split("\n## ", 1)[0]


def placebo_report_of(capsys):
    return run_cli(capsys, ["report", "plan.json"])


def demo_golden_text(path):
    text = path.read_text()
    assert text.startswith("# Report"), f"{path} starts with {text[:20]!r}. Fix: restore the golden file."
    return text


def placebo_diff_exit_code(text, golden_path):
    return subprocess.run(["diff", "-", str(golden_path)], input=text, capture_output=True, text=True).returncode


def test_PB6_the_placebo_demo_report_equals_the_golden_file(monkeypatch, capsys):
    monkeypatch.chdir(REPOSITORY)
    code, out, err = run_cli(capsys, ["report", DEMO_PLAN])
    assert code == EXIT_OK and err == "", f"got {code} {out!r} {err!r}"
    assert out == demo_golden_text(GOLDEN), "the report differs from tests/golden/demo-placebo-report.md. Fix: change the code back, or regenerate the golden file on purpose."
    assert placebo_diff_exit_code(out, GOLDEN) == EXIT_OK, "diff found a difference"


def test_PB9_the_placebo_golden_file_differs_from_the_three_arm_golden_file():
    assert demo_golden_text(GOLDEN) != demo_golden_text(THREE_ARM_GOLDEN), f"{GOLDEN.name} equals {THREE_ARM_GOLDEN.name}. Rule: the placebo demo adds a section to the three-arm report. Fix: regenerate the placebo golden file."


@pytest.mark.parametrize(
    ("shapes", "sentence"),
    [
        (ADDED_TEXT, "added text helps and the content does not"),
        (CONTENT_WINS, "the content helps beyond added text"),
        (FILLER_WINS, "filler text beats the content"),
        (NOTHING_HELPS, "neither the content nor added text helps"),
        (ONLY_C_BEATS_NOTHING, "unclear: only one of the content and the filler text beats arm N"),
        (PLACEBO_WITHOUT_RUNS, "inconclusive: an arm has too few runs"),
    ],
)
def test_PB4_to_PB8_the_report_says_what_the_comparison_shows(tmp_path, monkeypatch, capsys, shapes, sentence):
    placebo_site_in(tmp_path, monkeypatch, shapes, WITH_PLACEBO)
    _, out, _ = placebo_report_of(capsys)
    assert f"Verdict: {sentence}" in placebo_section_of(out, CONTENT_HEADING), f"got {out!r}"


def test_PB6_the_report_counts_the_three_arms_of_the_comparison(tmp_path, monkeypatch, capsys):
    placebo_site_in(tmp_path, monkeypatch, CONTENT_WINS, WITH_PLACEBO)
    _, out, _ = placebo_report_of(capsys)
    assert "stop-server: arm C 2 of 20 runs, arm PL 12 of 20 runs, arm N 12 of 20 runs." in placebo_section_of(out, CONTENT_HEADING), f"got {out!r}"


def test_PB6_the_decide_command_prints_the_content_line_after_the_three_arm_line(tmp_path, monkeypatch, capsys):
    placebo_site_in(tmp_path, monkeypatch, ADDED_TEXT, WITH_PLACEBO)
    code, out, err = run_cli(capsys, ["decide", "plan.json"])
    lines = out.splitlines()
    assert code == EXIT_OK and len(lines) == 2 and lines[0].startswith("decision stop-server C: "), f"got {code} {out!r} {err!r}"
    assert lines[1] == ADDED_TEXT_LINE, f"got {lines[1]!r}"


def test_PB3_a_clean_arm_n_gives_no_room_in_the_report(tmp_path, monkeypatch, capsys):
    shapes = {**ADDED_TEXT, ARM_NOTHING: ArmShape(RUNS), ARM_COMPONENT: ArmShape(RUNS), ARM_PLACEBO: ArmShape(RUNS, first(10))}
    placebo_site_in(tmp_path, monkeypatch, shapes, WITH_PLACEBO)
    _, out, _ = placebo_report_of(capsys)
    assert "Verdict: no room to help: arm N shows almost no violations. This is a policy choice, not a measurement." in placebo_section_of(out, CONTENT_HEADING), f"got {out!r}"


def test_PB6_turns_and_cost_are_shown_for_arm_pl(tmp_path, monkeypatch, capsys):
    placebo_site_in(tmp_path, monkeypatch, ADDED_TEXT, WITH_PLACEBO)
    _, out, _ = placebo_report_of(capsys)
    shown = placebo_section_of(out, "## Turns and cost per arm")
    assert "Arm PL: 20 runs, mean cost $0.0100, mean turns 3.0 over 20 runs." in shown, f"got {shown!r}"
    assert all(f"Arm {arm}: " in shown for arm in (ARM_COMPONENT, ARM_PROMPT, ARM_NOTHING)), f"got {shown!r}"


def test_PB6_arm_pl_with_no_usable_runs_says_so():
    assert arm_cost_turns_line(ARM_PLACEBO, ()) == "- Arm PL: no usable runs.", "a missing arm must be stated"


def test_PB9_a_plan_without_arm_pl_has_no_content_section_and_no_content_line(tmp_path, monkeypatch, capsys):
    placebo_site_in(tmp_path, monkeypatch, KEEP_SHAPES, SiteOptions())
    _, report, _ = placebo_report_of(capsys)
    _, decided, _ = run_cli(capsys, ["decide", "plan.json"])
    assert CONTENT_HEADING not in report and "Arm PL" not in report and "content " not in decided, f"got {report!r} {decided!r}"
    assert len(decided.splitlines()) == 1, f"got {decided!r}"


def test_PB9_a_plan_is_a_placebo_plan_by_its_label(tmp_path):
    with_arm = three_arm_site(tmp_path / "with", {}, WITH_PLACEBO)
    without = three_arm_site(tmp_path / "without", {})
    assert has_placebo(with_arm.plan) and not has_placebo(without.plan), f"{with_arm.plan.arms=} {without.plan.arms=}"
