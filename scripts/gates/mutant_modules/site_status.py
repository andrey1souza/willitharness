SOURCE = 'scripts/site/status.py'

TESTS = (
    'tests/site/test_status.py',
)

MUTANTS = (
    ('killed-counts-the-plan', SOURCE, 'killed = sum(int(done) for done, _ in MUTANTS_LINE.findall(log))', 'killed = sum(int(planned) for _, planned in MUTANTS_LINE.findall(log))'),
    ('first-match-wins', SOURCE, 'return found[-1]', 'return found[0]'),
    ('failed-tests-ignored', SOURCE, 'tests_failed = bool(TESTS_FAILED.search(log))', 'tests_failed = False'),
    ('survivors-pass', SOURCE, 'PASSED if killed == total else FAILED', 'PASSED'),
    ('unparsed-log-exits-zero', SOURCE, 'return EXIT_UNPARSED', 'return EXIT_WRITTEN'),
    ('empty-log-accepted', SOURCE, 'assert log.strip(),', 'assert True,'),
)
