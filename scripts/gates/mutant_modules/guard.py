TESTS = (
    'tests/unit/test_guard_unit.py',
    'tests/golden',
)

MUTANTS = (
    ('too-few-runs-counts-as-worse', 'src/willitharness/guard.py', 'UNTESTED_COMPLETED_VERDICTS = frozenset({Verdict.INCONCLUSIVE_SMALL_N})', 'UNTESTED_COMPLETED_VERDICTS = frozenset()'),
    ('none-seen-counts-as-worse', 'src/willitharness/guard.py', ' or coverage is Coverage.NONE_SEEN\n', '\n'),
    ('bypass-ignored', 'src/willitharness/guard.py', 'coverage is Coverage.FULL and zero_bypass:', 'coverage is Coverage.FULL:'),
    ('partial-coverage-accepted', 'src/willitharness/guard.py', 'coverage is Coverage.FULL and zero_bypass:', 'coverage is not Coverage.NONE_SEEN and zero_bypass:'),
    ('lower-completed-verdict-accepted', 'src/willitharness/guard.py', 'NOT_MATCHING_COMPLETED_VERDICTS = frozenset({Verdict.FIRST_LOWER})', 'NOT_MATCHING_COMPLETED_VERDICTS = frozenset()'),
)
