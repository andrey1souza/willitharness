TESTS = (
    'tests/unit/test_claude_agent_unit.py',
    'tests/gates/test_agent_tools.py',
)

MUTANTS = (
    ('unisolated-command-gains-isolation', 'src/willitharness/claude_agent.py', '        "--max-budget-usd", str(budget),\n        "--tools", "",\n        "--no-session-persistence",\n', '        "--max-budget-usd", str(budget),\n        "--tools", "",\n        "--strict-mcp-config",\n        "--no-session-persistence",\n'),
    ('unisolated-command-keeps-tools', 'src/willitharness/claude_agent.py', '        "--max-budget-usd", str(budget),\n        "--tools", "",\n        "--no-session-persistence",\n', '        "--max-budget-usd", str(budget),\n        "--no-session-persistence",\n'),
    ('strict-mcp-config-dropped', 'src/willitharness/claude_agent.py', '        "--strict-mcp-config",\n', ''),
    ('slash-commands-allowed', 'src/willitharness/claude_agent.py', '        "--disable-slash-commands",\n', ''),
    ('session-persisted', 'src/willitharness/claude_agent.py', '        "--disable-slash-commands",\n        "--no-session-persistence",\n', '        "--disable-slash-commands",\n'),
    ('user-settings-loaded', 'src/willitharness/claude_agent.py', '"--setting-sources", "project,local"', '"--setting-sources", "user,project,local"'),
    ('budget-flag-dropped', 'src/willitharness/claude_agent.py', '        "--strict-mcp-config",\n        "--max-budget-usd", str(budget),\n', '        "--strict-mcp-config",\n'),
    ('tools-left-on', 'src/willitharness/claude_agent.py', '        *tool_flags(policy),\n        "--disable-slash-commands",\n', '        "--disable-slash-commands",\n'),
    ('cost-ignored', 'src/willitharness/claude_agent.py', 'cost = float(event[COST_FIELD])', 'cost = 0.0'),
    ('effect-tools-gain-write', 'src/willitharness/claude_agent.py', 'EFFECT_TOOLS = "Bash"', 'EFFECT_TOOLS = "Bash,Write"'),
    ('guard-tools-lose-edit', 'src/willitharness/claude_agent.py', 'GUARD_TOOLS = "Bash,Write,Edit"', 'GUARD_TOOLS = "Bash,Write"'),
    ('guard-tools-lose-bash', 'src/willitharness/claude_agent.py', 'GUARD_TOOLS = "Bash,Write,Edit"', 'GUARD_TOOLS = "Write,Edit"'),
    ('allow-pattern-loses-wildcard', 'src/willitharness/claude_agent.py', 'ALLOW_PATTERN = "Bash({command}:*)"', 'ALLOW_PATTERN = "Bash({command})"'),
    ('permission-mode-not-default', 'src/willitharness/claude_agent.py', 'PERMISSION_MODE = "default"', 'PERMISSION_MODE = "acceptEdits"'),
    ('permission-mode-dropped', 'src/willitharness/claude_agent.py', '        flags += ["--permission-mode", PERMISSION_MODE]\n', '        flags += []\n'),
    ('allowlist-dropped', 'src/willitharness/claude_agent.py', '        flags += ["--allowedTools", ",".join(policy.allowed)]\n', '        flags += []\n'),
    ('allowlist-unsorted-and-repeated', 'src/willitharness/claude_agent.py', 'for command in sorted(set(commands))', 'for command in commands'),
    ('probe-gets-permission-mode', 'src/willitharness/claude_agent.py', '    if policy.tools:\n        flags += ["--permission-mode", PERMISSION_MODE]\n', '    if True:\n        flags += ["--permission-mode", PERMISSION_MODE]\n'),
    ('probe-policy-has-bash', 'src/willitharness/claude_agent.py', 'PROBE_POLICY = ToolPolicy("", ())', 'PROBE_POLICY = ToolPolicy("Bash", ())'),
    ('version-exit-code-ignored', 'src/willitharness/claude_agent.py', '    if completed.returncode != 0 or not version:', '    if not version:'),
    ('empty-version-accepted', 'src/willitharness/claude_agent.py', '    if completed.returncode != 0 or not version:', '    if completed.returncode != 0:'),
    ('missing-binary-not-refused', 'src/willitharness/claude_agent.py', '    except (OSError, subprocess.TimeoutExpired) as error:', '    except subprocess.TimeoutExpired as error:'),
)
