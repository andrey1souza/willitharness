TESTS = (
    'tests/unit/test_analysis_unit.py',
    'tests/bdd/test_reachability.py',
    'tests/golden',
)

MUTANTS = (
    ('unknown-rule-arm-may-report', 'src/willitharness/analysis.py', '        and facts.rule_reach is not Reach.UNKNOWN\n', '        and True\n'),
    ('loo-arm-always-valid', 'src/willitharness/analysis.py', '        and loo_arm_valid(facts.loo_probe)\n', '        and True\n'),
    ('noise-problem-still-reports', 'src/willitharness/analysis.py', '        and facts.noise is NoiseStatus.NOISE_OK\n', '        and True\n'),
    ('no-noise-pair-still-reports', 'src/willitharness/analysis.py', '        facts.has_noise_pair\n        and facts.noise', '        True\n        and facts.noise'),
    ('loo-message-changed', 'src/willitharness/analysis.py', '"LOO arm does not load its other rules; the effect cannot be reported"', '"LOO arm invalid"'),
    ('no-pair-message-changed', 'src/willitharness/analysis.py', '"no noise pair; add a repeat of arm {loo} with role noise_of:{loo}"', '"no noise pair"'),
)
