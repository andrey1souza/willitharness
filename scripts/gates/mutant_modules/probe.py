TESTS = (
    'tests/unit/test_probe_unit.py',
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
)
