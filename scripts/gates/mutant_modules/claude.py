TESTS = (
    'tests/unit/test_claude_agent_unit.py',
)

MUTANTS = (
    ('strict-mcp-config-dropped', 'src/willitharness/claude_agent.py', '        "--strict-mcp-config",\n', ''),
    ('slash-commands-allowed', 'src/willitharness/claude_agent.py', '        "--disable-slash-commands",\n', ''),
    ('session-persisted', 'src/willitharness/claude_agent.py', '        "--no-session-persistence",\n', ''),
    ('user-settings-loaded', 'src/willitharness/claude_agent.py', '"--setting-sources", "project,local"', '"--setting-sources", "user,project,local"'),
    ('budget-flag-dropped', 'src/willitharness/claude_agent.py', '        "--max-budget-usd", str(budget),\n', ''),
    ('tools-left-on', 'src/willitharness/claude_agent.py', '        "--tools", "",\n', ''),
    ('cost-ignored', 'src/willitharness/claude_agent.py', 'cost = float(event[COST_FIELD])', 'cost = 0.0'),
)
