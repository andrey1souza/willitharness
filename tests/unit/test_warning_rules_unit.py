import pytest
from analysis_site import COMPLETED, FULL_ROLES, TARGET, analyze_site, filled_cells, site_with_state

from willitharness.analysis import Row
from willitharness.counts import Counts
from willitharness.lifecycle import PlanState, lifecycle_dir
from willitharness.store import Cell, Record, RunState, append_record, run_id_of
from willitharness.vocabulary import EffectResult, NoiseStatus, Verdict
from willitharness.warning_rules import at_bound, cell_warnings, row_warnings, world_warnings


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


def started_in_world(run_id, arm, world_hash):
    return Record(run_id, arm, "stop-server", 1, 1, RunState.STARTED, {}, 0.0, world_hash=world_hash)


def test_T62_a_cell_with_two_worlds_gets_one_warning_naming_it():
    records = (started_in_world("B/stop-server/1#1", "B", "aa"), started_in_world("B/stop-server/2#2", "B", "bb"), started_in_world("C/stop-server/1#1", "C", "aa"))
    assert world_warnings(records) == ["W-WORLD: arm B, task stop-server has runs from 2 worlds; the runs do not share one validated world"], "only cell B mixes worlds"


def test_T62_cells_with_one_world_or_no_recorded_world_get_no_warning():
    records = (started_in_world("B/stop-server/1#1", "B", "aa"), started_in_world("B/stop-server/2#2", "B", "aa"), started_in_world("C/stop-server/1#1", "C", ""), started_in_world("C/stop-server/2#2", "C", "bb"))
    assert world_warnings(records) == [], "one hash per cell, and a record without a hash, are not a mix"


def test_T62_analyze_reports_a_cell_that_mixes_worlds_only_with_warnings_on(tmp_path):
    site = site_with_state(tmp_path, FULL_ROLES, (filled_cells(FULL_ROLES, {}), PlanState.COMPLETE))
    cell = Cell("B", "stop-server")
    for rep, world in ((21, "aa"), (22, "bb")):
        append_record(lifecycle_dir(site.root, site.plan), Record(run_id_of(cell, rep, 1), "B", "stop-server", rep, 1, RunState.RECORDED_USABLE, {TARGET: True, COMPLETED: True}, 0.01, {TARGET: False, COMPLETED: True}, 0, world))
    wanted = "W-WORLD: arm B, task stop-server has runs from 2 worlds; the runs do not share one validated world"
    shown, hidden = analyze_site(site, False, True).warnings, analyze_site(site, False, False).warnings
    assert wanted in shown, f"the mix {wanted!r} must be reported, got {shown}. Fix: add world_warnings to analyze_plan."
    assert hidden == (), f"warnings off must print none, got {hidden}. Rule: with_warnings controls every warning."
