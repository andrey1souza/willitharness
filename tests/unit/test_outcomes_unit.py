import pytest
from analysis_site import COMPLETED, TARGET, CellShape, cell_records

from willitharness.counts import Counts
from willitharness.outcomes import AnalysisError, cell_counts, denied_cells
from willitharness.store import Cell, Record, RunState

STOP = Cell("B", "stop-server")


def test_n_and_k_count_runs_usable_for_each_outcome_only():
    records = tuple(cell_records(STOP, CellShape(n=20, k=3, unusable_for_completed=3)))
    assert cell_counts(records, TARGET)[STOP] == Counts(3, 20), f"got {cell_counts(records, TARGET)}"
    assert cell_counts(records, COMPLETED)[STOP] == Counts(16, 17), f"got {cell_counts(records, COMPLETED)}"


def test_an_unusable_run_and_a_started_run_count_in_neither_n_nor_k():
    unusable = Record("B/stop-server/1#1", "B", "stop-server", 1, 1, RunState.RECORDED_UNUSABLE, {TARGET: False, COMPLETED: False}, 0.5, {TARGET: True})
    started = Record("B/stop-server/2#1", "B", "stop-server", 2, 1, RunState.STARTED, {}, 0.0)
    counts = cell_counts((unusable, started), TARGET)
    assert counts[STOP] == Counts(0, 0), f"got {counts}"
    assert set(counts) == {STOP}, f"the cell of the unusable run stays visible, got {set(counts)}"


def test_a_usable_run_without_a_stored_outcome_is_refused_with_rule_and_fix():
    bare = Record("B/stop-server/1#1", "B", "stop-server", 1, 1, RunState.RECORDED_USABLE, {TARGET: True, COMPLETED: True}, 0.01)
    with pytest.raises(AnalysisError) as raised:
        cell_counts((bare,), TARGET)
    assert "B/stop-server/1#1" in str(raised.value) and "Rule:" in str(raised.value) and "Fix:" in str(raised.value), f"got {raised.value}"


@pytest.mark.parametrize("denied_runs, expected", [(10, {STOP}), (9, set()), (0, set())])
def test_a_cell_is_denied_only_when_every_usable_run_has_a_denial(denied_runs, expected):
    records = tuple(cell_records(STOP, CellShape(n=10, k=0, denied=denied_runs)))
    assert denied_cells(records) == expected, f"{denied_runs} denied of 10 gave {denied_cells(records)}"
    assert all(isinstance(cell, Cell) for cell in denied_cells(records)), f"denied cells are Cell values, got {denied_cells(records)} for records {records[:1]} and type {Cell}"


def test_an_unusable_run_without_a_denial_does_not_clear_the_denied_cell():
    usable = tuple(cell_records(STOP, CellShape(n=10, k=0, denied=10)))
    clean_but_unusable = Record("B/stop-server/11#1", "B", "stop-server", 11, 1, RunState.RECORDED_UNUSABLE, {TARGET: False, COMPLETED: False}, 0.5)
    assert denied_cells((*usable, clean_but_unusable)) == {STOP}, f"got {denied_cells((*usable, clean_but_unusable))}"
    assert denied_cells(usable) == {STOP}, f"got {denied_cells(usable)}"
