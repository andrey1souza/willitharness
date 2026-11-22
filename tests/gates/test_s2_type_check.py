import itertools
import runpy
from pathlib import Path

import pytest
import s2_type_check
from guard_site import bash

from willitharness.decision import decide
from willitharness.side_effects import side_effect_report_lines
from willitharness.vocabulary import EffectResult, GuardResult, Reach

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "gates" / "s2_type_check.py"
PASS_LINE = "decision parameters are exactly: reach, effect, guard"
ALL_INPUTS = list(itertools.product(Reach, EffectResult, GuardResult))
EXPECTED_INPUT_COUNT = 45
LISTED_COMMAND_RUNS = ((bash("git -C repo status"),),) * 3


def decide_with_side_effects(reach, effect, guard, side_effects=None):
    assert side_effects is None or side_effects, "the mutant takes a side-effect report"
    return decide(reach, effect, guard)


def test_S2_the_real_decision_passes_with_the_exact_parameter_line(capsys):
    code = s2_type_check.main()
    assert (code, capsys.readouterr().out.strip()) == (0, PASS_LINE), "the real decision must pass"


def test_S2_the_script_run_as_main_exits_zero(capsys):
    with pytest.raises(SystemExit) as exit_request:
        runpy.run_path(str(SCRIPT), run_name="__main__")
    output = capsys.readouterr().out.strip()
    assert (exit_request.value.code, output) == (0, PASS_LINE), f"got {exit_request.value.code}: {output!r}"


def test_S2_a_decision_with_a_side_effects_parameter_exits_one(capsys):
    code = s2_type_check.exit_code_of(decide_with_side_effects)
    output = capsys.readouterr().out
    assert code == 1, f"a mutant with side_effects must exit 1, got {code}"
    assert "side_effects" in output and "S2" in output and "Fix:" in output, f"the failure must name the value, the rule and a fix: {output!r}"


def test_S2_a_missing_parameter_exits_one(capsys):
    assert s2_type_check.exit_code_of(lambda reach, effect: None) == 1, "a decision with fewer parameters must exit 1"
    output = capsys.readouterr().out
    assert "reach, effect," in output, f"the failure must name the parameters found, got {output!r}"


def test_S2_a_reordered_parameter_list_exits_one(capsys):
    assert s2_type_check.exit_code_of(lambda effect, reach, guard: None) == 1, "the order is part of the signature"
    output = capsys.readouterr().out
    assert "effect, reach, guard" in output, f"the failure must name the parameters found, got {output!r}"


def test_S2_the_decision_is_the_same_with_or_without_a_side_effect_report():
    assert len(ALL_INPUTS) == EXPECTED_INPUT_COUNT, f"got {len(ALL_INPUTS)} inputs"
    without_report = {inputs: decide(*inputs) for inputs in ALL_INPUTS}
    report = side_effect_report_lines({"B": LISTED_COMMAND_RUNS, "C": ((bash("ls"),),) * 3})
    assert report, "the side-effect report is empty"
    with_report = {inputs: decide(*inputs) for inputs in ALL_INPUTS}
    assert with_report == without_report, "building a side-effect report changed a decision"


@pytest.mark.parametrize(("reach", "effect", "guard"), ALL_INPUTS)
def test_S2_the_decision_refuses_a_side_effect_report_as_input(reach, effect, guard):
    with pytest.raises(TypeError, match="positional") as refusal:
        decide(reach, effect, guard, ["git -C: B 22 of 60 runs"])
    assert "4 were given" in str(refusal.value), f"decide must refuse the fourth argument, got {refusal.value}"
