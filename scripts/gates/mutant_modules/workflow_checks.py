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
    ('workflow-checks-not-registered', 'scripts/gates/repo_checks.py', '    **workflow_checks.CHECKS,\n', ''),
)
