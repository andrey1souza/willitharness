from pathlib import Path

import build
import pytest
from willitharness.paths import PathOutsideRoot
from files import write_tree
from site_tree import site_files


def test_check_passes_and_writes_nothing(tmp_path, capsys):
    write_tree(tmp_path, site_files())
    code = build.main(["--root", str(tmp_path), "--check"])
    output = capsys.readouterr().out
    assert code == 0, f"a good site must pass with exit 0, got exit {code} and {output!r}"
    assert not (tmp_path / "build").exists(), "--check writes nothing"
    assert output.startswith("site: checks passed, ") and "nothing written" in output, f"got {output!r}"


def test_build_writes_the_page_and_the_style(tmp_path, capsys):
    write_tree(tmp_path, site_files())
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
    assert not (tmp_path / "build").exists(), "a failing build writes nothing"
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
