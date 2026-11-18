TESTS = ("tests/gates/test_shell_live.py",)

MUTANTS = (
    ("alias-accepted", "scripts/gates/shell_live.py", "ALIAS_WORD not in reply.lower() and ", ""),
    ("clean-marker-ignored", "scripts/gates/shell_live.py", " and CLEAN_MARKER in reply", ""),
    ("cost-cap-ignored", "scripts/gates/shell_live.py", "if not shell_is_clean(reply) or cost > COST_CAP_USD:", "if not shell_is_clean(reply):"),
    ("failure-exits-zero", "scripts/gates/shell_live.py", "        print(NOT_PROVEN_MESSAGE)\n        return EXIT_FAILED", "        print(NOT_PROVEN_MESSAGE)\n        return EXIT_PASSED"),
    ("allowlist-widened", "scripts/gates/shell_live.py", 'ALLOWED_COMMANDS = ("type",)', 'ALLOWED_COMMANDS = ("type", "cat")'),
    ("bash-tool-dropped", "scripts/gates/shell_live.py", "claude_agent.tool_policy(False, ALLOWED_COMMANDS)", "claude_agent.PROBE_POLICY"),
)
