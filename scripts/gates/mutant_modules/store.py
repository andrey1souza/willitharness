TESTS = (
    'tests/unit/test_store_unit.py',
    'tests/gates/test_store_gate.py',
    'tests/property/test_store_properties.py',
    'tests/bdd/test_store_scenarios.py',
)

MUTANTS = (
    ('store-opened-in-write-mode', 'src/willitharness/store.py', 'APPEND_MODE = "a"', 'APPEND_MODE = "w"'),
    ('resume-ignores-existing-records', 'src/willitharness/store.py', '    counters = cell_counters(records)\n    missing = {}', '    counters = cell_counters(())\n    missing = {}'),
    ('attempts-pass-reps-plus-max-retries', 'src/willitharness/store.py', 'facts.reps + facts.max_retries - seen.attempts', 'facts.reps + facts.max_retries + 1 - seen.attempts'),
    ('attempt-cap-ignores-max-retries', 'src/willitharness/store.py', 'facts.reps + facts.max_retries - seen.attempts', 'facts.reps - seen.attempts'),
    ('unusable-runs-count-toward-reps', 'src/willitharness/store.py', 'if run.state is RunState.RECORDED_USABLE)', 'if run.state is not RunState.STARTED)'),
    ('in-flight-runs-not-counted', 'src/willitharness/store.py', 'facts.reps - seen.usable - seen.in_flight', 'facts.reps - seen.usable'),
    ('recorded-run-may-be-overwritten', 'src/willitharness/store.py', '    if prior.state is RunState.STARTED and record.state is not RunState.STARTED and same_run(prior, record):', '    if record.state is not RunState.STARTED:'),
    ('ended-run-may-change-cell', 'src/willitharness/store.py', 'and same_run(prior, record):', ':'),
    ('repeat-record-appended-again', 'src/willitharness/store.py', '    if prior == record:\n        return records', '    if prior == record:\n        return (*records, record)'),
    ('spent-counts-started-runs-only', 'src/willitharness/store.py', 'if run.state is not RunState.STARTED)', 'if run.state is RunState.STARTED)'),
    ('in-flight-lists-every-run', 'src/willitharness/store.py', 'for run in latest_by_run(records).values() if run.state is RunState.STARTED)', 'for run in latest_by_run(records).values())'),
)
