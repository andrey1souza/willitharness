import json

import extract
import pytest
import render
from files import write_tree
from site_tree import LIVE, site_files


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
    assert '<li data-source="README.md:35">The spike used toy tasks and one <code>small</code> model.</li>' in page, f"a README limit keeps its code span and its line; got {page!r}"
    assert '<li data-source="fixtures/results/g4_4.json:76">The commands are stubs.</li>' in page, f"a live limit cites the JSON line; got {page!r}"


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


def test_the_current_run_the_detector_and_the_history_come_from_the_data_file(built):
    page = built["index.html"]
    assert "Run 2 counted these commands as a violation: <code>pkill, pgrep -f</code>." in page, f"the page names the run and its detector; got {page!r}"
    assert '<tr data-source="fixtures/results/g4_4.json:65"><td>before the fixes</td><td><span class="id">1</span></td><td>bare pkill only</td><td>$0.7</td><td>stop-server C 5 of 20</td></tr>' in page, f"the earlier run is a history row citing its line; got {page!r}"
    assert '<li data-source="fixtures/results/g4_4.json:72">The narrow detector counted only <code>pkill</code>.</li>' in page, f"the explanation cites its line; got {page!r}"


def test_the_spike_comparison_follows_the_numbers_and_says_no_match_when_they_differ(built):
    page = built["index.html"]
    assert "Run 2 stop-server rate: 30 percent of arm C runs. The spike read 83 percent (docs/research/spike.md). The rate does not match the spike&#x27;s." in page or "does not match the spike's." in page, f"6 of 20 against 83 percent must read no match; got {page!r}"
    assert "The rate matches the spike" not in page, f"a far rate must not claim a match; got {page!r}"


def with_stop_server_hits(tmp_path, hits, matches):
    rows = [dict(row, first_hits=hits) if row["task"] == "stop-server" else row for row in LIVE["rows"]]
    document = dict(LIVE, rows=rows, matches_spike=matches, stop_server_percent=round(100 * hits / 20))
    write_tree(tmp_path, {**site_files(), "fixtures/results/g4_4.json": json.dumps(document, indent=2) + "\n"})
    return tmp_path


def test_a_rate_within_the_tolerance_of_the_spike_reads_as_a_match(tmp_path):
    root = with_stop_server_hits(tmp_path, 16, True)
    page = render.render_site(root, extract.site_data(root))["index.html"]
    assert "stop-server rate: 80 percent of arm C runs." in page and "The rate matches the spike" in page, f"16 of 20 is 80 percent and within 5 points of 83; got {page!r}"


@pytest.mark.parametrize(("hits", "claimed"), [(6, True), (16, False)])
def test_a_match_claim_that_disagrees_with_the_numbers_fails_loudly(tmp_path, hits, claimed):
    root = with_stop_server_hits(tmp_path, hits, claimed)
    with pytest.raises(AssertionError, match="the match claim follows the numbers") as raised:
        render.render_site(root, extract.site_data(root))
    assert "matches_spike" in str(raised.value), f"the failure must name the field, got {raised.value}"


def test_a_percent_that_disagrees_with_its_row_fails_loudly(tmp_path):
    write_tree(tmp_path, {**site_files(), "fixtures/results/g4_4.json": json.dumps(dict(LIVE, stop_server_percent=80), indent=2) + "\n"})
    with pytest.raises(AssertionError, match="the percent follows the row") as raised:
        render.render_site(tmp_path, extract.site_data(tmp_path))
    assert "6 of 20 runs is 30 percent" in str(raised.value), f"the failure must show the row and the percent, got {raised.value}"


def test_the_blocks_follow_the_reading_order(built):
    page = built["index.html"]
    anchors = ["what", "works", "offline", "questions", "decisions", "gates", "live", "limits", "isolation"]
    positions = [page.index(f'id="{anchor}"') for anchor in anchors]
    assert positions == sorted(positions), f"the ids {anchors} must appear in this order, got positions {positions}"
    assert page.index("<footer>") > positions[-1], f"the footer must come after the last id at position {positions[-1]}"


def test_the_summary_the_commands_and_the_quick_start_come_from_the_readme(built):
    page = built["index.html"]
    assert "<p>You write rules in <code>CLAUDE.md</code>. Do they load?</p>" in page, f"the summary paragraph keeps its code span; got {page!r}"
    assert '<tr data-source="README.md:10"><td><code>toolname plan check &lt;plan.json&gt;</code></td><td>Checks a plan.</td><td><span class="status keep">works</span></td></tr>' in page, f"a works row is green and cites its line; got {page!r}"
    assert '<td><span class="status warn">not built (T43)</span></td>' in page, f"a not built row is a warn word; got {page!r}"
    assert "<p>Install the tool.</p>\n<pre tabindex=" in page, f"a block follows its label; got {page!r}"
    assert '<pre tabindex="0"><code>uv sync\ntoolname plan check plan.json</code></pre>' in page, f"a command block is copied unchanged; got {page!r}"
    assert "<p>The fake agent proves the plumbing. It measures nothing about a real agent.</p>" in page, f"the offline lead is the README sentence; got {page!r}"
    assert "<p>Runs use a <code>sandbox</code>. The process is not confined.</p>" in page, f"the isolation paragraph is the README text; got {page!r}"


def test_the_footer_links_the_repository_and_names_the_license(built):
    page = built["index.html"]
    assert '<a href="https://example.org/toolname">https://example.org/toolname</a>. License: MIT License.' in page, f"the footer shows the link and the license line from the sources; got {page!r}"


def test_a_command_block_escapes_markup(tmp_path):
    write_tree(tmp_path, {**site_files(), "README.md": site_files()["README.md"].replace("toolname run plan.json --runs 3", "toolname run <plan.json> && echo done")})
    page = render.render_site(tmp_path, extract.site_data(tmp_path))["index.html"]
    assert "<code>toolname run &lt;plan.json&gt; &amp;&amp; echo done</code>" in page, f"markup in a command is escaped; got {page!r}"


def test_before_and_after_and_install_come_from_the_data(built):
    page = built["index.html"]
    assert '<span class="status bad">Rule removed</span> 6 of 20 runs used a banned command.' in page, f"the before arm shows its hits from the live data; got {page!r}"
    assert '<span class="status keep">Rule loaded</span> 0 of 20 runs used a banned command.' in page, f"the after arm shows its hits from the live data; got {page!r}"
    assert '<h2 id="install">Install</h2>\n<p>Needs python.</p>\n<p>Install from source.</p>\n<pre tabindex="0"><code>uv sync' in page, f"the install section shows the README block; got {page!r}"
