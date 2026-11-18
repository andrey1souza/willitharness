TESTS = (
    'tests/unit/test_noise_unit.py',
    'tests/gates/test_analysis_outcomes.py',
    'tests/bdd/analysis/test_effect_with_noise.py',
)

SOURCE = 'src/willitharness/noise.py'

MUTANTS = (
    ('repeat-compared-with-the-loo-arm-itself', SOURCE, "counts[Cell(pair.loo, task)], counts[Cell(pair.repeat, task)])\n    assert", "counts[Cell(pair.loo, task)], counts[Cell(pair.loo, task)])\n    assert"),
    ('noise-read-from-another-task', SOURCE, "status = noise_status_of(counts[Cell(pair.loo, task)]", "status = noise_status_of(counts[Cell(pair.loo, sorted(counts)[0].task)]"),
    ('pair-picks-the-non-repeats', SOURCE, "if loo is not None and noise_target(arm.role) == loo]", "if loo is not None and noise_target(arm.role) != loo]"),
    ('loo-label-from-the-rule-arm', SOURCE, "if arm.role == ROLE_LEAVE_ONE_OUT]", "if arm.role != ROLE_LEAVE_ONE_OUT]"),
    ('plan-without-repeat-gets-a-pair', SOURCE, "return NoisePair(loo, repeats[0]) if repeats else None", "return NoisePair(loo, loo)"),
)
