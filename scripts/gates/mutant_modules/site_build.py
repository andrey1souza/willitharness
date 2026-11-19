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
    ('record-not-written', SOURCE, '    write_gate_status(root, counts)\n    data = site_data(root)', '    data = site_data(root)'),
    ('record-written-without-counts', SOURCE, 'json.dumps(gates.status_document(counts), indent=2)', 'json.dumps(gates.status_document({label: 1 for label in counts}), indent=2)'),
    ('empty-record-accepted', SOURCE, 'assert counts, "write_gate_status got no counts.', 'assert True, "write_gate_status got no counts.'),
)
