import pytest

from willitharness.analysis import (
    LOO_INVALID_MESSAGE,
    RULE_UNKNOWN_MESSAGE,
    PlanFacts,
    analyze_effect,
    can_report,
)
from willitharness.vocabulary import EffectResult, NoiseStatus, Reach, Verdict

LOO_LABEL = "C"
ALL_FACTS = [
    PlanFacts(pair, noise, loo, rule)
    for pair in (True, False)
    for noise in NoiseStatus
    for loo in Reach
    for rule in Reach
]


def facts(changes):
    base = {"has_noise_pair": True, "noise": NoiseStatus.NOISE_OK, "loo_probe": Reach.LOADED, "rule_reach": Reach.LOADED}
    return PlanFacts(**{**base, **changes})


def analyze(plan_facts):
    return analyze_effect(plan_facts, Verdict.FIRST_HIGHER, LOO_LABEL)


def test_L8_a_plan_with_no_noise_pair_cannot_report_and_names_the_fix():
    outcome = analyze(facts({"has_noise_pair": False}))
    assert outcome.verdict is None and outcome.effect is EffectResult.INVALID, f"got {outcome}"
    assert outcome.message == "no noise pair; add a repeat of arm C with role noise_of:C", (
        f"expected the no-noise-pair message that names arm C, got {outcome.message!r}. Rule: the message tells the user what to add. Fix: restore it."
    )


@pytest.mark.parametrize("loo_probe", [Reach.MASKED, Reach.UNKNOWN])
def test_P4_a_loo_arm_that_is_not_loaded_gives_an_invalid_effect_with_the_message(loo_probe):
    outcome = analyze(facts({"loo_probe": loo_probe}))
    assert outcome.effect is EffectResult.INVALID and outcome.verdict is None, f"{loo_probe}: got {outcome}"
    assert outcome.message == LOO_INVALID_MESSAGE, f"{loo_probe}: expected {LOO_INVALID_MESSAGE!r}, got {outcome.message!r}"


def test_L7_an_unknown_rule_arm_emits_no_verdict():
    outcome = analyze(facts({"rule_reach": Reach.UNKNOWN}))
    assert outcome.verdict is None and outcome.message == RULE_UNKNOWN_MESSAGE, f"got {outcome}"


def test_a_masked_rule_arm_still_reports_its_measured_effect():
    outcome = analyze(facts({"rule_reach": Reach.MASKED}))
    assert outcome.verdict is Verdict.FIRST_HIGHER and outcome.message is None, f"got {outcome}"


@pytest.mark.parametrize("noise", [NoiseStatus.NOISE_UNMEASURED, NoiseStatus.NOISE_FLOOR_TOO_HIGH])
def test_V6_a_noise_problem_gives_an_invalid_effect_and_no_verdict(noise):
    outcome = analyze(facts({"noise": noise}))
    assert outcome.effect is EffectResult.INVALID and outcome.verdict is None, f"{noise}: got {outcome}"
    assert outcome.message, f"{noise}: a blocked effect needs a message, got {outcome}"


def test_both_arms_loaded_with_noise_ok_maps_the_verdict_to_the_effect():
    outcome = analyze(facts({}))
    assert (outcome.effect, outcome.verdict, outcome.message) == (
        EffectResult.RULE_LOWERS_VIOLATIONS,
        Verdict.FIRST_HIGHER,
        None,
    ), f"got {outcome}"


def test_can_report_is_true_for_exactly_the_plans_with_all_four_conditions():
    expected = [
        plan.has_noise_pair and plan.noise is NoiseStatus.NOISE_OK and plan.loo_probe is Reach.LOADED and plan.rule_reach is not Reach.UNKNOWN
        for plan in ALL_FACTS
    ]
    assert [can_report(plan) for plan in ALL_FACTS] == expected, "can_report disagrees with the four conditions of Lean's CanReport"
