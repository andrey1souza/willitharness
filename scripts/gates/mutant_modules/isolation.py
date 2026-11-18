PLATFORM = "darwin"
TESTS = ("tests/unit/test_isolation_unit.py", "tests/gates/test_sandbox_gate.py")

MUTANTS = (
    ("agent-shell-not-forced", "src/willitharness/isolation.py", "    kept[SHELL_VARIABLE] = AGENT_SHELL\n", ""),
    ("agent-shell-is-zsh", "src/willitharness/isolation.py", 'AGENT_SHELL = "/bin/bash"', 'AGENT_SHELL = "/bin/zsh"'),
    ("every-variable-passes", "src/willitharness/isolation.py", "if name in ALLOWED_VARIABLES or name.startswith(ALLOWED_PREFIXES)", "if True"),
    ("prefix-rule-dropped", "src/willitharness/isolation.py", "name in ALLOWED_VARIABLES or name.startswith(ALLOWED_PREFIXES)", "name in ALLOWED_VARIABLES"),
    ("writes-not-denied", "src/willitharness/isolation.py", '        "(deny file-write*)",\n', ""),
    ("reads-not-denied", "src/willitharness/isolation.py", '        f"(deny file-read* {deny_reads})",\n', ""),
    ("world-not-writable", "src/willitharness/isolation.py", "writable = [world, *extra_writable]", "writable = list(extra_writable)"),
    ("ssh-folder-readable", "src/willitharness/isolation.py", 'SECRET_DIRECTORIES = (".ssh", ".aws"', 'SECRET_DIRECTORIES = (".aws"'),
    ("extra-folders-ignored", "src/willitharness/isolation.py", "writable = [world, *extra_writable]", "writable = [world]"),
    ("profile-not-first-argument", "src/willitharness/isolation.py", 'return ["sandbox-exec", "-p", profile, *command]', 'return ["sandbox-exec", *command]'),
)
