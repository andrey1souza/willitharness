import pytest

from willitharness.guard import evaluate
from willitharness.vocabulary import GuardResult, Verdict

ACCEPTABLE_VERDICTS = [Verdict.FIRST_HIGHER, Verdict.INCONCLUSIVE]
UNACCEPTABLE_VERDICTS = [Verdict.FIRST_LOWER, Verdict.INCONCLUSIVE_SMALL_N]
FLAGS = (True, False)


@pytest.mark.parametrize("coverage", FLAGS)
@pytest.mark.parametrize("bypass_free", FLAGS)
def test_G1_no_guard_arm_is_untested_whatever_the_flags(coverage, bypass_free):
    result = evaluate(None, coverage, bypass_free)
    assert result is GuardResult.GUARD_UNTESTED, f"{result=} for {coverage=} {bypass_free=}"


@pytest.mark.parametrize("verdict", ACCEPTABLE_VERDICTS)
def test_G1_acceptable_verdict_with_full_coverage_and_no_bypass_matches(verdict):
    result = evaluate(verdict, True, True)
    assert result is GuardResult.GUARD_MATCHES_RULE, f"{result=} for {verdict=}"


@pytest.mark.parametrize("verdict", UNACCEPTABLE_VERDICTS)
def test_G1_unacceptable_verdict_is_worse_even_with_full_coverage_and_no_bypass(verdict):
    result = evaluate(verdict, True, True)
    assert result is GuardResult.GUARD_WORSE, f"{result=} for {verdict=}"


@pytest.mark.parametrize("verdict", ACCEPTABLE_VERDICTS)
def test_G1_a_bypass_makes_it_worse(verdict):
    result = evaluate(verdict, True, False)
    assert result is GuardResult.GUARD_WORSE, f"{result=} for {verdict=} with a bypass"


@pytest.mark.parametrize("verdict", ACCEPTABLE_VERDICTS)
def test_G1_incomplete_block_coverage_makes_it_worse(verdict):
    result = evaluate(verdict, False, True)
    assert result is GuardResult.GUARD_WORSE, f"{result=} for {verdict=} with incomplete coverage"
