from pathlib import Path

from willitharness.lifecycle import ANALYZABLE, STORE_LOCK, PlanState, lifecycle_dir, move_to, read_state
from willitharness.plan import Plan

MOVES_TO_ANALYZED = (PlanState.COMPLETE, PlanState.BUDGET_STOPPED)


def finish_analysis(root, plan):
    assert isinstance(root, Path), f"finish_analysis needs a Path root, got {root!r}. Fix: pass the project directory."
    assert isinstance(plan, Plan), f"finish_analysis needs a Plan, got {plan!r}. Fix: load the plan."
    folder = lifecycle_dir(root, plan)
    with STORE_LOCK:
        before = read_state(folder)
        if before in MOVES_TO_ANALYZED:
            move_to(folder, PlanState.ANALYZED)
        after = read_state(folder)
    assert after in ANALYZABLE and after not in MOVES_TO_ANALYZED, f"finish_analysis left the plan in {after}. Rule: Analyzed is final."
    assert before not in (PlanState.RUNNING, PlanState.ABORTED), f"finish_analysis saw {before}. Rule: L5, analyze_gate refuses these first."
    return before
