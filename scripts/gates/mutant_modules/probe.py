TESTS = (
    'tests/unit/test_probe_unit.py',
    'tests/gates/test_probe_command.py',
    'tests/bdd/test_reachability.py',
    'tests/golden',
    'tests/property',
)

MUTANTS = (
    ('control-token-check-dropped', 'src/willitharness/probe.py', 'if runs < MIN_PROBE_RUNS or control_hits > 0:', 'if runs < MIN_PROBE_RUNS:'),
    ('two-of-three-accepted-as-loaded', 'src/willitharness/probe.py', 'elif target_hits == runs:', 'elif target_hits >= runs - 1:'),
    ('unusable-runs-counted', 'src/willitharness/probe.py', 'usable = [run for run in runs if run.usable]', 'usable = list(runs)'),
    ('loo-probe-accepts-unknown', 'src/willitharness/probe.py', 'result = loo_probe is Reach.LOADED\n    assert result ==', 'result = loo_probe is not Reach.MASKED\n    assert result =='),
    ('error-result-counted-usable', 'src/willitharness/probe.py', 'or last.get("is_error"):', 'or False:'),
    ('control-message-changed', 'src/willitharness/probe.py', '"control token appeared; the probe cannot be trusted"', '"control seen"'),
    ('one-run-too-few-accepted', 'src/willitharness/probe.py', 'if requested < MIN_PROBE_RUNS:', 'if requested < MIN_PROBE_RUNS - 1:'),
    ('probe-never-records-the-result', 'src/willitharness/cli.py', '    if site is not None:\n        recorded_state', '    if False:\n        recorded_state'),
    ('probe-records-a-fixed-result', 'src/willitharness/cli.py', 'record_reachability(site, arguments.arm, result.reach)', 'record_reachability(site, arguments.arm, type(result.reach).LOADED)'),
    ('unknown-arm-checked-after-the-probe', 'src/willitharness/cli.py', 'if arm not in labels:', 'if False:'),
    ('unknown-arm-exits-zero', 'src/willitharness/cli.py', 'return None, EXIT_DOMAIN_FAILURE\n    state = read_state', 'return None, EXIT_OK\n    state = read_state'),
    ('result-recorded-after-the-run-started', 'src/willitharness/cli.py', 'if state not in PRE_RUN_ORDER:', 'if False:'),
    ('plan-without-arm-accepted', 'src/willitharness/cli.py', 'if (arguments.plan is None) != (arguments.arm is None):', 'if False:'),
    ('run-refusal-names-no-command', 'src/willitharness/lifecycle.py', 'Fix: run willitharness probe --plan <plan.json> --arm', 'probe the arm and record the result'),
    ('run-summary-counts-records', 'src/willitharness/cli.py', '{len(latest_by_run(records))} runs', '{len(records)} runs'),
)
