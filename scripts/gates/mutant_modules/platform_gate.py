MUTANTS_SOURCE = 'scripts/gates/mutants.py'
CHECKS_SOURCE = 'scripts/gates/repo_checks.py'

TESTS = (
    'tests/gates/test_platform_checks.py',
    'tests/gates/test_mutants_platform.py',
)

MUTANTS = (
    ('platform-mismatch-not-skipped', MUTANTS_SOURCE, 'if PLATFORMS[name] not in (ANY_PLATFORM, platform)', 'if False'),
    ('every-module-skipped', MUTANTS_SOURCE, 'PLATFORMS[name] not in (ANY_PLATFORM, platform)', 'PLATFORMS[name] is not None or True'),
    ('skip-branch-runs-anyway', MUTANTS_SOURCE, '        if name in skipped:\n', '        if False:\n'),
    ('skip-reason-dropped', MUTANTS_SOURCE, 'f"skipped {name}: needs {PLATFORMS[name]}"', 'f"skipped {name}"'),
    ('skipped-modules-line-loses-names', MUTANTS_SOURCE, '", ".join(skipped)', '""'),
    ('skip-check-ignores-missing-declaration', CHECKS_SOURCE, 'if skipping and platforms[module] != DARWIN:', 'if False:'),
    ('skip-check-ignores-needless-declaration', CHECKS_SOURCE, 'if platforms[module] == DARWIN and not skipping:', 'if False:'),
    ('skip-pattern-matches-equality', CHECKS_SOURCE, 's*!=', 's*=='),
    ('platform-check-not-registered', CHECKS_SOURCE, '    "mutant-platforms": registered_platform_errors,\n', ''),
)
