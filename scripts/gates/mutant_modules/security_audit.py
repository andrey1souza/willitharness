SOURCE = 'scripts/gates/security_audit.py'

TESTS = (
    'tests/gates/test_security_audit.py',
)

MUTANTS = (
    ('inactive-ruleset-counts', SOURCE, 'ruleset.get("enforcement") != RULESET_ACTIVE or ruleset.get("target") != BRANCH_TARGET', 'ruleset.get("target") != BRANCH_TARGET'),
    ('excluded-main-counts', SOURCE, 'return included and not excluded', 'return included'),
    ('unprotected-rulesets-counted', SOURCE, 'for ruleset in rulesets if protects_main(ruleset) for rule', 'for ruleset in rulesets for rule'),
    ('deletion-rule-not-required', SOURCE, '    "deletion blocked": "deletion",\n', ''),
    ('only-first-check-required', SOURCE, 'for name in REQUIRED_CHECKS if name not in contexts', 'for name in REQUIRED_CHECKS[:1] if name not in contexts'),
    ('last-check-not-required', SOURCE, 'for name in REQUIRED_CHECKS if name not in contexts', 'for name in REQUIRED_CHECKS[:-1] if name not in contexts'),
    ('disabled-analysis-accepted', SOURCE, '.get("status") != ENABLED]', '.get("status") is None]'),
    ('sha-pinning-not-required', SOURCE, 'if settings["actions"].get(SHA_PINNING_KEY) is not True:', 'if False:'),
    ('write-permissions-accepted', SOURCE, 'READ_PERMISSIONS = "read"', 'READ_PERMISSIONS = "write"'),
    ('gh-failure-ignored', SOURCE, 'if completed.returncode != 0:', 'if False:'),
    ('failures-exit-zero', SOURCE, 'if errors:\n        return EXIT_FAILED', 'if False:\n        return EXIT_FAILED'),
    ('strict-false-accepted', SOURCE, 'if strict is not True:', 'if strict is False:'),
    ('strict-absent-accepted', SOURCE, 'if strict is not True:', 'if strict is not None and strict is not True:'),
    ('strict-check-skipped', SOURCE, 'if strict is not True:', 'if False:'),
    ('strict-wrong-parameter-read', SOURCE, 'STRICT_PARAMETER = "strict_required_status_checks_policy"', 'STRICT_PARAMETER = "strict_status_checks"'),
    ('strict-error-without-value', SOURCE, '{STRICT_PARAMETER} is {strict!r}, not True', '{STRICT_PARAMETER} is not True'),
)
