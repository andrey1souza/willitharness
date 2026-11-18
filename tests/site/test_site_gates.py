import json

import extract
import gates
import pytest
import render
from files import write_tree
from site_tree import site_files

GOOD_COUNTS = {"Tests": 3, "Mutants": 2, "Contract IDs covered": 49, "Repository checks": 22}
GOOD_PAGE = '<html lang="en"><body><h1 id="top">T</h1><h2 id="a">A</h2><table><caption>c</caption></table><a href="#a">x</a></body></html>'


@pytest.fixture
def site(tmp_path):
    write_tree(tmp_path, site_files())
    data = extract.site_data(tmp_path)
    return data, render.render_site(tmp_path, data)


def test_a_good_site_has_no_problems(tmp_path, site):
    data, files = site
    assert gates.site_problems(tmp_path, files, data, GOOD_COUNTS) == [], "the fixture site must pass every gate"
    assert sorted(files) == ["index.html", "style.css"], f"the fixture site holds a page and a style, got {sorted(files)}"


def test_a_good_page_has_no_structure_problems():
    assert gates.structure_problems("a.html", GOOD_PAGE) == [], "a well formed page passes"
    assert gates.structure_problems("a.html", GOOD_PAGE.replace("<table>", "<table class='x'>")) == [], "a table with a caption passes"


@pytest.mark.parametrize(
    ("page", "fragment"),
    [
        (GOOD_PAGE.replace('id="a"', 'id="top"'), "repeats the id 'top'"),
        (GOOD_PAGE.replace("<table>", '<img src="x.png"><table>'), "img without alt"),
        (GOOD_PAGE.replace("<table>", '<link href="https://x.test/a.css"><table>'), "from outside"),
        (GOOD_PAGE.replace("<table>", '<script src="//x.test/a.js"></script><table>'), "from outside"),
        (GOOD_PAGE.replace("<caption>c</caption>", ""), "table without a caption"),
        (GOOD_PAGE.replace("<h2", "<h1").replace("</h2>", "</h1>"), "2 h1 headings"),
        (GOOD_PAGE.replace("<h2", "<h3").replace("</h2>", "</h3>"), "jumps from h1 to h3"),
        (GOOD_PAGE.replace("<h1", "<h2").replace("</h1>", "</h2>"), "0 h1 headings"),
    ],
)
def test_each_structure_fault_is_reported(page, fragment):
    problems = gates.structure_problems("a.html", page)
    assert any(fragment in problem for problem in problems), f"expected {fragment!r}, got {problems}"
    assert all(problem.startswith("a.html") for problem in problems), f"every problem names the page, got {problems}"


def test_an_external_anchor_is_allowed():
    page = GOOD_PAGE.replace("<table>", '<a href="https://example.test/">out</a><table>')
    assert gates.structure_problems("a.html", page) == [], "a visible link to another site is not a loaded resource"
    assert gates.structure_problems("a.html", page.replace("<a href", "<a data-x href")) == [], "attribute order does not matter"


def test_links_and_assets_must_resolve():
    files = {"index.html": '<a href="#a" id="a">x</a><a href="more.html#b">m</a><a href="gone.html">g</a><link href="style.css">', "more.html": '<h1 id="b">b</h1>', "style.css": "a{}"}
    assert gates.link_problems(files) == [
        "index.html:1 points at gone.html, but the site holds no gone.html. Rule: every link and asset resolves. Fix: add the file or correct the path."
    ], "only the missing page is reported"
    assert gates.link_problems({**files, "more.html": "<p>b</p>"})[0].startswith("index.html:1 points at more.html#b, but more.html has no id 'b'"), "a missing anchor is reported"


def test_a_missing_asset_is_reported():
    files = {"index.html": '<a id="a" href="#a">x</a><link rel="stylesheet" href="style.css"><img src="logo.svg" alt="">'}
    problems = gates.link_problems(files)
    assert [problem.split(" ")[3] for problem in problems] == ["style.css,", "logo.svg,"], f"both assets are missing, got {problems}"
    assert gates.link_problems({**files, "style.css": "", "logo.svg": ""}) == [], "present assets resolve"


def test_every_data_row_must_appear_on_the_page(tmp_path, site):
    data, files = site
    page = files["index.html"].replace("Reachability", "Reach").replace("The commands are stubs.", "x")
    problems = gates.coverage_problems("index.html", page.replace("stop-server", "stop"), data)
    assert [problem.split("'")[1] for problem in problems] == ["stop-server", "The commands are stubs."], f"two rows are missing, got {problems}"
    assert gates.coverage_problems("index.html", files["index.html"], data) == [], "the full page covers its data"


def test_a_row_must_cite_a_line_that_holds_it(tmp_path, site):
    data, files = site
    page = files["index.html"]
    wrong_line = page.replace('data-source="docs/contract.md:4"', 'data-source="docs/contract.md:5"')
    problems = gates.trace_problems(tmp_path, "index.html", wrong_line)
    assert len(problems) == 1 and "starting 'Q1' cites docs/contract.md:5" in problems[0], f"a wrong line is reported, got {problems}"
    assert gates.trace_problems(tmp_path, "index.html", page) == [], "the right lines pass"


@pytest.mark.parametrize(
    ("citation", "fragment"),
    [
        ('data-source="docs/contract.md:999"', "but the file has 20 lines"),
        ('data-source="docs/gone.md:1"', "not a file in the repository"),
        ('data-source="../outside.md:1"', "not a file in the repository"),
        ("", "has no data-source"),
    ],
)
def test_a_bad_citation_is_reported(tmp_path, site, citation, fragment):
    data, files = site
    page = files["index.html"].replace('data-source="docs/contract.md:4"', citation)
    problems = gates.trace_problems(tmp_path, "index.html", page)
    assert len(problems) == 1 and fragment in problems[0], f"expected {fragment!r}, got {problems}"
    assert problems[0].startswith("index.html: "), f"the problem names the page, got {problems[0]}"


def test_a_list_item_without_a_source_is_reported(tmp_path, site):
    data, files = site
    page = files["index.html"].replace('<li data-source="README.md:6">', "<li>")
    problems = gates.trace_problems(tmp_path, "index.html", page)
    assert len(problems) == 1 and "a <li> has no data-source" in problems[0], f"got {problems}"
    assert gates.trace_problems(tmp_path, "index.html", files["index.html"]) == [], "the original page passes"


def test_a_page_without_rows_fails_loudly(tmp_path, site):
    data, files = site
    with pytest.raises(AssertionError, match="no traceable rows") as raised:
        gates.trace_problems(tmp_path, "a.html", "<p>x</p>")
    assert "a.html" in str(raised.value), f"the failure must name the page, got {raised.value}"
    assert raised.type is AssertionError, f"expected an assertion failure, got {raised.type}"


def test_the_mutant_total_is_counted_from_the_tables(tmp_path):
    write_tree(tmp_path, {**site_files(), "scripts/gates/mutant_modules/two.py": "MUTANTS = (('c', 'x', 'p', 'q'),)\nOTHER = (1, 2, 3)\n"})
    assert gates.mutant_total(tmp_path) == 3, "two mutants in one module and one in another"
    assert gates.mutant_total(tmp_path) != len((1, 2, 3)) + 3, f"other tuples under {tmp_path} are not counted"


def test_a_missing_mutant_table_fails_loudly(tmp_path):
    write_tree(tmp_path, {**site_files(), "scripts/gates/mutant_modules/one.py": "X = 1\n"})
    with pytest.raises(AssertionError, match="lists no mutants") as raised:
        gates.mutant_total(tmp_path)
    assert "scripts/gates/mutant_modules" in str(raised.value), f"the failure must name the folder, got {raised.value}"
    assert raised.type is AssertionError, f"expected an assertion failure, got {raised.type}"


def test_counts_are_recomputed_from_real_gate_output(tmp_path):
    write_tree(tmp_path, site_files())
    assert gates.recomputed_counts(tmp_path) == GOOD_COUNTS, "tests, mutants, IDs and checks are read from the tree"
    write_tree(tmp_path, {"scripts/gates/trace_check.py": "print('trace-check: all 50 IDs covered')\n"})
    assert gates.recomputed_counts(tmp_path)["Contract IDs covered"] == 50, "a changed gate output changes the count"


def test_deselected_tests_are_not_counted(tmp_path):
    write_tree(tmp_path, {**site_files(), "tests/test_live.py": "import pytest\n\n\n@pytest.mark.live\ndef test_live():\n    assert True\n"})
    assert gates.collected_tests(tmp_path) == 3, "a live test is deselected, as in make check"
    assert gates.recomputed_counts(tmp_path)["Tests"] == 3, "the recomputed count agrees"


def test_a_gate_that_prints_nothing_countable_fails_loudly(tmp_path):
    write_tree(tmp_path, {**site_files(), "scripts/gates/repo_checks.py": "print('oops')\n"})
    with pytest.raises(AssertionError, match="printed no line matching") as raised:
        gates.recomputed_counts(tmp_path)
    assert "repo_checks.py" in str(raised.value), f"the failure must name the script, got {raised.value}"
    assert raised.type is AssertionError, f"expected an assertion failure, got {raised.type}"


def test_stale_status_is_reported(tmp_path, site):
    data, files = site
    rows = data["gates"]["rows"]
    assert gates.status_problems(rows, GOOD_COUNTS) == [], "a matching status passes"
    stale = gates.status_problems(rows, {**GOOD_COUNTS, "Tests": 4, "Contract IDs covered": 50})
    assert [problem.split(":")[0] for problem in stale] == ["Tests", "Contract IDs covered"], f"two counts are stale, got {stale}"
    assert "the status records 3 but the repository gives 4" in stale[0], f"got {stale[0]}"


def test_stale_mutant_totals_and_survivors_are_reported(tmp_path, site):
    data, files = site
    rows = [dict(row) for row in data["gates"]["rows"]]
    assert gates.status_problems(rows, {**GOOD_COUNTS, "Mutants": 3})[0].startswith("Mutants: the status records 2 of 2 killed but the tables hold 3"), "a changed total is stale"
    rows[1]["result"] = "1 of 2 mutants killed"
    problems = gates.status_problems(rows, GOOD_COUNTS)
    assert len(problems) == 1 and "records 1 of 2 killed" in problems[0], f"a survivor is reported, got {problems}"


def test_a_failed_record_is_reported(tmp_path, site):
    data, files = site
    rows = [dict(row) for row in data["gates"]["rows"]]
    rows[0]["status"] = "failed"
    problems = gates.status_problems(rows, GOOD_COUNTS)
    assert problems == ["Tests: the recorded status is 'failed'. Rule: the page shows only passing gate records. Fix: make the gate pass and record again."], f"got {problems}"
    assert gates.status_problems(data["gates"]["rows"], GOOD_COUNTS) == [], "passing rows pass"


def test_status_rows_and_counts_must_name_the_same_gates(tmp_path, site):
    data, files = site
    with pytest.raises(AssertionError, match="differ from counts") as raised:
        gates.status_problems(data["gates"]["rows"], {"Tests": 3})
    assert "Fix" in str(raised.value), f"the failure must say how to fix it, got {raised.value}"
    assert raised.type is AssertionError, f"expected an assertion failure, got {raised.type}"


def test_site_problems_collects_every_gate(tmp_path, site):
    data, files = site
    broken = {**files, "index.html": files["index.html"].replace("<h1>toolname</h1>", "<h1>toolname</h1><h1>again</h1><!-- why -->").replace("toy tasks", "toy tasks, proven")}
    (tmp_path / "site" / "extra.md").write_text("x")
    problems = gates.site_problems(tmp_path, broken, data, {**GOOD_COUNTS, "Tests": 9})
    joined = "\n".join(problems)
    for fragment in ("2 h1 headings", "holds a comment", "'proven'", "site/extra.md", "Tests: the status records 3 but the repository gives 9"):
        assert fragment in joined, f"expected {fragment!r} in the problems, got {joined}"
    assert json.dumps(data["live"]["claims"]).count("false") == 5, "the fixture marks every held-back claim false"


def test_the_template_may_not_type_a_number(tmp_path, site):
    data, files = site
    (tmp_path / "site" / "src" / "index.html").write_text((tmp_path / "site" / "src" / "index.html").read_text().replace("The four questions", "The 4 questions"))
    problems = gates.site_problems(tmp_path, files, data, GOOD_COUNTS)
    assert any("site/src/index.html:" in problem and "types the number 4 by hand" in problem for problem in problems), f"got {problems}"
    assert not any("shows the number" in problem for problem in problems), f"the rendered page is unchanged, got {problems}"


def test_a_site_without_the_page_fails_loudly(tmp_path, site):
    data, files = site
    with pytest.raises(AssertionError, match="lack index.html") as raised:
        gates.site_problems(tmp_path, {"style.css": files["style.css"]}, data, GOOD_COUNTS)
    assert "Fix" in str(raised.value), f"the failure must say how to fix it, got {raised.value}"
    assert raised.type is AssertionError, f"expected an assertion failure, got {raised.type}"
