TESTS = (
    'tests/gates/test_analysis_outcomes.py',
    'tests/gates/test_lifecycle_gate.py',
)

MUTANTS = (
    ('analyze-does-not-move-the-state', 'src/willitharness/analyzed.py', "        if before in MOVES_TO_ANALYZED:", "        if False:"),
    ('budget-stopped-plan-stays-resumable', 'src/willitharness/analyzed.py', "MOVES_TO_ANALYZED = (PlanState.COMPLETE, PlanState.BUDGET_STOPPED)", "MOVES_TO_ANALYZED = (PlanState.COMPLETE,)"),
    ('complete-plan-stays-complete', 'src/willitharness/analyzed.py', "MOVES_TO_ANALYZED = (PlanState.COMPLETE, PlanState.BUDGET_STOPPED)", "MOVES_TO_ANALYZED = (PlanState.BUDGET_STOPPED,)"),
    ('previous-state-not-returned', 'src/willitharness/analyzed.py', "    return before\n", "    return after\n"),
)
