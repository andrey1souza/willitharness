TESTS = ("tests/unit/test_claude_sandbox_unit.py",)
SOURCE = "src/willitharness/claude_sandbox.py"

MUTANTS = (
    ("fail-if-unavailable-false", SOURCE, "FAIL_IF_UNAVAILABLE = True", "FAIL_IF_UNAVAILABLE = False"),
    ("unsandboxed-commands-allowed", SOURCE, "ALLOW_UNSANDBOXED_COMMANDS = False", "ALLOW_UNSANDBOXED_COMMANDS = True"),
    ("sandbox-disabled", SOURCE, "ENABLED = True", "ENABLED = False"),
    ("a-secret-folder-dropped", SOURCE, 'for name in SECRET_DIRECTORIES]', 'for name in SECRET_DIRECTORIES[1:]]'),
    ("secret-folders-not-denied", SOURCE, 'for name in SECRET_DIRECTORIES]', 'for name in ()]'),
    ("workspace-missing-from-allow-write", SOURCE, "for path in (workspace, scratch_path(run_root), calls_path(run_root))]", "for path in (scratch_path(run_root), calls_path(run_root))]"),
    ("scratch-folder-missing-from-allow-write", SOURCE, "for path in (workspace, scratch_path(run_root), calls_path(run_root))]", "for path in (workspace, calls_path(run_root))]"),
    ("calls-log-missing-from-allow-write", SOURCE, "for path in (workspace, scratch_path(run_root), calls_path(run_root))]", "for path in (workspace, scratch_path(run_root))]"),
    ("run-folder-writable", SOURCE, "for path in (workspace, scratch_path(run_root), calls_path(run_root))]", "for path in (workspace, run_root, scratch_path(run_root), calls_path(run_root))]"),
    ("domains-open-by-default", SOURCE, "NO_DOMAINS = ()", 'NO_DOMAINS = ("example.com",)'),
    ("named-domains-ignored", SOURCE, 'list(allowed_domains)', 'list(NO_DOMAINS)'),
)
