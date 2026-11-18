from willitharness.vocabulary import Coverage, GuardResult, Verdict

NOT_MATCHING_COMPLETED_VERDICTS = frozenset({Verdict.FIRST_LOWER})
UNTESTED_COMPLETED_VERDICTS = frozenset({Verdict.INCONCLUSIVE_SMALL_N})


def evaluate(completed: Verdict | None, coverage: Coverage, zero_bypass: bool) -> GuardResult:
    assert completed is None or completed in Verdict, f"unknown completed verdict {completed!r}"
    assert coverage in Coverage and isinstance(zero_bypass, bool), (
        f"coverage must be a Coverage and bypass a flag, got {coverage!r}, {zero_bypass!r}"
    )
    untested = completed is None or completed in UNTESTED_COMPLETED_VERDICTS or coverage is Coverage.NONE_SEEN
    if untested:
        result = GuardResult.GUARD_UNTESTED
    elif completed not in NOT_MATCHING_COMPLETED_VERDICTS and coverage is Coverage.FULL and zero_bypass:
        result = GuardResult.GUARD_MATCHES_RULE
    else:
        result = GuardResult.GUARD_WORSE
    assert (result is GuardResult.GUARD_UNTESTED) == untested, f"G1 broken: {result} for completed {completed!r}, {coverage}"
    assert result is not GuardResult.GUARD_MATCHES_RULE or (
        coverage is Coverage.FULL and zero_bypass and completed not in NOT_MATCHING_COMPLETED_VERDICTS
    ), f"G1 broken: {result} for {completed!r}, coverage {coverage}, bypass-free {zero_bypass}"
    return result
