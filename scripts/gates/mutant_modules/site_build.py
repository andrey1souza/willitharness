SOURCE = 'scripts/site/build.py'

TESTS = (
    'tests/site/test_build.py',
)

MUTANTS = (
    ('check-writes', SOURCE, 'if arguments.check:', 'if False:'),
    ('problems-do-not-stop-the-build', SOURCE, 'if problems:\n        return EXIT_PROBLEMS', 'if False:\n        return EXIT_PROBLEMS'),
    ('default-output-moved', SOURCE, 'DEFAULT_OUTPUT = Path("build") / "site"', 'DEFAULT_OUTPUT = Path("out")'),
    ('build-exits-nonzero', SOURCE, 'EXIT_BUILT = 0', 'EXIT_BUILT = 2'),
    ('empty-build-accepted', SOURCE, 'assert files, "write_site got no files.', 'assert True, "write_site got no files.'),
)
