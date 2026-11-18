import pytest

from willitharness.counts import Counts
from willitharness.verdict import MIN_RUNS, flip, noise_status_of, verdict_from_interval, verdict_of
from willitharness.vocabulary import NoiseStatus, Verdict

INTERVAL_EDGE = 0.0
INTERVAL_REACH = 0.5
ENOUGH_RUNS = 20


def test_V1_an_interval_that_starts_at_zero_is_inconclusive():
    result = verdict_from_interval(INTERVAL_EDGE, INTERVAL_REACH)
    assert result is Verdict.INCONCLUSIVE, f"{result=} for the interval ({INTERVAL_EDGE}, {INTERVAL_REACH})"


def test_V1_an_interval_that_ends_at_zero_is_inconclusive():
    result = verdict_from_interval(-INTERVAL_REACH, INTERVAL_EDGE)
    assert result is Verdict.INCONCLUSIVE, f"{result=} for the interval ({-INTERVAL_REACH}, {INTERVAL_EDGE})"


def test_V1_an_interval_clear_of_zero_decides_the_direction():
    above = verdict_from_interval(INTERVAL_REACH / 2, INTERVAL_REACH)
    below = verdict_from_interval(-INTERVAL_REACH, -INTERVAL_REACH / 2)
    assert above is Verdict.FIRST_HIGHER, f"{above=} for an interval above zero"
    assert below is Verdict.FIRST_LOWER, f"{below=} for an interval below zero"
TOO_FEW_RUNS = MIN_RUNS - 1
EXPECTED_MIN_RUNS = 5


def test_min_runs_is_five():
    assert MIN_RUNS == EXPECTED_MIN_RUNS, f"{MIN_RUNS=}"


def test_V2_small_n_rule_ignores_the_counts():
    few = verdict_of(Counts(0, TOO_FEW_RUNS), Counts(ENOUGH_RUNS, ENOUGH_RUNS))
    empty = verdict_of(Counts(ENOUGH_RUNS, ENOUGH_RUNS), Counts(0, 0))
    assert few is Verdict.INCONCLUSIVE_SMALL_N, f"{few=} with {TOO_FEW_RUNS} runs"
    assert empty is Verdict.INCONCLUSIVE_SMALL_N, f"{empty=} with an empty arm"


def test_V2_five_runs_per_side_is_enough_to_decide():
    result = verdict_of(Counts(MIN_RUNS, MIN_RUNS), Counts(0, MIN_RUNS))
    assert result is Verdict.FIRST_HIGHER, f"{result=} at {MIN_RUNS} runs per side"


def test_verdict_first_higher_for_a_clear_gap():
    result = verdict_of(Counts(16, ENOUGH_RUNS), Counts(0, ENOUGH_RUNS))
    assert result is Verdict.FIRST_HIGHER, f"{result=} for 16 of 20 against 0 of 20"


def test_verdict_first_lower_for_the_reversed_gap():
    result = verdict_of(Counts(0, ENOUGH_RUNS), Counts(16, ENOUGH_RUNS))
    assert result is Verdict.FIRST_LOWER, f"{result=} for 0 of 20 against 16 of 20"


def test_verdict_inconclusive_for_a_noise_sized_gap():
    result = verdict_of(Counts(16, ENOUGH_RUNS), Counts(17, ENOUGH_RUNS))
    assert result is Verdict.INCONCLUSIVE, f"{result=} for 16 of 20 against 17 of 20"


@pytest.mark.parametrize(
    ("verdict", "flipped"),
    [
        (Verdict.FIRST_HIGHER, Verdict.FIRST_LOWER),
        (Verdict.FIRST_LOWER, Verdict.FIRST_HIGHER),
        (Verdict.INCONCLUSIVE, Verdict.INCONCLUSIVE),
        (Verdict.INCONCLUSIVE_SMALL_N, Verdict.INCONCLUSIVE_SMALL_N),
    ],
)
def test_V3_flip_table(verdict, flipped):
    once = flip(verdict)
    twice = flip(flipped)
    assert once is flipped, f"{once=} expected {flipped=} for {verdict=}"
    assert twice is verdict, f"{twice=} expected {verdict=} for {flipped=}"


def test_V6_noise_unmeasured_below_the_minimum():
    status = noise_status_of(Counts(1, TOO_FEW_RUNS), Counts(1, ENOUGH_RUNS))
    assert status is NoiseStatus.NOISE_UNMEASURED, f"{status=} with {TOO_FEW_RUNS} runs on one side"


def test_V6_noise_floor_too_high_when_the_pair_differs():
    upward = noise_status_of(Counts(0, ENOUGH_RUNS), Counts(ENOUGH_RUNS, ENOUGH_RUNS))
    downward = noise_status_of(Counts(ENOUGH_RUNS, ENOUGH_RUNS), Counts(0, ENOUGH_RUNS))
    assert upward is NoiseStatus.NOISE_FLOOR_TOO_HIGH, f"{upward=} for 0 against 20 of 20"
    assert downward is NoiseStatus.NOISE_FLOOR_TOO_HIGH, f"{downward=} for 20 of 20 against 0"


def test_V6_noise_ok_when_the_pair_agrees():
    status = noise_status_of(Counts(16, ENOUGH_RUNS), Counts(17, ENOUGH_RUNS))
    assert status is NoiseStatus.NOISE_OK, f"{status=} for 16 of 20 against 17 of 20"
