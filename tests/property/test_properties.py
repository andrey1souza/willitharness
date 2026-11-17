import itertools

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from willitharness.counts import Counts
from willitharness.decision import MASKED_FORBIDDEN_DECISIONS, decide
from willitharness.effect import map_effect
from willitharness.intervals import difference_interval, wilson
from willitharness.probe import MIN_PROBE_RUNS, classify
from willitharness.verdict import MIN_RUNS, flip, noise_status_of, verdict_of
from willitharness.vocabulary import Decision, EffectResult, GuardResult, NoiseStatus, Reach, Verdict

MAX_RUNS = 300
SWAP_TOLERANCE = 1e-9
EXAMPLES = 400
ALL_INPUTS = list(itertools.product(Reach, EffectResult, GuardResult))
property_settings = settings(max_examples=EXAMPLES, deadline=None)


@st.composite
def counts(draw, minimum_runs=0):
    runs = draw(st.integers(min_value=minimum_runs, max_value=MAX_RUNS))
    return Counts(draw(st.integers(min_value=0, max_value=runs)), runs)


def small_n_violations(verdict_function, pairs):
    return [
        pair
        for pair in pairs
        if min(pair[0].runs, pair[1].runs) < MIN_RUNS and verdict_function(*pair) is not Verdict.INCONCLUSIVE_SMALL_N
    ]


def verdict_without_the_small_n_guard(first, second):
    if min(first.runs, second.runs) == 0:
        return Verdict.INCONCLUSIVE_SMALL_N
    low, high = difference_interval(first, second)
    return Verdict.FIRST_HIGHER if low > 0 else Verdict.FIRST_LOWER if high < 0 else Verdict.INCONCLUSIVE


@property_settings
@given(counts(), counts())
def test_V1_exactly_one_verdict_for_any_input(first, second):
    result = verdict_of(first, second)
    matches = sum(result is verdict for verdict in Verdict)
    assert matches == 1, f"{matches=} for {first=} {second=} {result=}"


@property_settings
@given(counts(), counts())
def test_V2_small_n_gives_small_n_and_enough_runs_never_does(first, second):
    result = verdict_of(first, second)
    small = min(first.runs, second.runs) < MIN_RUNS
    assert (result is Verdict.INCONCLUSIVE_SMALL_N) == small, f"{result=} {small=} for {first=} {second=}"


@property_settings
@given(counts(), counts())
def test_V3_swapping_the_arms_flips_the_verdict(first, second):
    forward = verdict_of(first, second)
    backward = verdict_of(second, first)
    assert forward is flip(backward), f"{forward=} {backward=} for {first=} {second=}"


@property_settings
@given(counts())
def test_V4_identical_counts_never_differ(sample):
    result = verdict_of(sample, sample)
    assert result not in {Verdict.FIRST_HIGHER, Verdict.FIRST_LOWER}, f"{result=} for {sample=}"


@property_settings
@given(counts(minimum_runs=1))
def test_V5_wilson_bounds_hold(sample):
    low, high = wilson(sample)
    assert 0.0 <= low <= sample.rate() <= high <= 1.0, f"{low=} {high=} for {sample=}"


@property_settings
@given(counts(minimum_runs=1), counts(minimum_runs=1))
def test_DI_1_the_difference_interval_is_ordered(first, second):
    low, high = difference_interval(first, second)
    assert low <= high, f"{low=} {high=} for {first=} {second=}"


@property_settings
@given(counts(minimum_runs=1), counts(minimum_runs=1))
def test_DI_2_swap_negates_and_reverses_the_interval(first, second):
    low, high = difference_interval(first, second)
    swapped_low, swapped_high = difference_interval(second, first)
    assert swapped_low == pytest.approx(-high, abs=SWAP_TOLERANCE), f"{swapped_low=} {high=} for {first=} {second=}"
    assert swapped_high == pytest.approx(-low, abs=SWAP_TOLERANCE), f"{swapped_high=} {low=} for {first=} {second=}"


@property_settings
@given(counts(), counts())
def test_V6_noise_is_ok_exactly_when_the_pair_is_inconclusive(first, second):
    status = noise_status_of(first, second)
    verdict = verdict_of(first, second)
    assert (status is NoiseStatus.NOISE_OK) == (verdict is Verdict.INCONCLUSIVE), f"{status=} {verdict=}"


@property_settings
@given(st.sampled_from(list(NoiseStatus)), st.sampled_from(list(Verdict)))
def test_E1_an_effect_other_than_invalid_needs_noise_ok(noise, verdict):
    result = map_effect(noise, verdict)
    assert (result is not EffectResult.INVALID) == (noise is NoiseStatus.NOISE_OK), f"{result=} for {noise=} {verdict=}"


@property_settings
@given(st.integers(min_value=0, max_value=MAX_RUNS), st.data())
def test_P1_to_P3_probe_rules_hold_for_any_hits(runs, data):
    target_hits = data.draw(st.integers(min_value=0, max_value=runs))
    control_hits = data.draw(st.integers(min_value=0, max_value=runs))
    result = classify(runs, target_hits, control_hits)
    if runs < MIN_PROBE_RUNS or control_hits > 0:
        expected = Reach.UNKNOWN
    elif target_hits == runs:
        expected = Reach.LOADED
    elif target_hits == 0:
        expected = Reach.MASKED
    else:
        expected = Reach.UNKNOWN
    assert result is expected, f"{result=} {expected=} for {runs=} {target_hits=} {control_hits=}"


@pytest.mark.parametrize(("reach", "effect", "guard"), ALL_INPUTS)
def test_D9_decide_is_total_and_deterministic(reach, effect, guard):
    first = decide(reach, effect, guard)
    second = decide(reach, effect, guard)
    assert isinstance(first, Decision), f"{first=} for {reach=} {effect=} {guard=}"
    assert first is second, f"{first=} {second=} for {reach=} {effect=} {guard=}"


@pytest.mark.parametrize(("reach", "effect", "guard"), ALL_INPUTS)
def test_D10_replace_with_guard_only_when_everything_lines_up(reach, effect, guard):
    lines_up = (
        reach is Reach.LOADED
        and effect is EffectResult.RULE_LOWERS_VIOLATIONS
        and guard is GuardResult.GUARD_MATCHES_RULE
    )
    result = decide(reach, effect, guard)
    assert (result is Decision.REPLACE_WITH_GUARD) == lines_up, f"{result=} {lines_up=} for {reach=} {effect=} {guard=}"


@pytest.mark.parametrize(("reach", "effect", "guard"), ALL_INPUTS)
def test_D11_no_delete_candidate_when_the_rule_lowers_violations(reach, effect, guard):
    result = decide(reach, effect, guard)
    lowers = effect is EffectResult.RULE_LOWERS_VIOLATIONS
    assert not lowers or result is not Decision.DELETE_CANDIDATE, f"{result=} for {reach=} {effect=} {guard=}"


@pytest.mark.parametrize(("reach", "effect", "guard"), ALL_INPUTS)
def test_D12_masked_rules_never_get_a_verdict_decision(reach, effect, guard):
    result = decide(reach, effect, guard)
    masked = reach is Reach.MASKED
    assert not masked or result not in MASKED_FORBIDDEN_DECISIONS, f"{result=} for {reach=} {effect=} {guard=}"


def test_proof_it_can_fail_V2_a_verdict_without_the_small_n_guard_is_detected():
    pairs = [(Counts(0, MIN_RUNS - 1), Counts(MIN_RUNS, MIN_RUNS)), (Counts(1, MIN_RUNS - 1), Counts(0, MIN_RUNS - 1))]
    real = small_n_violations(verdict_of, pairs)
    wrong = small_n_violations(verdict_without_the_small_n_guard, pairs)
    assert real == [], f"{real=} for the real verdict function"
    assert wrong != [], f"{wrong=} for a verdict function without the small-n guard"
