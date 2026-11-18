TESTS = (
    "tests/unit/test_stubs_unit.py",
    "tests/gates/test_agent_tools.py",
)

MUTANTS = (
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
)
