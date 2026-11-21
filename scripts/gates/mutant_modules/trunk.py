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
    ('size-fix-names-no-pull-request', 'scripts/guards/trunk.py', 'PUBLISH_STEP = "git push origin <branch>, then open a pull request"', 'PUBLISH_STEP = "integrate it"'),
    ('verify-step-names-land-local', 'scripts/guards/trunk.py', 'VERIFY_STEP = "python3 scripts/guards/integrate.py"', 'VERIFY_STEP = "python3 scripts/guards/integrate.py --land-local"'),
    ('land-local-step-loses-the-flag', 'scripts/guards/trunk.py', 'LAND_LOCAL_STEP = "python3 scripts/guards/integrate.py --land-local"', 'LAND_LOCAL_STEP = "python3 scripts/guards/integrate.py"'),
    ('main-commit-fix-loses-the-warning', 'scripts/guards/trunk.py', ' and is not for publishing."', '."'),
    ('age-fix-omits-verify', 'scripts/guards/trunk.py', 'Fix: run {VERIFY_STEP} to verify the branch, then {PUBLISH_STEP}, or delete the branch."', 'Fix: {PUBLISH_STEP}, or delete the branch."'),
    ('merge-fix-omits-land-local', 'scripts/guards/trunk.py', 'fast-forward, as {LAND_LOCAL_STEP} does."', 'fast-forward, as integrate does."'),
    ('any-branch-may-go-to-main', 'scripts/guards/trunk.py', 'if name == TRUNK and local_ref != remote_ref:', 'if False:'),
    ('local-ref-compared-by-name-only', 'scripts/guards/trunk.py', 'if name == TRUNK and local_ref != remote_ref:', 'if name == TRUNK and not local_ref:'),
    ('local-ref-argument-dropped', 'scripts/guards/trunk.py', 'arguments[2] if len(arguments) > 2 else ""', '"refs/heads/main"'),
    ('missing-local-ref-accepted', 'scripts/guards/trunk.py', '    assert local_ref, "push_ref_errors got an empty local ref.', '    assert True, "push_ref_errors got an empty local ref.'),
)
