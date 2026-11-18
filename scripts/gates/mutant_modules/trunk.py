TESTS = (
    'tests/guards/test_trunk.py',
    'tests/guards/test_integrate.py',
)

MUTANTS = (
    ('commit-on-main-allowed', 'scripts/guards/trunk.py', '    if branch == TRUNK:\n        return [', '    if False:\n        return ['),
    ('branch-size-limit-off-by-one', 'scripts/guards/trunk.py', 'if len(timestamps) > MAX_BRANCH_COMMITS:', 'if len(timestamps) > MAX_BRANCH_COMMITS + 1:'),
    ('branch-age-limit-doubled', 'scripts/guards/trunk.py', 'MAX_BRANCH_AGE_HOURS = 24', 'MAX_BRANCH_AGE_HOURS = 48'),
    ('merge-commits-allowed', 'scripts/guards/trunk.py', '["rev-list", "--merges", TRUNK]', '["rev-list", "--max-count=0", TRUNK]'),
    ('any-branch-name-accepted', 'scripts/guards/trunk.py', 'if not BRANCH_PATTERN.match(branch):', 'if False:'),
    ('any-ref-pushable', 'scripts/guards/trunk.py', 'if name == TRUNK or BRANCH_PATTERN.match(name):', 'if True:'),
)
