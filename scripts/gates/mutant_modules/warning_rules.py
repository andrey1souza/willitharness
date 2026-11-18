TESTS = (
    'tests/unit/test_warning_rules_unit.py',
    'tests/gates/test_analysis_outcomes.py',
    'tests/bdd/analysis/test_warnings.py',
    'tests/bdd/analysis/test_effect_with_noise.py',
)

SOURCE = 'src/willitharness/warning_rules.py'

MUTANTS = (
    ('w-lown-at-exactly-the-recommended-runs', SOURCE, "if counts[cell].runs < DEFAULT_REPS:", "if counts[cell].runs <= DEFAULT_REPS:"),
    ('w-lown-only-below-the-minimum-runs', SOURCE, "if counts[cell].runs < DEFAULT_REPS:", "if counts[cell].runs < MIN_RUNS:"),
    ('w-denial-for-the-wrong-cells', SOURCE, "if cell in denied:", "if cell not in denied:"),
    ('saturated-at-one-violating-run', SOURCE, "row.first_counts.successes == 0:", "row.first_counts.successes <= 1:"),
    ('saturated-for-every-outcome', SOURCE, "if row.outcome == TARGET_OUTCOME and row.first_counts.runs >= 1", "if row.first_counts.runs >= 1"),
    ('saturated-for-an-empty-arm', SOURCE, "row.first_counts.runs >= 1 and row.first_counts.successes == 0", "row.first_counts.successes == 0"),
    ('at-bound-needs-only-one-bound', SOURCE, "(both_zero or both_full)", "(both_zero or first.successes == first.runs)"),
    ('at-bound-for-empty-arms', SOURCE, "result = first.runs >= 1 and second.runs >= 1 and (both_zero or both_full)", "result = both_zero or both_full"),
    ('at-bound-without-an-inconclusive-verdict', SOURCE, "if row.verdict is Verdict.INCONCLUSIVE and at_bound(", "if at_bound("),
    ('pooled-warning-for-per-task-rows', SOURCE, "        if row.pooled:", "        if not row.pooled:"),
    ('pooled-warning-repeated', SOURCE, "unique = list(dict.fromkeys(lines))", "unique = lines"),
    ('low-n-text-changed', SOURCE, "has {n} usable runs; {recommended} are recommended", "has {n} usable runs"),
    ('pooled-text-changed', SOURCE, 'POOLED_WARNING = "pooled: task clustering is ignored"', 'POOLED_WARNING = "pooled"'),
)
