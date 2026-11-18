TESTS = (
    'tests/unit',
    'tests/golden',
    'tests/property',
)

MUTANTS = (
    ('min-runs-5-to-1', 'src/willitharness/verdict.py', 'MIN_RUNS = 5', 'MIN_RUNS = 1'),
    ('z-1.96-to-1.0', 'src/willitharness/intervals.py', 'WILSON_Z = 1.96', 'WILSON_Z = 1.0'),
    ('swap-low-and-high', 'src/willitharness/intervals.py', 'low, high = difference - lower_reach, difference + upper_reach', 'low, high = difference + upper_reach, difference - lower_reach'),
    ('remove-wilson-clamp', 'src/willitharness/intervals.py', 'low = min(max(0.0, center - half_width), proportion)', 'low = center - half_width'),
    ('lower-bound-above-zero-to-at-least-zero', 'src/willitharness/verdict.py', 'if low > 0 else', 'if low >= 0 else'),
    ('swap-first-higher-and-first-lower', 'src/willitharness/verdict.py', 'Verdict.FIRST_HIGHER if low > 0 else Verdict.FIRST_LOWER if high < 0', 'Verdict.FIRST_LOWER if low > 0 else Verdict.FIRST_HIGHER if high < 0'),
    ('difference-interval-unordered', 'src/willitharness/intervals.py', '{low}, {high}"\n    return low, high\n', '{low}, {high}"\n    return high, low\n'),
    ('difference-without-negation-on-swap', 'src/willitharness/intervals.py', 'difference = first_rate - second_rate', 'difference = abs(first_rate - second_rate)'),
)
