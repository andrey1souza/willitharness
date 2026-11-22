TESTS = (
    'tests/gates/test_s2_type_check.py',
)

SOURCE = 'scripts/gates/s2_type_check.py'
DECISION = 'src/willitharness/decision.py'

MUTANTS = (
    ('decide-takes-a-side-effects-parameter', DECISION, 'def decide(reach: Reach, effect: EffectResult, guard: GuardResult) -> Decision:', 'def decide(reach: Reach, effect: EffectResult, guard: GuardResult, side_effects=None) -> Decision:'),
    ('decide-takes-a-leading-side-effects-parameter', DECISION, 'def decide(reach: Reach, effect: EffectResult, guard: GuardResult) -> Decision:', 'def decide(side_effects, reach: Reach, effect: EffectResult, guard: GuardResult) -> Decision:'),
    ('decide-takes-a-variadic-parameter', DECISION, 'def decide(reach: Reach, effect: EffectResult, guard: GuardResult) -> Decision:', 'def decide(reach: Reach, effect: EffectResult, guard: GuardResult = GuardResult.GUARD_UNTESTED, *rest) -> Decision:'),
    ('extra-parameter-passes', SOURCE, 'if parameters == EXPECTED_PARAMETERS:', 'if set(EXPECTED_PARAMETERS) <= set(parameters):'),
    ('order-ignored', SOURCE, 'passed = parameters == EXPECTED_PARAMETERS', 'passed = set(parameters) == set(EXPECTED_PARAMETERS)'),
    ('failure-exits-zero', SOURCE, 'EXIT_FAILED = 1', 'EXIT_FAILED = 0'),
    ('failure-without-the-rule', SOURCE, 'Rule: S2, the decision takes no side-effect input. ', ''),
    ('failure-without-the-parameters', SOURCE, 'found = PARAMETER_SEPARATOR.join(parameters)', 'found = ""'),
    ('pass-line-reworded', SOURCE, 'decision parameters are exactly: {expected}', 'decision parameters are: {expected}'),
    ('expected-parameter-dropped', SOURCE, 'EXPECTED_PARAMETERS = ("reach", "effect", "guard")', 'EXPECTED_PARAMETERS = ("reach", "effect")'),
)
