SOURCE = 'scripts/site/contrast.py'

TESTS = (
    'tests/site/test_contrast.py',
)

MUTANTS = (
    ('red-weight-changed', SOURCE, 'RED_WEIGHT = 0.2126', 'RED_WEIGHT = 0.3126'),
    ('gamma-exponent-changed', SOURCE, 'GAMMA_EXPONENT = 2.4', 'GAMMA_EXPONENT = 2.2'),
    ('flare-dropped', SOURCE, 'FLARE = 0.05', 'FLARE = 0.0'),
    ('linear-threshold-raised', SOURCE, 'LINEAR_THRESHOLD = 0.03928', 'LINEAR_THRESHOLD = 0.5'),
    ('one-direction-only', SOURCE, 'for first, second in ((foreground, background), (background, foreground)):', 'for first, second in ((foreground, background),):'),
    ('minimum-lowered', SOURCE, 'TEXT_MINIMUM = 4.5', 'TEXT_MINIMUM = 3.0'),
    ('missing-token-skipped', SOURCE, 'if foreground not in tokens:', 'if False:'),
    ('rounding-dropped', SOURCE, 'return round(result, DECIMALS)', 'return result'),
)
