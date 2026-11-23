TESTS = (
    'tests/gates/test_three_arm_report.py',
)

SOURCE = 'src/willitharness/three_arm_report.py'
REPORT = 'src/willitharness/report.py'
CLI = 'src/willitharness/cli.py'

MUTANTS = (
    ('remove-minimum-lowered', SOURCE, 'REMOVE_MIN_RUNS = 20', 'REMOVE_MIN_RUNS = 5'),
    ('remove-minimum-raised', SOURCE, 'REMOVE_MIN_RUNS = 20', 'REMOVE_MIN_RUNS = 21'),
    ('remove-minimum-excludes-the-limit', SOURCE, 'arms.nothing.runs) >= REMOVE_MIN_RUNS', 'arms.nothing.runs) > REMOVE_MIN_RUNS'),
    ('remove-needs-only-the-largest-arm', SOURCE, 'enough = min(arms.component.runs', 'enough = max(arms.component.runs'),
    ('remove-text-for-every-verdict', SOURCE, '    if verdict is not ArmVerdict.DELETE_CANDIDATE:\n        text = arm_verdict_text(verdict)', '    if False:\n        text = arm_verdict_text(verdict)'),
    ('remove-withheld-text-changed', SOURCE, 'NeedsMoreRuns: removal needs', 'Wait: removal needs'),
    ('three-arm-by-any-label', SOURCE, 'set(THREE_ARMS) <= {arm.label for arm in plan.arms}', 'bool(set(THREE_ARMS) & {arm.label for arm in plan.arms})'),
    ('trigger-counts-runs-without-a-transcript', SOURCE, 'fact.arm == ARM_COMPONENT and fact.fired is not None', 'fact.arm == ARM_COMPONENT'),
    ('missing-transcript-counts-as-not-fired', SOURCE, 'fired = None if lines is None else any(', 'fired = False if lines is None else any('),
    ('skill-call-inverted', SOURCE, 'any(call.tool == SKILL_TOOL for call in calls_of(lines))', 'any(call.tool != SKILL_TOOL for call in calls_of(lines))'),
    ('trigger-rate-for-a-component-that-is-no-skill', SOURCE, '    if channel != SKILL_CHANNEL:\n        return', '    if False:\n        return'),
    ('effect-counts-all-fired-runs-as-violations', SOURCE, 'violated = Counts(sum(fact.violated for fact in fired), len(fired))', 'violated = Counts(len(fired), len(fired))'),
    ('effect-compares-with-the-prompt-arm', SOURCE, 'nothing = [fact for fact in facts if fact.arm == ARM_NOTHING]', 'nothing = [fact for fact in facts if fact.arm == ARM_PROMPT]'),
    ('turns-from-the-first-result-line', SOURCE, 'last = turns[-1] if turns else None', 'last = turns[0] if turns else None'),
    ('turns-accept-a-flag', SOURCE, 'isinstance(last, int) and not isinstance(last, bool)', 'isinstance(last, int)'),
    ('turns-from-any-line', SOURCE, 'if load_event(line).get("type") == RESULT_EVENT]', 'if True]'),
    ('turns-mean-becomes-the-largest', SOURCE, 'mean turns {sum(measured) / len(measured):.1f}', 'mean turns {max(measured) / len(measured):.1f}'),
    ('cost-is-a-sum', SOURCE, 'mean cost ${sum(fact.cost for fact in runs) / len(runs):.4f}', 'mean cost ${sum(fact.cost for fact in runs):.4f}'),
    ('smallest-drop-becomes-the-largest', SOURCE, 'smallest = min(drops, default=None)', 'smallest = max(drops, default=None)'),
    ('drop-needs-the-other-arm-lower', SOURCE, 'verdict_of(other, Counts(violations, component_runs)) is Verdict.FIRST_HIGHER', 'verdict_of(other, Counts(violations, component_runs)) is Verdict.FIRST_LOWER'),
    ('detectable-minimum-excludes-five-runs', SOURCE, 'if min(other.runs, component_runs) < MIN_RUNS:\n        text', 'if min(other.runs, component_runs) <= MIN_RUNS:\n        text'),
    ('detectable-for-the-prompt-uses-nothing', SOURCE, '((ARM_PROMPT, arms.prompt), (ARM_NOTHING, arms.nothing))', '((ARM_PROMPT, arms.nothing), (ARM_NOTHING, arms.nothing))'),
    ('noise-line-dropped', SOURCE, 'is not measured separately.', 'is measured.'),
    ('decide-skips-the-finished-and-guard-checks', SOURCE, '    folder = decidable_folder(root, plan)\n    lines = tuple(three_arm_decision_line', '    folder = root / ".willitharness" / plan.name\n    lines = tuple(three_arm_decision_line'),
    ('decide-no-runs-not-refused', SOURCE, '    if not lines:\n        raise DecideRefused', '    if False:\n        raise DecideRefused'),
    ('report-skips-the-guard-check', REPORT, '    check_reportable(folder)\n    decidable_folder(root, plan)\n', '    check_reportable(folder)\n'),
    ('report-skips-the-finished-check', REPORT, '    check_reportable(folder)\n    decidable_folder(root, plan)\n', '    decidable_folder(root, plan)\n'),
    ('report-drops-the-limits', REPORT, '*three_arm_sections(folder, plan, records), limit_lines())', '*three_arm_sections(folder, plan, records))'),
    ('report-ignores-the-three-arms', REPORT, 'three_arm_report_text(root, plan) if is_three_arm(plan) else', 'three_arm_report_text(root, plan) if False else'),
    ('decide-ignores-the-three-arms', CLI, 'if is_three_arm(plan) else [decision_line', 'if False else [decision_line'),
)
