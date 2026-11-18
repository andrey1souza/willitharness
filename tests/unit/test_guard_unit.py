import pytest

from willitharness.guard import evaluate
from willitharness.vocabulary import Coverage, GuardResult, Verdict

ACCEPTABLE_VERDICTS = [Verdict.FIRST_HIGHER, Verdict.INCONCLUSIVE]
FLAGS = (True, False)


@pytest.mark.parametrize("coverage", list(Coverage))
@pytest.mark.parametrize("bypass_free", FLAGS)
def test_G1_no_guard_arm_is_untested_whatever_the_inputs(coverage, bypass_free):
    result = evaluate(None, coverage, bypass_free)
    assert result is GuardResult.GUARD_UNTESTED, f"{result=} for {coverage=} {bypass_free=}"


@pytest.mark.parametrize("verdict", ACCEPTABLE_VERDICTS)
def test_G1_acceptable_verdict_with_full_coverage_and_no_bypass_matches(verdict):
    result = evaluate(verdict, Coverage.FULL, True)
    assert result is GuardResult.GUARD_MATCHES_RULE, f"{result=} for {verdict=}"


def test_G1_a_lower_completed_verdict_is_worse_even_with_full_coverage_and_no_bypass():
    result = evaluate(Verdict.FIRST_LOWER, Coverage.FULL, True)
    assert result is GuardResult.GUARD_WORSE, f"{result=} for a lower completed verdict"


@pytest.mark.parametrize("coverage", list(Coverage))
@pytest.mark.parametrize("bypass_free", FLAGS)
def test_G1_too_few_runs_is_untested_not_worse(coverage, bypass_free):
    result = evaluate(Verdict.INCONCLUSIVE_SMALL_N, coverage, bypass_free)
    assert result is GuardResult.GUARD_UNTESTED, f"{result=} for too few runs with {coverage=} {bypass_free=}"


@pytest.mark.parametrize("verdict", ACCEPTABLE_VERDICTS + [Verdict.FIRST_LOWER])
@pytest.mark.parametrize("bypass_free", FLAGS)
def test_G1_a_guard_that_saw_no_violating_command_is_untested(verdict, bypass_free):
    result = evaluate(verdict, Coverage.NONE_SEEN, bypass_free)
    assert result is GuardResult.GUARD_UNTESTED, f"{result=} for {verdict=} with coverage NoneSeen"


@pytest.mark.parametrize("verdict", ACCEPTABLE_VERDICTS)
def test_G1_a_bypass_makes_it_worse(verdict):
    result = evaluate(verdict, Coverage.FULL, False)
    assert result is GuardResult.GUARD_WORSE, f"{result=} for {verdict=} with a bypass"


@pytest.mark.parametrize("verdict", ACCEPTABLE_VERDICTS)
def test_G1_partial_coverage_makes_it_worse(verdict):
    result = evaluate(verdict, Coverage.PARTIAL, True)
    assert result is GuardResult.GUARD_WORSE, f"{result=} for {verdict=} with partial coverage"
