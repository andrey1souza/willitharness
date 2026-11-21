SOURCE = 'scripts/gates/hook_checks.py'

TESTS = (
    'tests/gates/test_hook_checks.py',
)

MUTANTS = (
    ('scrub-after-tests-accepted', SOURCE, ' or text.index(SCRUB_COMMAND) > text.index(TEST_COMMAND)', ''),
    ('missing-scrub-accepted', SOURCE, 'SCRUB_COMMAND not in text or ', ''),
    ('missing-test-line-accepted', SOURCE, 'if TEST_COMMAND not in text:', 'if False:'),
    ('missing-hook-accepted', SOURCE, 'if not path.is_file():\n        return [f"{PRE_PUSH_HOOK} is missing. Rule: the push hook runs the tests.', 'if False:\n        return [f"{PRE_PUSH_HOOK} is missing. Rule: the push hook runs the tests.'),
    ('scrub-only-anywhere-in-file', SOURCE, 'text.index(SCRUB_COMMAND) > text.index(TEST_COMMAND)', 'False'),
    ('hook-checks-not-registered', 'scripts/gates/repo_checks.py', '    **hook_checks.CHECKS,\n', ''),
    ('bare-check-after-toplevel-accepted', SOURCE, ' or text.index(BARE_CHECK_COMMAND) > text.index(TOPLEVEL_COMMAND)', ''),
    ('missing-bare-check-accepted', SOURCE, 'BARE_CHECK_COMMAND not in text or ', ''),
    ('missing-toplevel-line-accepted', SOURCE, ' or TOPLEVEL_COMMAND not in text', ''),
    ('missing-hook-passes-bare-check', SOURCE, 'if not path.is_file():\n        return [f"{PRE_PUSH_HOOK} is missing. Rule: the push hook detects', 'if False:\n        return [f"{PRE_PUSH_HOOK} is missing. Rule: the push hook detects'),
    ('bare-check-not-registered', SOURCE, '    "pre-push-detects-bare-checkout": pre_push_bare_errors,\n', ''),
)
