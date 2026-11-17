from willitharness.vocabulary import EffectResult, NoiseStatus, Verdict

EFFECT_BY_VERDICT = {
    Verdict.INCONCLUSIVE_SMALL_N: EffectResult.NOT_ENOUGH_RUNS,
    Verdict.FIRST_HIGHER: EffectResult.RULE_LOWERS_VIOLATIONS,
    Verdict.FIRST_LOWER: EffectResult.RULE_RAISES_VIOLATIONS,
    Verdict.INCONCLUSIVE: EffectResult.NO_MEASURABLE_EFFECT,
}


def map_effect(noise: NoiseStatus, verdict: Verdict) -> EffectResult:
    assert noise in NoiseStatus, f"unknown noise status {noise!r}"
    assert verdict in EFFECT_BY_VERDICT, f"unknown verdict {verdict!r}"
    result = EFFECT_BY_VERDICT[verdict] if noise is NoiseStatus.NOISE_OK else EffectResult.INVALID
    assert (result is EffectResult.INVALID) == (noise is not NoiseStatus.NOISE_OK), "V6 broken: effect without NoiseOk"
    assert noise is not NoiseStatus.NOISE_OK or result is EFFECT_BY_VERDICT[verdict], "E1 broken: NoiseOk row"
    return result
