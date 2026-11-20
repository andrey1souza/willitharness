SOURCE = 'scripts/guards/bare_checkout.py'

TESTS = (
    'tests/guards/test_bare_checkout.py',
)

MUTANTS = (
    ('flag-not-required', SOURCE, 'if bare_value == BARE_VALUE and common_directory.name', 'if common_directory.name'),
    ('any-set-value-is-bare', SOURCE, 'if bare_value == BARE_VALUE and', 'if bare_value != "" and'),
    ('git-directory-name-not-required', SOURCE, ' and common_directory.name == GIT_DIRECTORY_NAME', ''),
    ('git-directory-need-not-exist', SOURCE, ' and common_directory.is_dir()', ''),
    ('problem-exits-clean', SOURCE, 'code = EXIT_BARE_CHECKOUT if problem else EXIT_CLEAN', 'code = EXIT_CLEAN'),
    ('worktree-reads-its-own-git-directory', SOURCE, '"--git-common-dir"', '"--git-dir"'),
    ('flag-not-normalised', SOURCE, '"--type=bool", ', ''),
    ('unset-flag-is-an-error', SOURCE, '(0, GIT_CONFIG_MISSING_KEY)', '(0,)'),
    ('message-names-the-git-directory', SOURCE, 'checkout = common_directory.parent', 'checkout = common_directory'),
    ('fix-names-the-wrong-value', SOURCE, '"Fix: run git config core.bare false in %s."', '"Fix: run git config core.bare true in %s."'),
    ('problem-not-printed', SOURCE, '        print(problem, file=sys.stderr)\n', '        pass\n'),
)
