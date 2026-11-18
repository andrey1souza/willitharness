PLATFORM = "darwin"
TESTS = (
    "tests/unit/test_artifacts_unit.py",
    "tests/gates/test_agent_tools.py",
)

MUTANTS = (
    ('transcript-stored-unredacted', 'src/willitharness/artifacts.py', '    transcript.write_text(redact(artifacts.transcript, secrets))\n', '    transcript.write_text(artifacts.transcript)\n'),
    ('calls-stored-unredacted', 'src/willitharness/artifacts.py', '    calls.write_text(redact(artifacts.calls, secrets))\n', '    calls.write_text(artifacts.calls)\n'),
    ('redact-replaces-nothing', 'src/willitharness/artifacts.py', '        text = text.replace(secret, REDACTED)\n', '        pass\n'),
    ('key-variables-not-secret', 'src/willitharness/artifacts.py', 'SECRET_MARKERS = ("KEY", "TOKEN", "SECRET")', 'SECRET_MARKERS = ("TOKEN", "SECRET")'),
    ('token-variables-not-secret', 'src/willitharness/artifacts.py', 'SECRET_MARKERS = ("KEY", "TOKEN", "SECRET")', 'SECRET_MARKERS = ("KEY", "SECRET")'),
    ('secret-variables-not-secret', 'src/willitharness/artifacts.py', 'SECRET_MARKERS = ("KEY", "TOKEN", "SECRET")', 'SECRET_MARKERS = ("KEY", "TOKEN")'),
    ('secret-names-matched-case-sensitively', 'src/willitharness/artifacts.py', 'marker in name.upper()', 'marker in name'),
    ('empty-secret-kept', 'src/willitharness/artifacts.py', 'if value and any(marker', 'if any(marker'),
    ('shorter-secret-replaced-first', 'src/willitharness/artifacts.py', 'key=lambda value: (-len(value), value)', 'key=lambda value: (len(value), value)'),
    ('artifact-folder-lacks-rep', 'src/willitharness/artifacts.py', 'folder = inside(runs, f"{cell.arm}/{cell.task}/{rep}")', 'folder = inside(runs, f"{cell.arm}/{cell.task}")'),
    ('artifacts-outside-the-store', 'src/willitharness/artifacts.py', 'runs = inside(root, f"{STORE_DIR}/{plan_name}/{RUNS_DIR}")', 'runs = inside(root, f"{plan_name}/{RUNS_DIR}")'),
    ('attempts-overwrite-each-other', 'src/willitharness/artifacts.py', 'TRANSCRIPT_NAME = "transcript-{attempt}.jsonl"', 'TRANSCRIPT_NAME = "transcript.jsonl"'),
    ('artifact-folder-not-confined', 'src/willitharness/artifacts.py', 'folder = inside(runs, f"{cell.arm}/{cell.task}/{rep}")', 'folder = runs / f"{cell.arm}/{cell.task}/{rep}"'),
)
