import itertools

import pytest

from willitharness.decision import decide
from willitharness.vocabulary import Decision, EffectResult, GuardResult, Reach

ANY_EFFECT_AND_GUARD = list(itertools.product(EffectResult, GuardResult))
INPUT_COUNT = 45
LOADED_ROWS = [
    pytest.param(EffectResult.INVALID, GuardResult.GUARD_WORSE, Decision.CANNOT_DECIDE, id="D3"),
    pytest.param(EffectResult.NOT_ENOUGH_RUNS, GuardResult.GUARD_UNTESTED, Decision.NEEDS_MORE_RUNS, id="D4"),
    pytest.param(EffectResult.RULE_RAISES_VIOLATIONS, GuardResult.GUARD_WORSE, Decision.DELETE_CANDIDATE, id="D5"),
    pytest.param(EffectResult.NO_MEASURABLE_EFFECT, GuardResult.GUARD_WORSE, Decision.DELETE_CANDIDATE, id="D6"),
    pytest.param(EffectResult.RULE_LOWERS_VIOLATIONS, GuardResult.GUARD_MATCHES_RULE, Decision.REPLACE_WITH_GUARD, id="D7"),
    pytest.param(EffectResult.RULE_LOWERS_VIOLATIONS, GuardResult.GUARD_WORSE, Decision.KEEP, id="D8-worse"),
    pytest.param(EffectResult.RULE_LOWERS_VIOLATIONS, GuardResult.GUARD_UNTESTED, Decision.KEEP, id="D8-untested"),
]


@pytest.mark.parametrize(("effect", "guard"), ANY_EFFECT_AND_GUARD)
def test_D1_masked_always_means_fix_the_loading(effect, guard):
    result = decide(Reach.MASKED, effect, guard)
    assert result is Decision.FIX_LOADING, f"{result=} for {effect=} {guard=}"


@pytest.mark.parametrize(("effect", "guard"), ANY_EFFECT_AND_GUARD)
def test_D2_unknown_reach_always_cannot_decide(effect, guard):
    result = decide(Reach.UNKNOWN, effect, guard)
    assert result is Decision.CANNOT_DECIDE, f"{result=} for {effect=} {guard=}"


@pytest.mark.parametrize(("effect", "guard", "expected"), LOADED_ROWS)
def test_D3_to_D8_loaded_rows(effect, guard, expected):
    result = decide(Reach.LOADED, effect, guard)
    assert result is expected, f"{result=} expected {expected=} for {effect=} {guard=}"


def test_D9_there_are_forty_five_inputs():
    inputs = len(list(itertools.product(Reach, EffectResult, GuardResult)))
    assert inputs == INPUT_COUNT, f"{inputs=} expected {INPUT_COUNT}"
