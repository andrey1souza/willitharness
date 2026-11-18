TESTS = (
    'tests/unit/test_plan_unit.py',
    'tests/gates/test_plan_gate.py',
    'tests/bdd/test_plan_arms.py',
)

MUTANTS = (
    ('default-reps-20-to-10', 'src/willitharness/plan.py', 'DEFAULT_REPS = 20', 'DEFAULT_REPS = 10'),
    ('max-retries-2-to-3', 'src/willitharness/plan.py', 'MAX_RETRIES = 2', 'MAX_RETRIES = 3'),
    ('min-probe-runs-3-to-1', 'src/willitharness/plan.py', 'MIN_PROBE_RUNS = 3', 'MIN_PROBE_RUNS = 1'),
    ('noise-target-check-inverted', 'src/willitharness/plan.py', 'if target != loo_label:', 'if target == loo_label:'),
    ('noise-pair-without-loo-arm-allowed', 'src/willitharness/plan.py', '        if not leave_one_out:\n', '        if False:\n'),
    ('run-cap-may-exceed-budget', 'src/willitharness/plan.py', 'if run_cap > budget:', 'if run_cap > budget * 2:'),
    ('two-loo-arms-allowed', 'src/willitharness/plan.py', 'if len(leave_one_out) > 1:', 'if len(leave_one_out) > 2:'),
    ('repeated-labels-allowed-once', 'src/willitharness/plan.py', 'labels.count(label) > 1', 'labels.count(label) > 2'),
    ('unknown-channel-accepted', 'src/willitharness/plan.py', 'if channel not in CHANNELS:', 'if False:'),
    ('default-channel-changed', 'src/willitharness/plan.py', 'DEFAULT_CHANNEL = "file"', 'DEFAULT_CHANNEL = "hook"'),
)
