from dataclasses import dataclass

from willitharness.effect import map_effect
from willitharness.probe import loo_arm_valid
from willitharness.vocabulary import EffectResult, NoiseStatus, Reach, Verdict

LOO_INVALID_MESSAGE = "LOO arm does not load its other rules; the effect cannot be reported"
RULE_NOT_LOADED_MESSAGE = "the rule arm is not known to load; fix loading or run the probe again before measuring an effect"


@dataclass(frozen=True)
class EffectAnalysis:
    effect: EffectResult
    verdict: Verdict | None
    message: str | None


def analyze_effect(rule_reach, loo_probe, noise, verdict):
    assert rule_reach in Reach and loo_probe in Reach, f"unknown reach values {rule_reach!r}, {loo_probe!r}"
    assert noise in NoiseStatus and verdict in Verdict, f"unknown noise or verdict {noise!r}, {verdict!r}"
    if not loo_arm_valid(loo_probe):
        outcome = EffectAnalysis(EffectResult.INVALID, None, LOO_INVALID_MESSAGE)
    elif rule_reach is not Reach.LOADED:
        outcome = EffectAnalysis(EffectResult.INVALID, None, RULE_NOT_LOADED_MESSAGE)
    else:
        outcome = EffectAnalysis(map_effect(noise, verdict), verdict, None)
    assert (outcome.verdict is None) == (outcome.effect is EffectResult.INVALID and outcome.message is not None), (
        f"L7 or P4 broken: {outcome} for rule reach {rule_reach} and LOO probe {loo_probe}"
    )
    assert outcome.verdict is None or (rule_reach is Reach.LOADED and loo_probe is Reach.LOADED), (
        f"L7 or P4 broken: a verdict was emitted for rule reach {rule_reach} and LOO probe {loo_probe}"
    )
    return outcome
