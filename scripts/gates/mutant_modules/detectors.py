TESTS = (
    'tests/unit/test_detectors_unit.py',
    'tests/bdd/test_detectors_scenarios.py',
    'tests/gates/test_detectors_gate.py',
)

SOURCE = 'src/willitharness/detectors.py'
LIFECYCLE = 'src/willitharness/lifecycle.py'
REAL_RUNNER = 'src/willitharness/real_runner.py'
BUDGET = 'src/willitharness/budget.py'

MUTANTS = (
    ('forbidden-never-matches', SOURCE, '        return any(call_matches(call, detector.action) for call in calls)\n', '        return False\n'),
    ('required-never-violated', SOURCE, 'return not any(call_matches(call, detector.action) for call in calls[:point_index(detector, calls)])', 'return False'),
    ('required-ignores-the-point', SOURCE, 'for call in calls[:point_index(detector, calls)])', 'for call in calls)'),
    ('point-is-the-last-edit', SOURCE, 'edits[0] if', 'edits[-1] if'),
    ('final-answer-point-is-the-first-edit', SOURCE, 'detector.before == POINT_FIRST_EDIT and edits', 'edits'),
    ('pipe-is-not-a-separator', SOURCE, 'r"&&|\\|\\||;|\\||\\n"', 'r"&&|\\|\\||;|\\n"'),
    ('newline-is-not-a-separator', SOURCE, 'r"&&|\\|\\||;|\\||\\n"', 'r"&&|\\|\\||;|\\|"'),
    ('semicolon-is-not-a-separator', SOURCE, 'r"&&|\\|\\||;|\\||\\n"', 'r"&&|\\|\\||\\||\\n"'),
    ('tool-name-never-matches', SOURCE, 'return call.tool == action or starts_with_action(call.command, action)', 'return starts_with_action(call.command, action)'),
    ('action-matches-anywhere-in-a-segment', SOURCE, 'segment[:len(words)] == words', 'all(word in segment for word in words)'),
    ('only-bash-calls-are-read', SOURCE, 'and isinstance(name, str) and bool(name)', 'and name == "Bash"'),
    ('executed-counts-every-log-line', SOURCE, 'sum(starts_with_action(line, detector.action) for line in logged_commands(calls_log))', 'len(logged_commands(calls_log))'),
    ('calls-contain-always-true', SOURCE, 'return any(starts_with_action(line, command) for line in logged_commands(calls_log))', 'return True'),
    ('unusable-run-is-judged-for-the-attempt', SOURCE, 'if parsed.usable_for_attempted_violation:', 'if True:'),
    ('unusable-run-is-judged-for-completion', SOURCE, 'if parsed.usable_for_completed and task_id in checks:', 'if task_id in checks:'),
    ('violation-flag-inverted', SOURCE, 'outcome[TARGET_OUTCOME] = attempted_violation(plan.rule.detector, calls_of(evidence.lines))', 'outcome[TARGET_OUTCOME] = not attempted_violation(plan.rule.detector, calls_of(evidence.lines))'),
    ('executed-count-not-stored', SOURCE, '        outcome[EXECUTED_KEY] = executed_count(plan.rule.detector, evidence.calls_log)\n', ''),
    ('completed-not-stored', SOURCE, '        outcome[COMPLETED_OUTCOME] = task_completed(checks[task_id], evidence.calls_log)\n', ''),
    ('rule-less-plan-is-judged', SOURCE, '    if plan.rule is None:\n        return {}\n', ''),
    ('judged-outcome-not-stored', LIFECYCLE, 'denials=parsed.denials, outcome=outcome)', 'denials=parsed.denials)'),
    ('calls-log-not-judged', LIFECYCLE, 'Evidence(tuple(lines), result.calls)', 'Evidence(tuple(lines), "")'),
    ('finished-drops-the-calls-log', LIFECYCLE, 'RunResult(tuple(lines), False, calls)', 'RunResult(tuple(lines), False)'),
    ('runner-drops-the-calls-log', REAL_RUNNER, 'output.splitlines(), calls)', 'output.splitlines(), "")'),
    ('over-cap-run-keeps-its-outcome', BUDGET, 'usable=dict(UNUSABLE_FLAGS), outcome={}, cost_usd=float(run_cap))\n    return replace(started, state=state', 'usable=dict(UNUSABLE_FLAGS), cost_usd=float(run_cap))\n    return replace(started, state=state'),
)
