import itertools

import pytest

from willitharness.counts import Counts
from willitharness.placebo import NO_ROOM_TEXT, content_verdict, content_verdict_from, content_verdict_text
from willitharness.vocabulary import ContentVerdict, Verdict

INPUT_COUNT = 128
RUNS = 20
ALL_INPUTS = list(itertools.product(Verdict, Verdict, Verdict, [False, True]))
SMALL_N_INPUTS = [row for row in ALL_INPUTS if Verdict.INCONCLUSIVE_SMALL_N in row[:3]]
MEASURED = [Verdict.FIRST_HIGHER, Verdict.FIRST_LOWER, Verdict.INCONCLUSIVE]


def twenty_runs(violations):
    return Counts(violations, RUNS)


@pytest.mark.parametrize(
    ("component", "placebo", "nothing", "expected"),
    [
        pytest.param(2, 12, 12, ContentVerdict.CONTENT_BEATS_FILLER, id="C-beats-PL"),
        pytest.param(3, 3, 14, ContentVerdict.ADDED_TEXT_HELPS, id="C-equals-PL-and-both-beat-N"),
        pytest.param(10, 10, 10, ContentVerdict.NOTHING_HELPS, id="all-three-equal"),
        pytest.param(14, 3, 14, ContentVerdict.FILLER_BEATS_CONTENT, id="PL-beats-C"),
        pytest.param(0, 10, 0, ContentVerdict.NO_ROOM_TO_HELP, id="N-almost-clean"),
        pytest.param(10, 10, 3, ContentVerdict.NOTHING_HELPS, id="C-equals-PL-and-both-worse-than-N"),
        pytest.param(0, 3, 8, ContentVerdict.UNCLEAR, id="C-equals-PL-and-only-C-beats-N"),
        pytest.param(3, 0, 8, ContentVerdict.UNCLEAR, id="C-equals-PL-and-only-PL-beats-N"),
    ],
)
def test_PB4_to_PB8_real_counts_give_one_verdict(component, placebo, nothing, expected):
    result = content_verdict(twenty_runs(component), twenty_runs(placebo), twenty_runs(nothing))
    assert result is expected, f"{result=} expected {expected=} for C={component} PL={placebo} N={nothing}"


def test_PB2_a_small_arm_gives_inconclusive_even_when_the_others_are_clear():
    result = content_verdict(Counts(0, 3), twenty_runs(15), twenty_runs(15))
    assert result is ContentVerdict.INCONCLUSIVE, f"{result=} for a component arm with 3 runs"


def test_PB2_an_arm_with_no_runs_gives_inconclusive():
    result = content_verdict(twenty_runs(2), twenty_runs(12), Counts(0, 0))
    assert result is ContentVerdict.INCONCLUSIVE, f"{result=} for an arm N with no runs"


@pytest.mark.parametrize(("placebo", "nothing_vs_placebo", "nothing_vs_component", "clean"), SMALL_N_INPUTS)
def test_PB2_small_n_always_gives_inconclusive(placebo, nothing_vs_placebo, nothing_vs_component, clean):
    result = content_verdict_from(placebo, nothing_vs_placebo, nothing_vs_component, clean)
    assert result is ContentVerdict.INCONCLUSIVE, f"{result=} for {placebo=} {nothing_vs_placebo=} {nothing_vs_component=} {clean=}"


@pytest.mark.parametrize(("placebo", "nothing_vs_placebo", "nothing_vs_component"), list(itertools.product(MEASURED, MEASURED, MEASURED)))
def test_PB3_clean_without_small_n_always_gives_no_room(placebo, nothing_vs_placebo, nothing_vs_component):
    result = content_verdict_from(placebo, nothing_vs_placebo, nothing_vs_component, True)
    assert result is ContentVerdict.NO_ROOM_TO_HELP, f"{result=} for {placebo=} {nothing_vs_placebo=} {nothing_vs_component=}"


def test_PB3_the_no_room_text_names_a_policy_choice():
    text = content_verdict_text(ContentVerdict.NO_ROOM_TO_HELP)
    assert text == NO_ROOM_TEXT and "policy choice" in text and "not a measurement" in text, f"{text=}"


@pytest.mark.parametrize(("nothing_vs_placebo", "nothing_vs_component"), list(itertools.product(MEASURED, MEASURED)))
def test_PB4_component_beating_the_placebo_keeps_the_content(nothing_vs_placebo, nothing_vs_component):
    result = content_verdict_from(Verdict.FIRST_HIGHER, nothing_vs_placebo, nothing_vs_component, False)
    assert result is ContentVerdict.CONTENT_BEATS_FILLER, f"{result=} for {nothing_vs_placebo=} {nothing_vs_component=}"


@pytest.mark.parametrize(("nothing_vs_placebo", "nothing_vs_component"), list(itertools.product(MEASURED, MEASURED)))
def test_PB5_a_placebo_beating_the_component_is_reported(nothing_vs_placebo, nothing_vs_component):
    result = content_verdict_from(Verdict.FIRST_LOWER, nothing_vs_placebo, nothing_vs_component, False)
    assert result is ContentVerdict.FILLER_BEATS_CONTENT, f"{result=} for {nothing_vs_placebo=} {nothing_vs_component=}"


def test_PB6_equal_to_the_placebo_and_both_beating_nothing_says_added_text_helps():
    result = content_verdict_from(Verdict.INCONCLUSIVE, Verdict.FIRST_HIGHER, Verdict.FIRST_HIGHER, False)
    assert result is ContentVerdict.ADDED_TEXT_HELPS, f"{result=}"
    assert content_verdict_text(result) == "added text helps and the content does not", f"{content_verdict_text(result)=}"


@pytest.mark.parametrize(("nothing_vs_placebo", "nothing_vs_component"), list(itertools.product([Verdict.INCONCLUSIVE, Verdict.FIRST_LOWER], repeat=2)))
def test_PB7_equal_to_the_placebo_and_neither_beating_nothing_says_nothing_helps(nothing_vs_placebo, nothing_vs_component):
    result = content_verdict_from(Verdict.INCONCLUSIVE, nothing_vs_placebo, nothing_vs_component, False)
    assert result is ContentVerdict.NOTHING_HELPS, f"{result=} for {nothing_vs_placebo=} {nothing_vs_component=}"


@pytest.mark.parametrize(
    ("nothing_vs_placebo", "nothing_vs_component"),
    [(Verdict.FIRST_HIGHER, Verdict.INCONCLUSIVE), (Verdict.FIRST_HIGHER, Verdict.FIRST_LOWER), (Verdict.INCONCLUSIVE, Verdict.FIRST_HIGHER), (Verdict.FIRST_LOWER, Verdict.FIRST_HIGHER)],
)
def test_PB8_equal_to_the_placebo_with_only_one_beating_nothing_is_unclear(nothing_vs_placebo, nothing_vs_component):
    result = content_verdict_from(Verdict.INCONCLUSIVE, nothing_vs_placebo, nothing_vs_component, False)
    assert result is ContentVerdict.UNCLEAR, f"{result=} for {nothing_vs_placebo=} {nothing_vs_component=}"


def test_PB1_there_are_128_inputs_and_each_gives_one_stable_verdict():
    first = [content_verdict_from(*row) for row in ALL_INPUTS]
    second = [content_verdict_from(*row) for row in ALL_INPUTS]
    assert len(ALL_INPUTS) == INPUT_COUNT, f"{len(ALL_INPUTS)=} expected {INPUT_COUNT}"
    assert first == second and all(result in ContentVerdict for result in first), f"{first=} {second=}"


def test_PB1_the_same_counts_twice_give_the_same_verdict():
    arms = (twenty_runs(3), twenty_runs(3), twenty_runs(14))
    assert content_verdict(*arms) is content_verdict(*arms), f"two calls differ for {arms=}"


def test_PB1_every_verdict_value_is_reachable():
    reached = {content_verdict_from(*row) for row in ALL_INPUTS}
    assert reached == set(ContentVerdict), f"{reached=}"


def test_PB1_every_verdict_value_has_a_distinct_text():
    texts = {verdict: content_verdict_text(verdict) for verdict in ContentVerdict}
    assert len(set(texts.values())) == len(ContentVerdict), f"{texts=}"
