TESTS = (
    'tests/unit/test_outcomes_unit.py',
    'tests/gates/test_analysis_outcomes.py',
    'tests/bdd/analysis/test_effect_with_noise.py',
)

SOURCE = 'src/willitharness/outcomes.py'

MUTANTS = (
    ('unusable-runs-counted-in-n', SOURCE, " and run.usable.get(outcome):", ":"),
    ('completed-uses-the-attempted-flag', SOURCE, "run.usable.get(outcome):", "run.usable.get(TARGET_OUTCOME):"),
    ('missing-outcome-counts-as-false', SOURCE, "        raise AnalysisError(NO_OUTCOME_MESSAGE.format(run_id=record.run_id, outcome=outcome))", "        return False"),
    ('every-usable-run-counts-as-violating', SOURCE, "return bool(record.outcome[outcome])", "return True"),
    ('one-denial-is-enough-for-w-denial', SOURCE, "all(run.denials >= 1 for run in runs if cell_of(run) == cell)", "any(run.denials >= 1 for run in runs if cell_of(run) == cell)"),
    ('no-denial-counts-as-a-denial', SOURCE, "run.denials >= 1", "run.denials >= 0"),
    ('unusable-runs-judge-denial', SOURCE, "runs = tuple(run for run in latest_by_run(records).values() if run.state is RunState.RECORDED_USABLE)", "runs = tuple(run for run in latest_by_run(records).values())"),
    ('started-run-adds-no-cell', SOURCE, "counts = {cell_of(run): Counts(0, 0) for run in runs}", "counts = {}"),
)
