TESTS = (
    'tests/unit/test_claude_agent_unit.py',
)

MUTANTS = (
    ('unisolated-command-gains-isolation', 'src/willitharness/claude_agent.py', '        "--max-budget-usd", str(budget),\n        "--tools", "",\n        "--no-session-persistence",\n', '        "--max-budget-usd", str(budget),\n        "--tools", "",\n        "--strict-mcp-config",\n        "--no-session-persistence",\n'),
    ('unisolated-command-keeps-tools', 'src/willitharness/claude_agent.py', '        "--max-budget-usd", str(budget),\n        "--tools", "",\n        "--no-session-persistence",\n', '        "--max-budget-usd", str(budget),\n        "--no-session-persistence",\n'),
    ('strict-mcp-config-dropped', 'src/willitharness/claude_agent.py', '        "--strict-mcp-config",\n', ''),
    ('slash-commands-allowed', 'src/willitharness/claude_agent.py', '        "--disable-slash-commands",\n', ''),
    ('session-persisted', 'src/willitharness/claude_agent.py', '        "--disable-slash-commands",\n        "--no-session-persistence",\n', '        "--disable-slash-commands",\n'),
    ('user-settings-loaded', 'src/willitharness/claude_agent.py', '"--setting-sources", "project,local"', '"--setting-sources", "user,project,local"'),
    ('budget-flag-dropped', 'src/willitharness/claude_agent.py', '        "--strict-mcp-config",\n        "--max-budget-usd", str(budget),\n', '        "--strict-mcp-config",\n'),
    ('tools-left-on', 'src/willitharness/claude_agent.py', '        "--max-budget-usd", str(budget),\n        "--tools", "",\n        "--disable-slash-commands",\n', '        "--max-budget-usd", str(budget),\n        "--disable-slash-commands",\n'),
    ('cost-ignored', 'src/willitharness/claude_agent.py', 'cost = float(event[COST_FIELD])', 'cost = 0.0'),
)
