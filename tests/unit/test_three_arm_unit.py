import itertools

import pytest

from willitharness.counts import Counts
from willitharness.three_arm import (
    INSURANCE_MAX_RATE,
    INSURANCE_TEXT,
    arm_verdict_from,
    arm_verdict_text,
    nothing_is_clean,
    three_arm_verdict,
)
from willitharness.vocabulary import ArmVerdict, Verdict

INPUT_COUNT = 32
RUNS = 20
ALL_INPUTS = list(itertools.product(Verdict, Verdict, [False, True]))
SMALL_N_INPUTS = [row for row in ALL_INPUTS if Verdict.INCONCLUSIVE_SMALL_N in row[:2]]


def counts(violations):
    return Counts(violations, RUNS)


@pytest.mark.parametrize(
    ("component", "prompt", "nothing", "expected"),
    [
        pytest.param(2, 12, 12, ArmVerdict.KEEP_COMPONENT, id="C-beats-P"),
        pytest.param(3, 3, 14, ArmVerdict.REPLACE_WITH_PROMPT, id="C-equals-P-and-beats-N"),
        pytest.param(10, 10, 10, ArmVerdict.DELETE_CANDIDATE, id="C-equals-N"),
        pytest.param(0, 10, 0, ArmVerdict.INSURANCE_KEEP, id="N-almost-clean"),
        pytest.param(10, 10, 0, ArmVerdict.INSURANCE_KEEP, id="N-clean-and-C-not"),
        pytest.param(0, 0, 10, ArmVerdict.REPLACE_WITH_PROMPT, id="C-clean-and-N-not"),
        pytest.param(14, 3, 10, ArmVerdict.INCONCLUSIVE, id="C-worse-than-P"),
        pytest.param(14, 14, 3, ArmVerdict.INCONCLUSIVE, id="C-worse-than-N"),
    ],
)
def test_TA4_to_TA7_real_counts_give_one_verdict(component, prompt, nothing, expected):
    result = three_arm_verdict(counts(component), counts(prompt), counts(nothing))
    assert result is expected, f"{result=} expected {expected=} for C={component} P={prompt} N={nothing}"


def test_TA2_a_small_arm_gives_inconclusive_even_when_the_others_are_clear():
    result = three_arm_verdict(Counts(0, 3), counts(15), counts(15))
    assert result is ArmVerdict.INCONCLUSIVE, f"{result=} for a component arm with 3 runs"


def test_TA2_an_arm_with_no_runs_gives_inconclusive():
    result = three_arm_verdict(counts(2), counts(12), Counts(0, 0))
    assert result is ArmVerdict.INCONCLUSIVE, f"{result=} for an arm N with no runs"


@pytest.mark.parametrize(("prompt", "nothing", "clean"), SMALL_N_INPUTS)
def test_TA2_small_n_always_gives_inconclusive(prompt, nothing, clean):
    result = arm_verdict_from(prompt, nothing, clean)
    assert result is ArmVerdict.INCONCLUSIVE, f"{result=} for {prompt=} {nothing=} {clean=}"


def test_TA3_the_threshold_run_is_clean_and_the_next_is_not():
    at_threshold = nothing_is_clean(counts(1))
    above_threshold = nothing_is_clean(counts(2))
    assert (at_threshold, above_threshold) == (True, False), f"{at_threshold=} {above_threshold=} with {INSURANCE_MAX_RATE=}"


def test_TA3_an_arm_with_no_runs_is_not_clean():
    assert nothing_is_clean(Counts(0, 0)) is False, "an arm with no runs cannot show almost no violations"


def test_TA3_insurance_text_names_a_policy_choice():
    text = arm_verdict_text(ArmVerdict.INSURANCE_KEEP)
    assert text == INSURANCE_TEXT and "policy choice" in text and "not a measurement" in text, f"{text=}"


def test_TA3_other_verdicts_print_their_name():
    texts = {verdict: arm_verdict_text(verdict) for verdict in ArmVerdict if verdict is not ArmVerdict.INSURANCE_KEEP}
    assert texts == {verdict: verdict.value for verdict in texts}, f"{texts=}"


@pytest.mark.parametrize(("prompt", "nothing"), list(itertools.product(Verdict, Verdict)))
def test_TA3_clean_without_small_n_always_gives_insurance(prompt, nothing):
    result = arm_verdict_from(prompt, nothing, True)
    expected = ArmVerdict.INCONCLUSIVE if Verdict.INCONCLUSIVE_SMALL_N in (prompt, nothing) else ArmVerdict.INSURANCE_KEEP
    assert result is expected, f"{result=} expected {expected=} for {prompt=} {nothing=}"


@pytest.mark.parametrize("nothing", [Verdict.FIRST_HIGHER, Verdict.FIRST_LOWER, Verdict.INCONCLUSIVE])
def test_TA4_component_beating_the_prompt_is_kept(nothing):
    result = arm_verdict_from(Verdict.FIRST_HIGHER, nothing, False)
    assert result is ArmVerdict.KEEP_COMPONENT, f"{result=} for {nothing=}"


def test_TA5_equal_to_the_prompt_and_beating_nothing_is_replaced():
    result = arm_verdict_from(Verdict.INCONCLUSIVE, Verdict.FIRST_HIGHER, False)
    assert result is ArmVerdict.REPLACE_WITH_PROMPT, f"{result=}"


def test_TA6_equal_to_nothing_is_a_delete_candidate():
    result = arm_verdict_from(Verdict.INCONCLUSIVE, Verdict.INCONCLUSIVE, False)
    assert result is ArmVerdict.DELETE_CANDIDATE, f"{result=}"


@pytest.mark.parametrize(
    ("prompt", "nothing"),
    [
        (Verdict.FIRST_LOWER, Verdict.FIRST_HIGHER),
        (Verdict.FIRST_LOWER, Verdict.FIRST_LOWER),
        (Verdict.FIRST_LOWER, Verdict.INCONCLUSIVE),
        (Verdict.INCONCLUSIVE, Verdict.FIRST_LOWER),
    ],
)
def test_TA7_the_unnamed_inputs_give_inconclusive(prompt, nothing):
    result = arm_verdict_from(prompt, nothing, False)
    assert result is ArmVerdict.INCONCLUSIVE, f"{result=} for {prompt=} {nothing=}"


def test_TA1_there_are_thirty_two_inputs_and_each_gives_one_stable_verdict():
    first = [arm_verdict_from(*row) for row in ALL_INPUTS]
    second = [arm_verdict_from(*row) for row in ALL_INPUTS]
    assert len(ALL_INPUTS) == INPUT_COUNT, f"{len(ALL_INPUTS)=} expected {INPUT_COUNT}"
    assert first == second and all(result in ArmVerdict for result in first), f"{first=} {second=}"


def test_TA1_the_same_counts_twice_give_the_same_verdict():
    arms = (counts(3), counts(3), counts(14))
    assert three_arm_verdict(*arms) is three_arm_verdict(*arms), f"two calls differ for {arms=}"


def test_TA1_every_verdict_value_is_reachable():
    reached = {arm_verdict_from(*row) for row in ALL_INPUTS}
    assert reached == set(ArmVerdict), f"{reached=}"

