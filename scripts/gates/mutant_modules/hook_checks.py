SOURCE = 'scripts/gates/hook_checks.py'

TESTS = (
    'tests/gates/test_hook_checks.py',
)

MUTANTS = (
    ('scrub-after-tests-accepted', SOURCE, ' or text.index(SCRUB_COMMAND) > text.index(TEST_COMMAND)', ''),
    ('missing-scrub-accepted', SOURCE, 'SCRUB_COMMAND not in text or ', ''),
    ('missing-test-line-accepted', SOURCE, 'if TEST_COMMAND not in text:', 'if False:'),
    ('missing-hook-accepted', SOURCE, 'if not path.is_file():', 'if False:'),
    ('scrub-only-anywhere-in-file', SOURCE, 'text.index(SCRUB_COMMAND) > text.index(TEST_COMMAND)', 'False'),
    ('hook-checks-not-registered', 'scripts/gates/repo_checks.py', '    **hook_checks.CHECKS,\n', ''),
)
