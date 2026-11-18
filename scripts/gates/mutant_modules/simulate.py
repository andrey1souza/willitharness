TESTS = (
    'tests/gates/test_simulate_gate.py',
)

SOURCE = 'scripts/gates/simulate.py'

MUTANTS = (
    ('false-positive-limit-lifted', SOURCE, "FALSE_POSITIVE_LIMIT = 0.08", "FALSE_POSITIVE_LIMIT = 1.0"),
    ('power-minimum-dropped', SOURCE, "POWER_MINIMUM = 0.95", "POWER_MINIMUM = 0.0"),
    ('gate-passes-on-either-bound', SOURCE, "passed = false_positive <= FALSE_POSITIVE_LIMIT and power >= POWER_MINIMUM", "passed = false_positive <= FALSE_POSITIVE_LIMIT or power >= POWER_MINIMUM"),
    ('z-ignored-by-the-simulation', SOURCE, "setup.z) in scenario.wanted", "WILSON_Z) in scenario.wanted"),
    ('seed-ignored', SOURCE, "generator = random.Random(seed)", "generator = random.Random(0)"),
    ('equal-rate-changed', SOURCE, "EQUAL_RATE = 0.5", "EQUAL_RATE = 0.4"),
    ('false-positive-counts-only-one-direction', SOURCE, "Scenario(EQUAL_RATE, EQUAL_RATE, DECISIVE_VERDICTS)", "Scenario(EQUAL_RATE, EQUAL_RATE, POWER_VERDICTS)"),
    ('power-run-with-equal-rates', SOURCE, "Scenario(HIGH_RATE, LOW_RATE, POWER_VERDICTS)", "Scenario(HIGH_RATE, HIGH_RATE, POWER_VERDICTS)"),
    ('failure-message-dropped', SOURCE, "    if code != EXIT_PASSED:", "    if False:"),
)
