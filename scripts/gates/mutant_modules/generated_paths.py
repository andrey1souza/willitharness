SOURCE = 'scripts/gates/repo_checks.py'

TESTS = (
    'tests/gates/test_generated_paths.py',
)

MUTANTS = (
    ('status-file-not-listed', SOURCE, ', Path("site") / "data" / "gate_status.json")', ')'),
    ('generated-folder-not-listed', SOURCE, 'GENERATED_PATHS = (Path("formal") / "tla" / "generated", ', 'GENERATED_PATHS = ('),
    ('exact-file-not-matched', SOURCE, 'name == generated.as_posix() or ', ''),
    ('folder-contents-not-matched', SOURCE, ' or name.startswith(f"{generated.as_posix()}/")', ''),
    ('name-prefix-matched', SOURCE, 'name.startswith(f"{generated.as_posix()}/")', 'name.startswith(generated.as_posix())'),
)
