from pathlib import Path

import build
import pytest
from willitharness.paths import PathOutsideRoot
from files import write_tree
from site_tree import site_files

RECORD = "build/gate_status.json"
EXPECTED_RECORD = (
    "{\n"
    '  "command": "scripts/site/build.py",\n'
    '  "gates": [\n'
    "    {\n"
    '      "label": "Tests",\n'
    '      "status": "counted",\n'
    '      "result": "3 collected"\n'
    "    },\n"
    "    {\n"
    '      "label": "Mutants",\n'
    '      "status": "counted",\n'
    '      "result": "2 listed"\n'
    "    },\n"
    "    {\n"
    '      "label": "Contract IDs covered",\n'
    '      "status": "passed",\n'
    '      "result": "49 covered"\n'
    "    },\n"
    "    {\n"
    '      "label": "Repository checks",\n'
    '      "status": "passed",\n'
    '      "result": "22 checks passed"\n'
    "    }\n"
    "  ]\n"
    "}\n"
)


def tree_without_record():
    return {name: text for name, text in site_files().items() if name != RECORD}


def test_check_passes_and_writes_only_the_generated_record(tmp_path, capsys):
    write_tree(tmp_path, tree_without_record())
    code = build.main(["--root", str(tmp_path), "--check"])
    output = capsys.readouterr().out
    assert code == 0, f"a good site must pass with exit 0, got exit {code} and {output!r}"
    assert sorted(path.name for path in (tmp_path / "build").iterdir()) == ["gate_status.json"], "--check writes no site, only the record"
    assert (tmp_path / RECORD).read_text() == EXPECTED_RECORD, f"the record holds this run's counts, got {(tmp_path / RECORD).read_text()}"
    assert output.startswith("site: checks passed, ") and "no site written" in output, f"got {output!r}"


def test_a_committed_status_file_is_ignored(tmp_path):
    stale = '{"command": "make check", "date": "2020-01-01", "gates": [{"label": "Tests", "status": "passed", "result": "1 passed"}]}\n'
    write_tree(tmp_path, {**tree_without_record(), "site/data/gate_status.json": stale})
    assert build.main(["--root", str(tmp_path), "--check"]) == 0, "a stale committed record cannot fail the check"
    assert (tmp_path / "site" / "data" / "gate_status.json").read_text() == stale, "the build never touches it"
    assert "1 passed" not in (tmp_path / RECORD).read_text(), "the page data comes from this run"


def test_adding_a_test_needs_no_regeneration(tmp_path, capsys):
    write_tree(tmp_path, {**tree_without_record(), "tests/test_more.py": "def test_d():\n    assert True\n"})
    code = build.main(["--root", str(tmp_path)])
    page = (tmp_path / "build" / "site" / "index.html").read_text()
    assert code == 0 and "4 collected" in page, f"a new test is counted at once, got exit {code}"
    assert "3 collected" not in page, "the old count is gone"


def test_build_writes_the_page_and_the_style(tmp_path, capsys):
    write_tree(tmp_path, tree_without_record())
    code = build.main(["--root", str(tmp_path)])
    written = sorted(path.name for path in (tmp_path / "build" / "site").iterdir())
    assert code == build.EXIT_BUILT and written == ["index.html", "style.css"], f"got exit {code} and {written}"
    assert "<h1>toolname</h1>" in (tmp_path / "build" / "site" / "index.html").read_text(), "the page holds the README title"
    assert capsys.readouterr().out.startswith('site: built {"index.html": '), "the build prints the sizes"


def test_a_problem_fails_the_check_and_the_build_and_writes_nothing(tmp_path, capsys):
    write_tree(tmp_path, site_files())
    (tmp_path / "site" / "src" / "style.css").write_text(":tmp_path { --bg: #FFFFFF; --text: #EEEEEE; --muted: #58584F; --link: #0B4F9C; --keep: #1B6B3A; --warn: #8A4B00; --bad: #A31F34; }")
    assert build.main(["--root", str(tmp_path), "--check"]) == 1, "low contrast fails the check with exit 1"
    assert build.main(["--root", str(tmp_path)]) == 1, "low contrast fails the build with exit 1"
    assert not (tmp_path / "build" / "site").exists(), "a failing build writes no site"
    printed = capsys.readouterr().out
    assert "site: --text on --bg measures" in printed, f"the problem is printed, got {printed!r}"


def test_an_output_outside_the_root_is_refused(tmp_path):
    write_tree(tmp_path, site_files())
    with pytest.raises(PathOutsideRoot, match="outside") as raised:
        build.main(["--root", str(tmp_path), "--output", "../elsewhere"])
    assert "../elsewhere" in str(raised.value), f"the refusal must name the path, got {raised.value}"
    assert not (tmp_path.parent / "elsewhere").exists(), "nothing is written outside the tmp_path"


def test_an_empty_build_is_refused(tmp_path):
    with pytest.raises(AssertionError, match="no files") as raised:
        build.write_site(tmp_path, Path("out"), {})
    assert "Fix" in str(raised.value), f"the failure must say how to fix it, got {raised.value}"
    assert raised.type is AssertionError, f"expected an assertion failure, got {raised.type}"


def test_a_record_without_counts_is_refused(tmp_path):
    with pytest.raises(AssertionError, match="got no counts") as raised:
        build.write_gate_status(tmp_path, {})
    assert "Fix" in str(raised.value), f"the failure must say how to fix it, got {raised.value}"
    assert not (tmp_path / RECORD).exists(), f"nothing is written, got {sorted(tmp_path.iterdir())}"
