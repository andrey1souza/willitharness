TESTS = (
    'tests/gates/test_decide_command.py',
    'tests/gates/test_decide_guard_arm.py',
)

DECIDE_PLAN = 'src/willitharness/decide_plan.py'
CLI = 'src/willitharness/cli.py'
DECIDE_ALL = 'scripts/gates/decide_all.py'

MUTANTS = (
    ('decide-skips-the-state-check', DECIDE_PLAN, "    if state not in ANALYZABLE:", "    if False:"),
    ('decide-assumes-the-guard-matches', DECIDE_PLAN, "decide(reach, row.effect, guard))", "decide(reach, row.effect, GuardResult.GUARD_MATCHES_RULE))"),
    ('decide-ignores-the-guard-evidence', DECIDE_PLAN, "guard_reading(plan, records, calls, rules).result if rules and complete else GuardResult.GUARD_UNTESTED", "GuardResult.GUARD_MATCHES_RULE"),
    ('decide-ignores-missing-calls', DECIDE_PLAN, "if rules and complete else", "if rules else"),
    ('decide-ignores-missing-rules', DECIDE_PLAN, "if rules and complete else", "if complete else"),
    ('decide-ignores-the-recorded-reach', DECIDE_PLAN, "rule_decision_of(row, reach.get(row.second, Reach.UNKNOWN), guard)", "rule_decision_of(row, Reach.LOADED, guard)"),
    ('decide-reads-the-wrong-outcome', DECIDE_PLAN, "if row.outcome == TARGET_OUTCOME]", "if row.outcome != TARGET_OUTCOME]"),
    ('decide-hides-the-decision', CLI, '    print("\\n".join(lines))\n    assert lines', '    assert lines'),
    ('decide-refusal-exits-zero', CLI, "AnalysisError, DecideRefused) as error:\n        print(str(error), file=sys.stderr)\n        return EXIT_DOMAIN_FAILURE", "AnalysisError, DecideRefused) as error:\n        print(str(error), file=sys.stderr)\n        return EXIT_OK"),
    ('decide-analysis-error-not-caught', CLI, "LifecycleRefused, AnalysisError, DecideRefused)", "LifecycleRefused, DecideRefused)"),
    ('decide-not-routed', CLI, 'if command == ["decide"]:', 'if command == ["decide-off"]:'),
    ('decide-all-checks-nothing', DECIDE_ALL, "decision_mismatches(rows, decide_function)", "decision_mismatches(rows, decide)"),
    ('decide-all-prints-the-last-mismatch', DECIDE_ALL, "found[0]", "found[-1]"),
    ('decide-all-mismatch-exits-zero', DECIDE_ALL, "        return EXIT_MISMATCH", "        return EXIT_EQUAL"),
)
