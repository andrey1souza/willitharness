SOURCE = 'scripts/gates/workflow_checks.py'

TESTS = (
    'tests/gates/test_workflow_checks.py',
)

MUTANTS = (
    ('short-sha-accepted', SOURCE, '[0-9a-f]{40}")', '[0-9a-f]{7,40}")'),
    ('upper-case-sha-accepted', SOURCE, '[0-9a-f]{40}")', '[0-9a-fA-F]{40}")'),
    ('local-action-not-exempt', SOURCE, 'not reference.startswith(LOCAL_ACTION_PREFIX) and ', ''),
    ('permissions-anywhere-accepted', SOURCE, 're.compile(r"^permissions:", re.MULTILINE)', 're.compile(r"^\\s*permissions:", re.MULTILINE)'),
    ('inline-trigger-ignored', SOURCE, r'|^\s*on:.*\bpull_request_target\b', ''),
    ('head-ref-allowed', SOURCE, '(?:event\\.|head_ref)', '(?:event\\.)'),
    ('run-block-never-ends', SOURCE, '<= key_indent:', '<= -1:'),
    ('unlocked-sync-allowed', SOURCE, '(?! --locked)', ''),
    ('security-md-not-required', SOURCE, 'REQUIRED_FILES = (SECURITY_FILE, ', 'REQUIRED_FILES = ('),
    ('any-star-is-catch-all', SOURCE, 're.compile(r"^\\*\\s+@\\S+", re.MULTILINE)', 're.compile(r"\\*", re.MULTILINE)'),
    ('actions-ecosystem-not-required', SOURCE, '("github-actions", "uv")', '("uv",)'),
    ('empty-workflow-directory-passes', SOURCE, 'if not files:', 'if False:'),
    ('zanity-job-not-required', SOURCE, 'REQUIRED_JOBS = ("test", "zanity", "macos")', 'REQUIRED_JOBS = ("test", "macos")'),
    ('last-job-block-dropped', SOURCE, 'if index + 1 < len(keys) else len(body)', 'if index + 1 < len(keys) else key.end()'),
    ('uv-job-without-python-accepted', SOURCE, 'if UV_USE.search(block) and not EXPLICIT_PYTHON.search(block)', 'if False'),
    ('pin-file-ignored-by-source-check', SOURCE, '    if (root / PYTHON_VERSION_FILE).is_file():\n        return []\n', ''),
    ('uv-python-env-not-explicit', SOURCE, 'python-version:|\\bUV_PYTHON\\b|--python\\b', 'python-version:|--python\\b'),
    ('pin-below-minimum-accepted', SOURCE, '>= tuple(map(int, minimum.groups()))', '>= (0, 0)'),
    ('pin-minor-only-compared', SOURCE, 'satisfied = tuple(map(int, pinned.groups())) >=', 'satisfied = int(pinned.group(2)) >='),
    ('missing-pin-file-passes', SOURCE, '    if not pinned:\n        return [', '    if False:\n        return ['),
    ('workflow-checks-not-registered', 'scripts/gates/repo_checks.py', '    **workflow_checks.CHECKS,\n', ''),
)
