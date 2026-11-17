from fnmatch import fnmatch
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
IGNORE_FILE = REPO_ROOT / ".gitignore"
WATCHER_FILES = [".testmondata", ".testmondata-shm", ".testmondata-wal"]
NOT_WATCHER_FILE = "src/willitharness/intervals.py"


def ignored(name, patterns):
    return any(fnmatch(name, pattern) for pattern in patterns)


def patterns():
    lines = IGNORE_FILE.read_text().splitlines()
    return [line for line in lines if line and not line.startswith("#")]


def test_files_written_by_the_overwatch_python_watcher_are_ignored():
    found = patterns()
    for name in WATCHER_FILES:
        assert ignored(name, found), (
            "%s is written by the overwatch pytest watcher and would leave the tree dirty, "
            "so TCR could not judge edits; patterns are %r" % (name, found)
        )


def test_the_matcher_does_not_ignore_source_files():
    found = patterns()
    assert not ignored(NOT_WATCHER_FILE, found), (
        "%s must not match any ignore pattern, or the check cannot fail; patterns are %r"
        % (NOT_WATCHER_FILE, found)
    )
