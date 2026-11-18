TESTS = (
    'tests/gates/test_probe_live.py',
)

MUTANTS = (
    ('cost-cap-raised', 'scripts/gates/probe_live.py', 'COST_CAP_USD = 0.10', 'COST_CAP_USD = 10.0'),
    ('mismatch-ignored', 'scripts/gates/probe_live.py', '            if reach != expected[case.name]:', '            if False:'),
    ('exit-zero-on-mismatch', 'scripts/gates/probe_live.py', '    if mismatches:\n        return EXIT_FAILED', '    if False:\n        return EXIT_FAILED'),
    ('pass-line-changed', 'scripts/gates/probe_live.py', 'print("GATE G2.3 PASS")', 'print("ok")'),
)
