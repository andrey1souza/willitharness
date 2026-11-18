TESTS = (
    'tests/guards/test_trunk.py',
    'tests/guards/test_integrate.py',
)

MUTANTS = (
    ('checks-skipped', 'scripts/guards/integrate.py', '    run_branch_checks(repo, command)\n', '    pass\n'),
    ('rebase-skipped', 'scripts/guards/integrate.py', '    rebase_on_trunk(repo, branch)\n', '    pass\n'),
    ('dirty-tree-allowed', 'scripts/guards/integrate.py', '    if dirty:\n', '    if False:\n'),
    ('branch-kept-after-merge', 'scripts/guards/integrate.py', '    run_checked(repo, ["git", "branch", "-d", branch])\n', '    pass\n'),
)
