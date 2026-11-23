TESTS = (
    'tests/unit/test_three_arm_unit.py',
    'tests/golden/test_golden_tables.py',
)

SOURCE = 'src/willitharness/three_arm.py'

MUTANTS = (
    ('insurance-threshold-too-low', SOURCE, 'INSURANCE_MAX_RATE = 0.05', 'INSURANCE_MAX_RATE = 0.0'),
    ('insurance-threshold-too-high', SOURCE, 'INSURANCE_MAX_RATE = 0.05', 'INSURANCE_MAX_RATE = 0.5'),
    ('insurance-excludes-the-threshold', SOURCE, 'nothing.rate() <= INSURANCE_MAX_RATE', 'nothing.rate() < INSURANCE_MAX_RATE'),
    ('empty-arm-counts-as-clean', SOURCE, 'return nothing.runs >= 1 and nothing.rate()', 'return nothing.runs < 1 or nothing.rate()'),
    ('insurance-never-given', SOURCE, '    elif nothing_clean:\n        result = ArmVerdict.INSURANCE_KEEP', '    elif False:\n        result = ArmVerdict.INSURANCE_KEEP'),
    ('insurance-before-small-n', SOURCE, '    if small:\n        result = ArmVerdict.INCONCLUSIVE\n    elif nothing_clean:', '    if nothing_clean:\n        result = ArmVerdict.INSURANCE_KEEP\n    elif small:'),
    ('small-n-in-prompt-comparison-ignored', SOURCE, 'Verdict.INCONCLUSIVE_SMALL_N in (prompt_vs_component, nothing_vs_component)', 'Verdict.INCONCLUSIVE_SMALL_N is nothing_vs_component'),
    ('small-n-in-nothing-comparison-ignored', SOURCE, 'Verdict.INCONCLUSIVE_SMALL_N in (prompt_vs_component, nothing_vs_component)', 'Verdict.INCONCLUSIVE_SMALL_N is prompt_vs_component'),
    ('keep-needs-more-than-beating-the-prompt', SOURCE, '    elif prompt_vs_component is Verdict.FIRST_HIGHER:\n        result = ArmVerdict.KEEP_COMPONENT', '    elif prompt_vs_component is Verdict.FIRST_HIGHER and nothing_vs_component is Verdict.FIRST_HIGHER:\n        result = ArmVerdict.KEEP_COMPONENT'),
    ('keep-when-component-is-worse', SOURCE, 'prompt_vs_component is Verdict.FIRST_HIGHER:\n        result = ArmVerdict.KEEP_COMPONENT', 'prompt_vs_component is not Verdict.INCONCLUSIVE:\n        result = ArmVerdict.KEEP_COMPONENT'),
    ('worse-than-prompt-not-inconclusive', SOURCE, '    elif prompt_vs_component is Verdict.FIRST_LOWER:\n        result = ArmVerdict.INCONCLUSIVE\n', '    elif prompt_vs_component is Verdict.FIRST_LOWER:\n        result = ArmVerdict.REPLACE_WITH_PROMPT\n'),
    ('replace-without-beating-nothing', SOURCE, '    elif nothing_vs_component is Verdict.FIRST_HIGHER:\n        result = ArmVerdict.REPLACE_WITH_PROMPT', '    elif nothing_vs_component is not Verdict.FIRST_LOWER:\n        result = ArmVerdict.REPLACE_WITH_PROMPT'),
    ('equal-to-nothing-replaced', SOURCE, '    else:\n        result = ArmVerdict.DELETE_CANDIDATE', '    else:\n        result = ArmVerdict.REPLACE_WITH_PROMPT'),
    ('worse-than-nothing-not-deleted', SOURCE, '    elif nothing_vs_component is Verdict.FIRST_LOWER:\n        result = ArmVerdict.DELETE_CANDIDATE', '    elif nothing_vs_component is Verdict.FIRST_LOWER:\n        result = ArmVerdict.INCONCLUSIVE'),
    ('worse-than-nothing-checked-after-keep', SOURCE, '    elif nothing_vs_component is Verdict.FIRST_LOWER:\n        result = ArmVerdict.DELETE_CANDIDATE\n    elif prompt_vs_component is Verdict.FIRST_HIGHER:\n        result = ArmVerdict.KEEP_COMPONENT', '    elif prompt_vs_component is Verdict.FIRST_HIGHER:\n        result = ArmVerdict.KEEP_COMPONENT\n    elif nothing_vs_component is Verdict.FIRST_LOWER:\n        result = ArmVerdict.DELETE_CANDIDATE'),
    ('worse-than-nothing-before-insurance', SOURCE, '    elif nothing_clean:\n        result = ArmVerdict.INSURANCE_KEEP\n    elif nothing_vs_component is Verdict.FIRST_LOWER:\n        result = ArmVerdict.DELETE_CANDIDATE', '    elif nothing_vs_component is Verdict.FIRST_LOWER:\n        result = ArmVerdict.DELETE_CANDIDATE\n    elif nothing_clean:\n        result = ArmVerdict.INSURANCE_KEEP'),
    ('arms-swapped-in-prompt-comparison', SOURCE, 'verdict_of(prompt, component), verdict_of(nothing, component)', 'verdict_of(component, prompt), verdict_of(nothing, component)'),
    ('arms-swapped-in-nothing-comparison', SOURCE, 'verdict_of(prompt, component), verdict_of(nothing, component)', 'verdict_of(prompt, component), verdict_of(component, nothing)'),
    ('clean-read-from-the-component', SOURCE, 'nothing_is_clean(nothing))\n    assert result in', 'nothing_is_clean(component))\n    assert result in'),
    ('policy-text-dropped', SOURCE, 'text = INSURANCE_TEXT if verdict is ArmVerdict.INSURANCE_KEEP else verdict.value', 'text = verdict.value'),
)
