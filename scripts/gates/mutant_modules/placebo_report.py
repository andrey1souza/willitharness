TESTS = (
    'tests/gates/test_placebo_report.py',
)

SOURCE = 'src/willitharness/three_arm_report.py'

MUTANTS = (
    ('plan-always-has-a-placebo', SOURCE, 'found = ARM_PLACEBO in {arm.label for arm in plan.arms}', 'found = True'),
    ('plan-never-has-a-placebo', SOURCE, 'found = ARM_PLACEBO in {arm.label for arm in plan.arms}', 'found = False'),
    ('content-section-dropped', SOURCE, '*placebo, trigger_lines(plan, facts)', 'trigger_lines(plan, facts)'),
    ('content-heading-changed', SOURCE, '"## Content against filler"', '"## Placebo"'),
    ('placebo-turns-and-cost-dropped', SOURCE, 'cost_turns_lines(facts, labels)', 'cost_turns_lines(facts)'),
    ('placebo-label-refused-in-cost-line', SOURCE, 'assert arm in (*THREE_ARMS, ARM_PLACEBO)', 'assert arm in THREE_ARMS'),
    ('decide-skips-the-content-line', SOURCE, 'if has_placebo(plan) else lines', 'if False else lines'),
    ('decide-prints-the-content-line-first', SOURCE, 'return (*lines, *(placebo_decision_line(arms) for arms in task_arms(records, ARM_PLACEBO))) if', 'return (*(placebo_decision_line(arms) for arms in task_arms(records, ARM_PLACEBO)), *lines) if'),
    ('report-reads-the-prompt-as-the-placebo', SOURCE, 'placebo_lines(task_arms(records, ARM_PLACEBO))', 'placebo_lines(task_arms(records, ARM_PROMPT))'),
    ('decide-reads-the-prompt-as-the-placebo', SOURCE, '(placebo_decision_line(arms) for arms in task_arms(records, ARM_PLACEBO))', '(placebo_decision_line(arms) for arms in task_arms(records, ARM_PROMPT))'),
    ('placebo-counts-show-the-component', SOURCE, '(arms.other_label, arms.other), (ARM_NOTHING', '(arms.other_label, arms.component), (ARM_NOTHING'),
    ('content-verdict-arms-swapped', SOURCE, 'content_verdict(arms.component, arms.other, arms.nothing)', 'content_verdict(arms.other, arms.component, arms.nothing)'),
    ('content-line-names-the-wrong-arm', SOURCE, 'against {ARM_PLACEBO}: {content_verdict_text', 'against {ARM_PROMPT}: {content_verdict_text'),
)
