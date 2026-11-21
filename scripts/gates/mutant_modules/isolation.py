PLATFORM = "darwin"
TESTS = ("tests/unit/test_isolation_unit.py", "tests/gates/test_sandbox_gate.py")

MUTANTS = (
    ("agent-shell-not-forced", "src/willitharness/isolation.py", "    kept[SHELL_VARIABLE] = AGENT_SHELL\n", ""),
    ("agent-shell-is-zsh", "src/willitharness/isolation.py", 'AGENT_SHELL = "/bin/bash"', 'AGENT_SHELL = "/bin/zsh"'),
    ("every-variable-passes", "src/willitharness/isolation.py", "if name in ALLOWED_VARIABLES", "if True"),
    ("claude-code-prefix-restored", "src/willitharness/isolation.py", "if name in ALLOWED_VARIABLES}", 'if name in ALLOWED_VARIABLES or name.startswith("CLAUDE_CODE_")}'),
    ("session-id-listed", "src/willitharness/isolation.py", '"CLAUDE_CONFIG_DIR", "CLAUDE_CODE_TMPDIR"', '"CLAUDE_CONFIG_DIR", "CLAUDE_CODE_SESSION_ID", "CLAUDE_CODE_TMPDIR"'),
    ("messaging-token-listed", "src/willitharness/isolation.py", '"CLAUDE_CODE_OAUTH_TOKEN", "ANTHROPIC_BASE_URL"', '"CLAUDE_CODE_OAUTH_TOKEN", "CLAUDE_CODE_MESSAGING_TOKEN", "ANTHROPIC_BASE_URL"'),
    ("locale-prefix-restored", "src/willitharness/isolation.py", "if name in ALLOWED_VARIABLES}", 'if name in ALLOWED_VARIABLES or name.startswith("LC_")}'),
    ("secret-marker-password-dropped", "src/willitharness/isolation.py", 'SECRET_MARKERS = ("TOKEN", "SECRET", "KEY", "PASSWORD")', 'SECRET_MARKERS = ("TOKEN", "SECRET", "KEY")'),
    ("oauth-token-unlisted", "src/willitharness/isolation.py", '"ANTHROPIC_API_KEY", "CLAUDE_CODE_OAUTH_TOKEN", "ANTHROPIC_BASE_URL"', '"ANTHROPIC_API_KEY", "ANTHROPIC_BASE_URL"'),
    ("writes-not-denied", "src/willitharness/isolation.py", '        "(deny file-write*)",\n', ""),
    ("reads-not-denied", "src/willitharness/isolation.py", '        f"(deny file-read* {deny_reads})",\n', ""),
    ("world-not-writable", "src/willitharness/isolation.py", "writable = [world, *extra_writable]", "writable = list(extra_writable)"),
    ("ssh-folder-readable", "src/willitharness/isolation.py", 'SECRET_DIRECTORIES = (".ssh", ".aws"', 'SECRET_DIRECTORIES = (".aws"'),
    ("extra-folders-ignored", "src/willitharness/isolation.py", "writable = [world, *extra_writable]", "writable = [world]"),
    ("profile-not-first-argument", "src/willitharness/isolation.py", 'return ["sandbox-exec", "-p", profile, *command]', 'return ["sandbox-exec", *command]'),
)
