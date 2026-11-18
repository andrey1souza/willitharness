from willitharness.outcomes import TARGET_OUTCOME
from willitharness.plan import DEFAULT_REPS
from willitharness.verdict import MIN_RUNS
from willitharness.vocabulary import Verdict

LOW_N_WARNING = "W-LOWN: arm {arm}, task {task} has {n} usable runs; {recommended} are recommended"
DENIAL_WARNING = "W-DENIAL: arm {arm}, task {task}: every run has a permission denial"
SATURATED_WARNING = "saturated: arm {arm}, task {task} has no violating run; not measurable at this n; the model may already obey the rule"
POOLED_WARNING = "pooled: task clustering is ignored"
AT_BOUND_WARNING = "AtBound: {outcome}, task {task}, arm {first} against arm {second}: both arms at 0% (or 100%); harder tasks are needed"


def at_bound(first, second):
    assert first.runs >= 0 and second.runs >= 0, f"run counts must not be negative: {first.runs}, {second.runs}"
    assert MIN_RUNS >= 1, f"MIN_RUNS must keep both arms measured, got {MIN_RUNS}"
    both_zero = first.successes == 0 and second.successes == 0
    both_full = first.successes == first.runs and second.successes == second.runs
    result = first.runs >= 1 and second.runs >= 1 and (both_zero or both_full)
    assert not result or min(first.runs, second.runs) >= 1, f"AtBound for an empty arm: {first}, {second}"
    return result


def cell_warnings(counts, denied):
    assert all(item.runs >= 0 for item in counts.values()), f"negative run count in {counts}"
    assert denied <= set(counts), f"denied cells {denied} are not all cells of {sorted(counts)}"
    lines = []
    for cell in sorted(counts):
        if counts[cell].runs < DEFAULT_REPS:
            lines.append(LOW_N_WARNING.format(arm=cell.arm, task=cell.task, n=counts[cell].runs, recommended=DEFAULT_REPS))
        if cell in denied:
            lines.append(DENIAL_WARNING.format(arm=cell.arm, task=cell.task))
    assert all(isinstance(line, str) for line in lines), f"cell_warnings must return text, got {lines}"
    return lines


def row_warnings(rows):
    lines = []
    for row in rows:
        if row.pooled:
            lines.append(POOLED_WARNING)
        if row.outcome == TARGET_OUTCOME and row.first_counts.runs >= 1 and row.first_counts.successes == 0:
            lines.append(SATURATED_WARNING.format(arm=row.first, task=row.task))
        if row.verdict is Verdict.INCONCLUSIVE and at_bound(row.first_counts, row.second_counts):
            lines.append(AT_BOUND_WARNING.format(outcome=row.outcome, task=row.task, first=row.first, second=row.second))
    unique = list(dict.fromkeys(lines))
    assert len(unique) <= len(lines), f"row_warnings invented lines: {unique} from {lines}"
    assert all(isinstance(line, str) for line in unique), f"row_warnings must return text, got {unique}"
    return unique
