TESTS = (
    'tests/gates/test_fakeagent.py',
)

MUTANTS = (
    ('fallback-file-always-read', 'src/willitharness/fakeagent.py', 'chosen = primary or fallback', 'chosen = primary + fallback'),
    ('recall-ignored', 'src/willitharness/fakeagent.py', 'values[0] if values and draw < behavior.recall else', 'values[0] if values else'),
    ('walk-passes-the-boundary', 'src/willitharness/fakeagent.py', 'while chain[-1] != boundary:', 'while chain[-1] != chain[-1].parent:'),
    ('seed-ignored', 'src/willitharness/fakeagent.py', 'random.Random(f"{behavior.seed}:{run_index}")', 'random.Random()'),
    ('seed-message-changed', 'src/willitharness/fakeagent.py', '"seed required; pass --seed N"', '"seed needed"'),
    ('claude-file-not-read', 'src/willitharness/fakeagent.py', 'CONTEXT_FILE = "CLAUDE.md"', 'CONTEXT_FILE = "CLAUDE.txt"'),
)
