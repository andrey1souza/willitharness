TESTS = (
    'tests/unit/test_arms_unit.py',
)

MUTANTS = (
    ('nested-sections-kept', 'src/willitharness/arms.py', 'len(matched.group(1)) <= level', 'len(matched.group(1)) < level'),
    ('repeated-heading-accepted', 'src/willitharness/arms.py', 'assert len(starts) == 1,', 'assert len(starts) >= 1,'),
    ('last-line-of-the-file-kept', 'src/willitharness/arms.py', '    end = len(lines)\n    for index', '    end = len(lines) - 1\n    for index'),
)
