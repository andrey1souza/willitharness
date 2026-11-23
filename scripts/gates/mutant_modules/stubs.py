PLATFORM = "darwin"
TESTS = (
    "tests/unit/test_stubs_unit.py",
    "tests/gates/test_agent_tools.py",
    "tests/gates/test_real_runner.py",
)

MUTANTS = (
    ('guard-rules-copied-into-workspace', 'src/willitharness/stubs.py', 'CALLS_LOG, SYSTEM_PROMPT_NAME, GUARD_RULES_NAME}', 'CALLS_LOG, SYSTEM_PROMPT_NAME}'),
    ('guard-rules-in-working-directory', 'src/willitharness/stubs.py', 'path = run_root / GUARD_RULES_NAME\n    assert path.parent == run_root, f"the guard rules {path} are not directly under {run_root}"', 'path = run_root / "work" / GUARD_RULES_NAME'),
    ('system-prompt-file-copied-into-workspace', 'src/willitharness/stubs.py', 'CALLS_LOG, SYSTEM_PROMPT_NAME, GUARD_RULES_NAME}', 'CALLS_LOG, GUARD_RULES_NAME}'),
    ('wrapper-exits-nonzero', 'src/willitharness/stubs.py', '    "exit 0\\n"\n', '    "exit 1\\n"\n'),
    ('wrapper-logs-to-nowhere', 'src/willitharness/stubs.py', '>> {log}\\n', '>> /dev/null\\n'),
    ('wrapper-log-lacks-command-name', 'src/willitharness/stubs.py', "{{ printf '%s' {command}; ", "{{ printf '%s' x; "),
    ('wrapper-log-lacks-arguments', 'src/willitharness/stubs.py', "do printf ' %s' ", "do printf '' "),
    ('wrapper-prints-nothing', 'src/willitharness/stubs.py', '    "printf \'%s\' {output}\\n"\n', '    "printf \'%s\' \'\'\\n"\n'),
    ('wrapper-output-unquoted', 'src/willitharness/stubs.py', 'output=shlex.quote(output))', 'output=output)'),
    ('wrapper-not-executable', 'src/willitharness/stubs.py', 'WRAPPER_MODE = 0o755', 'WRAPPER_MODE = 0o644'),
    ('wrapper-body-empty', 'src/willitharness/stubs.py', '        wrapper.write_text(wrapper_text(command, output, log))\n', '        wrapper.write_text("")\n'),
    ('world-bin-folder-copied', 'src/willitharness/stubs.py', 'ignore=partial(reserved_at_top, resolved))', 'ignore=None)'),
    ('reserved-names-dropped-everywhere', 'src/willitharness/stubs.py', 'if Path(directory) == source else set()', 'if True else set()'),
    ('stub-folder-in-working-directory', 'src/willitharness/stubs.py', 'folder = run_root / BIN_NAME\n    assert folder.parent == run_root, f"the stub folder {folder} is not directly under {run_root}"', 'folder = run_root / "work" / BIN_NAME'),
    ('calls-log-in-working-directory', 'src/willitharness/stubs.py', 'path = run_root / CALLS_LOG\n    assert path.parent == run_root, f"the calls log {path} is not directly under {run_root}"', 'path = run_root / "work" / CALLS_LOG'),
    ('bin-name-not-reserved', 'src/willitharness/stubs.py', 'CONTROL_NAMES | {BIN_NAME, CALLS_LOG, SYSTEM_PROMPT_NAME, GUARD_RULES_NAME}', 'CONTROL_NAMES | {CALLS_LOG, SYSTEM_PROMPT_NAME, GUARD_RULES_NAME}'),
    ('calls-log-name-not-reserved', 'src/willitharness/stubs.py', 'CONTROL_NAMES | {BIN_NAME, CALLS_LOG, SYSTEM_PROMPT_NAME, GUARD_RULES_NAME}', 'CONTROL_NAMES | {BIN_NAME, SYSTEM_PROMPT_NAME, GUARD_RULES_NAME}'),
    ('control-names-not-reserved', 'src/willitharness/stubs.py', 'CONTROL_NAMES | {BIN_NAME, CALLS_LOG, SYSTEM_PROMPT_NAME, GUARD_RULES_NAME}', '{BIN_NAME, CALLS_LOG, SYSTEM_PROMPT_NAME, GUARD_RULES_NAME}'),
)
