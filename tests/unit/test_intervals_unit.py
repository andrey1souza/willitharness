import pytest

from willitharness.counts import Counts
from willitharness.intervals import difference_interval, difference_interval_at, wilson, wilson_at
from willitharness.verdict import verdict_at, verdict_of
from willitharness.vocabulary import Verdict

KNOWN_TOLERANCE = 1e-3
SWAP_TOLERANCE = 1e-9
PERCENT = 100
NARROW_Z = 1.0
WIDE_Z = 3.0
PILOT_PAIRS = [
    pytest.param(Counts(16, 20), Counts(0, 20), 53, 92, id="stop-server-A-vs-B"),
    pytest.param(Counts(16, 20), Counts(17, 20), -29, 19, id="stop-server-A-vs-A2"),
    pytest.param(Counts(20, 20), Counts(12, 20), 16, 61, id="backup-delete-A-vs-B"),
    pytest.param(Counts(20, 20), Counts(20, 20), -16, 16, id="backup-delete-A-vs-A2"),
]


def test_V5_wilson_zero_of_ten_matches_the_known_value():
    low, high = wilson(Counts(0, 10))
    assert low == pytest.approx(0.0, abs=KNOWN_TOLERANCE), f"{low=} for 0 of 10"
    assert high == pytest.approx(0.2775, abs=KNOWN_TOLERANCE), f"{high=} for 0 of 10"


def test_V5_wilson_five_of_ten_matches_the_known_value():
    low, high = wilson(Counts(5, 10))
    assert low == pytest.approx(0.2366, abs=KNOWN_TOLERANCE), f"{low=} for 5 of 10"
    assert high == pytest.approx(0.7634, abs=KNOWN_TOLERANCE), f"{high=} for 5 of 10"


def test_V5_wilson_all_successes_ends_at_one():
    low, high = wilson(Counts(10, 10))
    assert high == pytest.approx(1.0), f"{high=} for 10 of 10"
    assert 0.0 < low < 1.0, f"{low=} for 10 of 10"


def test_V5_all_successes_at_six_runs_keeps_the_upper_bound_at_the_rate():
    low, high = wilson(Counts(6, 6))
    assert high == pytest.approx(1.0), f"{high=} for 6 of 6"
    assert low <= 1.0 <= high, f"{low=} {high=} for 6 of 6"


def test_V5_wilson_needs_at_least_one_run():
    with pytest.raises(AssertionError) as raised:
        wilson(Counts(0, 0))
    assert "at least one run" in str(raised.value), f"{raised.value=}"


def test_counts_reject_more_successes_than_runs():
    with pytest.raises(AssertionError) as raised:
        Counts(6, 5)
    assert "between 0 and runs" in str(raised.value), f"{raised.value=}"


@pytest.mark.parametrize(("first", "second", "low_percent", "high_percent"), PILOT_PAIRS)
def test_pilot_pairs_match_the_spike_analyzer(first, second, low_percent, high_percent):
    low, high = difference_interval(first, second)
    assert round(low * PERCENT) == low_percent, f"{low=} expected about {low_percent}%"
    assert round(high * PERCENT) == high_percent, f"{high=} expected about {high_percent}%"


def test_DI_2_swap_negates_and_reverses_the_interval():
    first, second = Counts(16, 20), Counts(3, 20)
    low, high = difference_interval(first, second)
    swapped_low, swapped_high = difference_interval(second, first)
    assert swapped_low == pytest.approx(-high, abs=SWAP_TOLERANCE), f"{swapped_low=} {high=}"
    assert swapped_high == pytest.approx(-low, abs=SWAP_TOLERANCE), f"{swapped_high=} {low=}"


def test_a_smaller_z_narrows_the_wilson_interval_and_a_larger_z_widens_it():
    low_default, high_default = wilson(Counts(10, 20))
    low_narrow, high_narrow = wilson_at(Counts(10, 20), NARROW_Z)
    low_wide, high_wide = wilson_at(Counts(10, 20), WIDE_Z)
    assert low_default < low_narrow < 0.5 < high_narrow < high_default, f"NARROW_Z must narrow {(low_default, high_default)} to {(low_narrow, high_narrow)}"
    assert low_wide < low_default and high_wide > high_default, f"WIDE_Z must widen {(low_default, high_default)} to {(low_wide, high_wide)}"


def test_the_difference_interval_and_the_verdict_follow_z():
    first, second = Counts(8, 20), Counts(3, 20)
    assert difference_interval_at(first, second, NARROW_Z)[0] > difference_interval(first, second)[0], f"a smaller z raises the lower bound for {first} against {second} at {NARROW_Z}"
    low, high = difference_interval_at(first, second, NARROW_Z)
    assert abs(low - 0.10950864) < KNOWN_TOLERANCE and abs(high - 0.37831208) < KNOWN_TOLERANCE, f"hand-computed Newcombe bounds at z 1.0 are 0.1095 and 0.3783, got {(low, high)}"
    assert verdict_of(first, second) is Verdict.INCONCLUSIVE and verdict_at(first, second, NARROW_Z) is Verdict.FIRST_HIGHER, f"{NARROW_Z} must turn {first} against {second} decisive; expected {Verdict.FIRST_HIGHER}"
