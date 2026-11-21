SOURCE = 'scripts/gates/repo_checks.py'

TESTS = (
    'tests/gates/test_pr_text_imports.py',
)

MUTANTS = (
    ('plain-imports-not-read', SOURCE, 'isinstance(node, ast.Import) for alias', 'isinstance(node, ast.Pass) for alias'),
    ('from-imports-not-read', SOURCE, 'isinstance(node, ast.ImportFrom) and node.module]', 'isinstance(node, ast.Pass) and node.module]'),
    ('submodule-import-not-cut', SOURCE, 'return {name.split(".")[0] for', 'return {name for'),
    ('status-not-removable', SOURCE, 'REMOVABLE_SITE_MODULES = ("status",)', 'REMOVABLE_SITE_MODULES = ("other",)'),
    ('findings-dropped', SOURCE, '    found = imported_modules((root / PR_TEXT_FILE).read_text()) & set(REMOVABLE_SITE_MODULES)\n', '    found = set()\n'),
    ('check-not-registered', SOURCE, '    "pr-text-self-contained": pr_text_import_errors,\n', ''),
)
