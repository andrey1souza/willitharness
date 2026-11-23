SOURCE = 'scripts/gates/repo_checks.py'

TESTS = (
    'tests/gates/test_data_statement.py',
    'tests/gates/test_result_detector.py',
    'tests/gates/test_home_path_check.py',
    'tests/gates/test_ignored_fixtures.py',
)

MUTANTS = (
    ('home-path-check-not-registered', SOURCE, '    "no-home-paths": home_path_errors,\n', ''),
    ('home-path-folders-not-scanned', SOURCE, 'for leak in leak_check.leaks_in(present)', 'for leak in leak_check.leaks_in([])'),
    ('missing-folder-scanned', SOURCE, 'if (root / name).is_dir()]', 'if True]'),
    ('data-section-not-required', SOURCE, '    if section is None:\n        return [f"{README_FILE} has no', '    if False:\n        return [f"{README_FILE} has no'),
    ('data-heading-renamed', SOURCE, 'DATA_HEADING = "## Data"', 'DATA_HEADING = "## Storage"'),
    ('data-redaction-not-required', SOURCE, '"task text", "redacted", "ignores"', '"task text", "ignores"'),
    ('data-task-text-not-required', SOURCE, '"approvals", "task text", "redacted"', '"approvals", "redacted"'),
    ('data-delete-command-not-required', SOURCE, '"ignores", "rm -r .willitharness", ".willitharness/<plan>")', '"ignores", ".willitharness/<plan>")'),
    ('data-plan-delete-not-required', SOURCE, '"rm -r .willitharness", ".willitharness/<plan>")', '"rm -r .willitharness")'),
    ('data-length-unchecked', SOURCE, 'if len(lines) > DATA_MAX_LINES:', 'if False:'),
    ('data-limit-off-by-one', SOURCE, 'DATA_MAX_LINES = 6', 'DATA_MAX_LINES = 7'),
    ('data-gitignore-unchecked', SOURCE, '    if not any(fnmatch(f"{store}/", pattern) for pattern in patterns):', '    if False:'),
    ('data-check-not-registered', SOURCE, '    "readme-data-statement": data_statement_errors,\n', ''),
    ('result-detector-not-compared', SOURCE, 'errors = [] if recorded == used else', 'errors = [] if True else'),
    ('result-detector-compared-as-a-set', SOURCE, 'errors = [] if recorded == used else', 'errors = [] if set(recorded or ()) <= set(used) else'),
    ('result-detector-check-not-registered', SOURCE, '    "result-detector": result_detector_errors,\n', ''),
    ('ignored-fixtures-not-registered', SOURCE, '    "no-ignored-fixtures": ignored_fixture_errors,\n', ''),
    ('ignored-fixture-folders-narrowed', SOURCE, 'FIXTURE_FOLDERS = ("tests", "fixtures", "features")', 'FIXTURE_FOLDERS = ("tests",)'),
    ('ignored-fixture-everything-allowed', SOURCE, 'if not any(part in TOOL_CACHES for part in Path(name).parts)', 'if False'),
    ('ignored-fixture-caches-reported', SOURCE, 'if not any(part in TOOL_CACHES for part in Path(name).parts)', 'if True'),
    ('ignored-fixture-bytecode-cache-not-allowed', SOURCE, 'TOOL_CACHES = ("__pycache__", ".pytest_cache")', 'TOOL_CACHES = (".pytest_cache",)'),
    ('ignored-fixtures-not-listed', SOURCE, '"--others", "--ignored", "--exclude-standard"', '"--others", "--exclude-standard"'),
    ('ignored-fixture-rule-dropped', SOURCE, 'Rule: a file under', 'A file under'),
    ('ignored-fixture-fix-dropped', SOURCE, 'Fix: git add -f it, or delete it.', 'Delete it.'),
)
