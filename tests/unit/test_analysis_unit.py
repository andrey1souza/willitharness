from willitharness.analysis import LOO_INVALID_MESSAGE, RULE_NOT_LOADED_MESSAGE, analyze_effect
from willitharness.vocabulary import EffectResult, NoiseStatus, Reach, Verdict


def analyze(rule_reach, loo_probe):
    return analyze_effect(rule_reach, loo_probe, NoiseStatus.NOISE_OK, Verdict.FIRST_HIGHER)


def test_P4_a_loo_arm_that_is_not_loaded_gives_an_invalid_effect_with_the_message():
    for loo_probe in (Reach.MASKED, Reach.UNKNOWN):
        outcome = analyze(Reach.LOADED, loo_probe)
        assert outcome.effect is EffectResult.INVALID and outcome.verdict is None, f"{loo_probe}: got {outcome}"
        assert outcome.message == LOO_INVALID_MESSAGE, (
            f"{loo_probe}: expected message {LOO_INVALID_MESSAGE!r}, got {outcome.message!r}. Rule: the message tells the user why. Fix: restore the message."
        )


def test_L7_a_rule_arm_that_is_not_loaded_emits_no_verdict():
    for rule_reach in (Reach.MASKED, Reach.UNKNOWN):
        outcome = analyze(rule_reach, Reach.LOADED)
        assert outcome.verdict is None and outcome.message == RULE_NOT_LOADED_MESSAGE, f"{rule_reach}: got {outcome}"


def test_both_arms_loaded_with_noise_ok_maps_the_verdict_to_the_effect():
    outcome = analyze(Reach.LOADED, Reach.LOADED)
    assert (outcome.effect, outcome.verdict, outcome.message) == (
        EffectResult.RULE_LOWERS_VIOLATIONS,
        Verdict.FIRST_HIGHER,
        None,
    ), f"got {outcome}"


def test_both_arms_loaded_with_a_noise_problem_keeps_the_verdict_but_marks_the_effect_invalid():
    outcome = analyze_effect(Reach.LOADED, Reach.LOADED, NoiseStatus.NOISE_FLOOR_TOO_HIGH, Verdict.FIRST_HIGHER)
    assert outcome.effect is EffectResult.INVALID, f"a noise problem must give Invalid, got {outcome}"
