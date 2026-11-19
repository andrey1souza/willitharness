import extract
import pytest
import render
from files import write_tree
from site_tree import site_files


@pytest.fixture
def built(tmp_path):
    write_tree(tmp_path, site_files())
    return render.render_site(tmp_path, extract.site_data(tmp_path))


def test_the_page_and_the_style_are_built(built):
    assert sorted(built) == ["index.html", "style.css"], f"a build holds the page and the style, got {sorted(built)}"
    assert built["index.html"].startswith("<!doctype html>") and "<h1>toolname</h1>" in built["index.html"], f"the page opens with the title from the README; got {built['index.html'][:300]!r}"


def test_question_rows_cite_the_contract_line(built):
    assert '<tr data-source="docs/contract.md:4"><td><span class="id">Q1</span></td><td>Reachability</td><td>is the text loaded?</td><td>Loaded or Masked</td></tr>' in built["index.html"], f"the first question row is rendered with its source; got {built['index.html'][:300]!r}"
    assert built["index.html"].count('data-source="docs/contract.md:') == 7, f"four questions and three decisions cite the contract; got {built['index.html'][:300]!r}"


def test_decisions_and_results_carry_a_word_and_a_tone(built):
    page = built["index.html"]
    assert '<span class="status warn">FixLoading</span>' in page, f"a fix decision is a warn word; got {page!r}"
    assert '<span class="status keep">Keep</span>' in page and '<span class="status keep">passed</span>' in page, f"keep and passed are keep words; got {page!r}"
    assert '<span class="status keep">NoiseOk</span>' in page, f"the noise word shows beside its tone; got {page!r}"


def test_live_rows_show_hits_and_runs(built):
    page = built["index.html"]
    assert "<td>C: 6 of 20 runs</td><td>B: 0 of 20 runs</td>" in page, f"the first live row shows hits of runs for both arms; got {page!r}"
    assert "Cost: $0.5." in page and "Runs per cell: 20." in page, f"the live header shows cost and reps from the data; got {page!r}"


def test_limits_render_code_spans_and_source_lines(built):
    page = built["index.html"]
    assert '<li data-source="README.md:6">The spike used toy tasks and one <code>small</code> model.</li>' in page, f"a README limit keeps its code span and its line; got {page!r}"
    assert '<li data-source="fixtures/results/g4_4.json:60">The commands are stubs.</li>' in page, f"a live limit cites the JSON line; got {page!r}"


def test_a_quote_in_the_description_is_escaped_in_the_attribute(tmp_path):
    write_tree(tmp_path, {**site_files(), "README.md": site_files()["README.md"].replace("Check whether the rules work.", 'Check "quoted" rules.')})
    page = render.render_site(tmp_path, extract.site_data(tmp_path))["index.html"]
    assert 'content="Check &quot;quoted&quot; rules."' in page, f"the attribute must escape quotes, got {page[:400]!r}"
    assert '<p class="lede">Check &quot;quoted&quot; rules.</p>' in page, f"the paragraph shows the same escaped text, got {page[:400]!r}"


def test_text_is_escaped():
    assert render.inline("a <b> & `x<y`") == "a &lt;b&gt; &amp; <code>x&lt;y</code>", "html in source text is escaped, also inside code spans"
    assert render.identifier("<i>") == '<td><span class="id">&lt;i&gt;</span></td>', "ids are escaped"


def test_an_unknown_status_word_is_a_warn_word():
    assert render.status_cell("Strange") == '<td><span class="status warn">Strange</span></td>', "an unknown word still shows, in warn"
    assert render.status_cell("failed") == '<td><span class="status bad">failed</span></td>', "failed is a bad word"


def test_hits_above_runs_fail_loudly():
    with pytest.raises(AssertionError, match="hits never exceed runs") as raised:
        render.arm_cell("C", 21, 20)
    assert "21 hits of 20 runs" in str(raised.value), f"the failure must show the values, got {raised.value}"
    assert raised.type is AssertionError, f"expected an assertion failure, got {raised.type}"


def test_a_template_placeholder_without_data_fails_loudly(tmp_path):
    write_tree(tmp_path, {**site_files(), "site/src/index.html": "$missing_value"})
    with pytest.raises(KeyError) as raised:
        render.render_site(tmp_path, extract.site_data(tmp_path))
    assert raised.value.args == ("missing_value",), f"the failure must name the placeholder, got {raised.value.args}"
    assert "missing_value" in str(raised.value), f"the failure must name the placeholder to add to page_values, got {raised.value}"
