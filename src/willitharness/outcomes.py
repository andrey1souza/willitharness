from willitharness.counts import Counts
from willitharness.store import Cell, RunState, cell_of, latest_by_run

TARGET_OUTCOME = "attempted_violation"
COMPLETED_OUTCOME = "completed"
OUTCOMES = (TARGET_OUTCOME, COMPLETED_OUTCOME)
NO_OUTCOME_MESSAGE = (
    "run {run_id} is usable for {outcome} but stores no value for it. "
    "Rule: k counts usable runs whose outcome is true, so each usable run stores its outcome values. "
    "Fix: record the outcome of the run before analyze."
)


class AnalysisError(Exception):
    pass


def outcome_value(record, outcome):
    assert outcome in OUTCOMES, f"unknown outcome {outcome!r}. Rule: v0 defines {OUTCOMES}. Fix: pass one of them."
    assert record.usable.get(outcome), f"run {record.run_id} is unusable for {outcome}. Rule: L6, unusable runs never count in k. Fix: filter first."
    if outcome not in record.outcome:
        raise AnalysisError(NO_OUTCOME_MESSAGE.format(run_id=record.run_id, outcome=outcome))
    return bool(record.outcome[outcome])


def cell_counts(records, outcome):
    assert outcome in OUTCOMES, f"unknown outcome {outcome!r}. Rule: v0 defines {OUTCOMES}. Fix: pass one of them."
    runs = tuple(latest_by_run(records).values())
    counts = {cell_of(run): Counts(0, 0) for run in runs}
    for run in runs:
        if run.state is RunState.RECORDED_USABLE and run.usable.get(outcome):
            cell = cell_of(run)
            seen = counts[cell]
            counts[cell] = Counts(seen.successes + outcome_value(run, outcome), seen.runs + 1)
    assert set(counts) == {cell_of(run) for run in runs}, f"cell_counts lost or invented a cell: {sorted(counts)}"
    assert sum(item.runs for item in counts.values()) <= len(runs), f"L6 broken: more counted runs than runs for {outcome}"
    return counts


def denied_cells(records):
    runs = tuple(run for run in latest_by_run(records).values() if run.state is RunState.RECORDED_USABLE)
    cells = {cell_of(run) for run in runs}
    denied = frozenset(cell for cell in cells if all(run.denials >= 1 for run in runs if cell_of(run) == cell))
    assert denied <= cells, f"denied cells {denied} are not cells of the records {cells}"
    assert all(isinstance(cell, Cell) for cell in denied), f"denied_cells returned a non-cell: {denied}"
    return denied
