import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TABLE_FILE = REPO_ROOT / "docs" / "mistakes-to-rules.md"
CAUGHT_SECTION = "## Mistakes caught by a rule"
NEXT_SECTION = "## Mistakes with no rule yet"
TEST_REFERENCE = re.compile(r"`(tests/[\w/]+\.py)::(\w+)`")


def caught_section_text():
    text = TABLE_FILE.read_text()
    start = text.index(CAUGHT_SECTION)
    end = text.index(NEXT_SECTION)
    assert start < end, "section order changed: %r must come before %r" % (CAUGHT_SECTION, NEXT_SECTION)
    return text[start:end]


def test_every_caught_row_names_a_test_that_exists():
    references = TEST_REFERENCE.findall(caught_section_text())
    assert references, "the table names no tests; every caught mistake needs one"
    for relative_path, test_name in references:
        test_file = REPO_ROOT / relative_path
        assert test_file.is_file(), "row names %s which does not exist" % (relative_path,)
        assert "def %s(" % test_name in test_file.read_text(), (
            "row names %s::%s but that function is not in the file" % (relative_path, test_name)
        )


def test_every_caught_row_has_a_test_cell():
    rows = [line for line in caught_section_text().splitlines() if line.startswith("| ") and "---" not in line]
    body_rows = rows[1:]
    assert body_rows, "the table has no rows"
    for row in body_rows:
        assert TEST_REFERENCE.search(row), "row has no test reference: %s" % (row[:80],)


def test_a_made_up_test_name_is_detected():
    fake_row = "| m | c | r | `tests/guards/test_push_window.py::test_that_does_not_exist` |"
    relative_path, test_name = TEST_REFERENCE.search(fake_row).groups()
    source = (REPO_ROOT / relative_path).read_text()
    assert "def %s(" % test_name not in source, (
        "the made-up name %r must not exist in %s (%d characters), or the check cannot fail"
        % (test_name, relative_path, len(source))
    )
