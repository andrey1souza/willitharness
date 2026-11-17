from willitharness.vocabulary import Decision, EffectResult, GuardResult, Reach

LOADED_DECISION_BY_EFFECT = {
    EffectResult.INVALID: Decision.CANNOT_DECIDE,
    EffectResult.NOT_ENOUGH_RUNS: Decision.NEEDS_MORE_RUNS,
    EffectResult.RULE_RAISES_VIOLATIONS: Decision.DELETE_CANDIDATE,
    EffectResult.NO_MEASURABLE_EFFECT: Decision.DELETE_CANDIDATE,
}
MASKED_FORBIDDEN_DECISIONS = frozenset({Decision.KEEP, Decision.REPLACE_WITH_GUARD, Decision.DELETE_CANDIDATE})


def decide(reach: Reach, effect: EffectResult, guard: GuardResult) -> Decision:
    assert reach in Reach and effect in EffectResult and guard in GuardResult, (
        f"decide needs known values, got {reach!r}, {effect!r}, {guard!r}"
    )
    assert len(LOADED_DECISION_BY_EFFECT) == len(EffectResult) - 1, (
        f"every effect but RuleLowersViolations is tabled: {len(LOADED_DECISION_BY_EFFECT)} of {len(EffectResult)}"
    )
    if reach is Reach.MASKED:
        result = Decision.FIX_LOADING
    elif reach is Reach.UNKNOWN:
        result = Decision.CANNOT_DECIDE
    elif effect is EffectResult.RULE_LOWERS_VIOLATIONS:
        result = Decision.REPLACE_WITH_GUARD if guard is GuardResult.GUARD_MATCHES_RULE else Decision.KEEP
    else:
        result = LOADED_DECISION_BY_EFFECT[effect]
    assert result is not Decision.REPLACE_WITH_GUARD or (
        reach is Reach.LOADED and effect is EffectResult.RULE_LOWERS_VIOLATIONS and guard is GuardResult.GUARD_MATCHES_RULE
    ), f"D10 broken: {result} for {reach}, {effect}, {guard}"
    assert result is not Decision.DELETE_CANDIDATE or effect is not EffectResult.RULE_LOWERS_VIOLATIONS, (
        f"D11 broken: {result} despite {effect}"
    )
    assert reach is not Reach.MASKED or result not in MASKED_FORBIDDEN_DECISIONS, (
        f"D12 broken: a masked rule got {result}"
    )
    return result
