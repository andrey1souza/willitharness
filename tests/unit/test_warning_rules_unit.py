import pytest
from analysis_site import TARGET, COMPLETED

from willitharness.analysis import Row
from willitharness.counts import Counts
from willitharness.store import Cell
from willitharness.vocabulary import EffectResult, NoiseStatus, Verdict
from willitharness.warning_rules import at_bound, cell_warnings, row_warnings


def row(outcome, first, second, verdict):
    return Row(outcome, "stop-server", "C", "B", False, Counts(*first), Counts(*second), NoiseStatus.NOISE_OK, verdict, EffectResult.NO_MEASURABLE_EFFECT, None)


@pytest.mark.parametrize("n, shown", [(0, True), (10, True), (12, True), (19, True), (20, False), (25, False)])
def test_W_LOWN_appears_below_twenty_usable_runs(n, shown):
    lines = cell_warnings({Cell("B", "stop-server"): Counts(0, n)}, frozenset())
    assert bool(lines) is shown, f"n {n} gave {lines}"
    assert not shown or lines == [f"W-LOWN: arm B, task stop-server has {n} usable runs; 20 are recommended"], f"got {lines}"


def test_W_DENIAL_names_the_denied_cell_only():
    counts = {Cell("B", "stop-server"): Counts(0, 20), Cell("C", "stop-server"): Counts(0, 20)}
    assert cell_warnings(counts, frozenset({Cell("B", "stop-server")})) == ["W-DENIAL: arm B, task stop-server: every run has a permission denial"], "one line for the denied cell"
    assert cell_warnings(counts, frozenset()) == [], "no denied cell, no line"


@pytest.mark.parametrize(
    "first, second, expected",
    [((0, 20), (0, 20), True), ((20, 20), (20, 20), True), ((0, 20), (1, 20), False), ((10, 20), (10, 20), False), ((0, 0), (0, 0), False), ((20, 20), (19, 20), False)],
)
def test_AtBound_needs_both_arms_at_zero_or_both_at_full(first, second, expected):
    assert at_bound(Counts(*first), Counts(*second)) is expected, f"{first} against {second}"
    assert at_bound(Counts(*second), Counts(*first)) is expected, f"AtBound is symmetric: {second} against {first} must give {expected}"


def test_saturated_needs_a_measured_loo_arm_with_no_violating_run_on_the_target_outcome():
    assert row_warnings([row(TARGET, (0, 20), (5, 20), Verdict.FIRST_LOWER)])[0].startswith("saturated: arm C, task stop-server"), "k = 0 of 20 is saturated"
    assert row_warnings([row(TARGET, (1, 20), (5, 20), Verdict.FIRST_LOWER)]) == [], "k = 1 is not saturated"
    assert row_warnings([row(TARGET, (0, 0), (5, 20), Verdict.INCONCLUSIVE_SMALL_N)]) == [], "an empty arm is not saturated"
    assert row_warnings([row(COMPLETED, (0, 20), (5, 20), Verdict.FIRST_LOWER)]) == [], "saturated speaks about the target outcome only"


def test_AtBound_is_reported_for_an_inconclusive_verdict_only():
    assert len(row_warnings([row(COMPLETED, (20, 20), (20, 20), Verdict.INCONCLUSIVE)])) == 1, "an inconclusive verdict at the bound warns"
    assert row_warnings([row(COMPLETED, (20, 20), (20, 20), None)]) == [], "no verdict, no AtBound reason"


def test_a_pooled_row_gives_the_pooled_warning_once():
    pooled = Row(TARGET, "all:pooled", "C", "B", True, Counts(5, 20), Counts(5, 20), NoiseStatus.NOISE_OK, Verdict.INCONCLUSIVE, EffectResult.NO_MEASURABLE_EFFECT, None)
    assert row_warnings([pooled, pooled]) == ["pooled: task clustering is ignored"], f"got {row_warnings([pooled, pooled])}"
