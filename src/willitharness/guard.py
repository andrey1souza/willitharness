from willitharness.vocabulary import GuardResult, Verdict

UNACCEPTABLE_COMPLETED_VERDICTS = frozenset({Verdict.FIRST_LOWER, Verdict.INCONCLUSIVE_SMALL_N})


def evaluate(completed: Verdict | None, full_block_coverage: bool, zero_bypass: bool) -> GuardResult:
    assert completed is None or completed in Verdict, f"unknown completed verdict {completed!r}"
    assert isinstance(full_block_coverage, bool) and isinstance(zero_bypass, bool), (
        f"coverage and bypass are flags, got {full_block_coverage!r}, {zero_bypass!r}"
    )
    if completed is None:
        result = GuardResult.GUARD_UNTESTED
    elif completed not in UNACCEPTABLE_COMPLETED_VERDICTS and full_block_coverage and zero_bypass:
        result = GuardResult.GUARD_MATCHES_RULE
    else:
        result = GuardResult.GUARD_WORSE
    assert (result is GuardResult.GUARD_UNTESTED) == (completed is None), (
        f"G1 broken: {result} for completed {completed!r}"
    )
    assert result is not GuardResult.GUARD_MATCHES_RULE or (
        full_block_coverage and zero_bypass and completed not in UNACCEPTABLE_COMPLETED_VERDICTS
    ), f"G1 broken: {result} for {completed!r}, coverage {full_block_coverage}, bypass-free {zero_bypass}"
    return result
