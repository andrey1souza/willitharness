TESTS = ("tests/unit/test_guard_hook_unit.py", "tests/gates/test_guard_hook_gate.py",)
SOURCE = "src/willitharness/guard_hook.py"

MUTANTS = (
    ("block-exit-code-is-one", SOURCE, "BLOCK_EXIT_CODE = 2", "BLOCK_EXIT_CODE = 1"),
    ("allow-exit-code-is-two", SOURCE, "ALLOW_EXIT_CODE = 0", "ALLOW_EXIT_CODE = 2"),
    ("matcher-dropped", SOURCE, '[{"matcher": BASH_TOOL, "hooks"', '[{"hooks"'),
    ("timeout-dropped", SOURCE, ', "timeout": HOOK_TIMEOUT_SECONDS}]}]', "}]}]"),
    ("event-renamed", SOURCE, 'HOOK_EVENT = "PreToolUse"', 'HOOK_EVENT = "PostToolUse"'),
    ("hook-type-renamed", SOURCE, 'HOOK_TYPE = "command"', 'HOOK_TYPE = "prompt"'),
    ("module-renamed", SOURCE, 'HOOK_MODULE = "willitharness.guard_hook"', 'HOOK_MODULE = "willitharness.guard"'),
    ("isolated-flag-dropped", SOURCE, 'ISOLATED_MODE_FLAG = "-I"', 'ISOLATED_MODE_FLAG = "-B"'),
    ("command-joined-without-quotes", SOURCE, "command = shlex.join([python, ISOLATED_MODE_FLAG, \"-m\", HOOK_MODULE, str(rules_path)])", "command = \" \".join([python, ISOLATED_MODE_FLAG, \"-m\", HOOK_MODULE, str(rules_path)])"),
    ("unreadable-call-allowed", SOURCE, "        return BLOCK_EXIT_CODE, UNREADABLE_CALL.format(call=call_text)", "        return ALLOW_EXIT_CODE, UNREADABLE_CALL.format(call=call_text)"),
    ("other-tool-judged-as-bash", SOURCE, "    if command is NOT_BASH:", "    if False:"),
    ("other-tool-blocked", SOURCE, "        return ALLOW_EXIT_CODE, \"\"\n    decision", "        return BLOCK_EXIT_CODE, UNREADABLE_CALL\n    decision"),
    ("tool-name-not-checked", SOURCE, '    if call["tool_name"] != BASH_TOOL:', "    if False:"),
    ("broken-rules-allowed", SOURCE, '"\\n")\n        return BLOCK_EXIT_CODE\n    code, message', '"\\n")\n        return ALLOW_EXIT_CODE\n    code, message'),
    ("message-not-written", SOURCE, "    if message:\n        standard_error.write", "    if False:\n        standard_error.write"),
    ("decision-ignored", SOURCE, "code = BLOCK_EXIT_CODE if decision.blocked else ALLOW_EXIT_CODE", "code = ALLOW_EXIT_CODE"),
    ("everything-blocked", SOURCE, "code = BLOCK_EXIT_CODE if decision.blocked else ALLOW_EXIT_CODE", "code = BLOCK_EXIT_CODE"),
    ("non-text-command-accepted", SOURCE, "result = command if isinstance(command, str) and command.strip() else UNREADABLE", "result = command if command else UNREADABLE"),
)
