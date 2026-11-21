SOURCE = 'scripts/gates/repo_checks.py'

TESTS = (
    'tests/gates/test_integrate_source.py',
)

MUTANTS = (
    ('run-checked-not-scanned', SOURCE, 'GIT_HELPERS = ("run_checked", "git_lines")', 'GIT_HELPERS = ("git_lines",)'),
    ('git-lines-not-scanned', SOURCE, 'GIT_HELPERS = ("run_checked", "git_lines")', 'GIT_HELPERS = ("run_checked",)'),
    ('short-f-not-found', SOURCE, '[A-Za-z]*[fD][A-Za-z]*$', '[A-Za-z]*[D][A-Za-z]*$'),
    ('short-D-not-found', SOURCE, '[A-Za-z]*[fD][A-Za-z]*$', '[A-Za-z]*[f][A-Za-z]*$'),
    ('combined-short-flags-not-found', SOURCE, '^-[A-Za-z]*[fD][A-Za-z]*$', '^-[fD]$'),
    ('force-not-found', SOURCE, '("--force", "--force-with-lease", "--hard", "push", "update-ref")', '("--force-with-lease", "--hard", "push", "update-ref")'),
    ('force-with-lease-not-found', SOURCE, '("--force", "--force-with-lease", "--hard", "push", "update-ref")', '("--force", "--hard", "push", "update-ref")'),
    ('hard-not-found', SOURCE, '"--force-with-lease", "--hard", "push"', '"--force-with-lease", "push"'),
    ('push-not-found', SOURCE, '"--hard", "push", "update-ref")', '"--hard", "update-ref")'),
    ('update-ref-not-found', SOURCE, '"push", "update-ref")', '"push")'),
    ('tuples-not-scanned', SOURCE, 'isinstance(argument, (ast.List, ast.Tuple))', 'isinstance(argument, ast.List)'),
    ('findings-dropped', SOURCE, '    found = forbidden_git_arguments((root / INTEGRATE_FILE).read_text())\n', '    found = []\n'),
    ('check-not-registered', SOURCE, '    "integrate-source-never-forces": integrate_source_errors,\n', ''),
)
