import brand_gates
import pytest
from files import write_tree
from site_tree import site_files

GOOD = (
    '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">'
    "<title>Tool</title>"
    '<meta name="description" content="Short text."><meta property="og:title" content="Tool">'
    '<meta property="og:description" content="Short text."><meta name="twitter:card" content="summary">'
    "</head><body><h1>Tool</h1><p>One short sentence. Another short one.</p></body></html>"
)
LONG_SENTENCE = " ".join(["word"] * 25) + "."
SITE_FOLDERS = ("site", "scripts/site", "build/site")


def with_body(text):
    return GOOD.replace("<p>One short sentence. Another short one.</p>", text)


def test_a_good_page_passes_every_page_check():
    assert brand_gates.hype_problems("a.html", GOOD) == [], "no hype in the good page"
    assert brand_gates.meta_problems("a.html", GOOD) == [], "the good page declares its meta tags"
    assert brand_gates.hold_back_problems("a.html", GOOD, {}) == [], "no held-back phrase in the good page"
    assert brand_gates.style_problems({"a.html": GOOD}) == [], "the good page has short sentences"


@pytest.mark.parametrize("phrase", ["revolutionary", "Cutting-Edge", "blazing fast", "10x"])
def test_a_hype_word_is_reported_in_any_case(phrase):
    problems = brand_gates.hype_problems("a.html", with_body(f"<p>A {phrase} tool.</p>"))
    assert len(problems) == 1 and phrase.lower() in problems[0], f"{phrase} must be reported once, got {problems}"
    assert problems[0].startswith("a.html uses the hype word"), f"got {problems[0]}"


def test_a_word_that_only_contains_hype_is_not_reported():
    assert brand_gates.hype_problems("a.html", with_body("<p>The seamlessly-named file.</p>")) == [], "a hyphenated compound is not the bare phrase"
    assert brand_gates.hype_problems("a.html", with_body("<p>Unseamless is a word.</p>")) == [], "a longer word is not the phrase"


@pytest.mark.parametrize("phrase", ["proven", "reproduced", "released", "nobody", "works on Linux"])
def test_a_held_back_phrase_is_reported_unless_the_data_marks_it_true(phrase):
    page = with_body(f"<p>It is {phrase.upper()} here.</p>")
    unmarked = brand_gates.hold_back_problems("a.html", page, {})
    assert len(unmarked) == 1 and phrase in unmarked[0], f"{phrase} must be reported without proof, got {unmarked}"
    assert brand_gates.hold_back_problems("a.html", page, {phrase: False}) == unmarked, "a false claim is reported too"
    assert brand_gates.hold_back_problems("a.html", page, {phrase: True}) == [], "a true claim may appear"


def test_a_held_back_phrase_in_the_head_is_not_visible_text():
    page = GOOD.replace("Short text.", "Nobody", 1)
    assert brand_gates.hold_back_problems("a.html", page, {}) == [], "only visible text counts"
    assert brand_gates.hold_back_problems("a.html", with_body("<p>Unproven things.</p>"), {}) == [], "a longer word is not the phrase"


def test_claims_must_be_booleans():
    with pytest.raises(AssertionError, match="true or false") as raised:
        brand_gates.hold_back_problems("a.html", GOOD, {"proven": "yes"})
    assert "'yes'" in str(raised.value), f"the failure must show the value, got {raised.value}"
    assert raised.type is AssertionError, f"expected an assertion failure, got {raised.type}"


@pytest.mark.parametrize(
    ("dropped", "fragment"),
    [
        ('<meta name="description" content="Short text.">', 'name="description"'),
        ('<meta name="viewport" content="width=device-width">', 'name="viewport"'),
        ('<meta property="og:title" content="Tool">', 'property="og:title"'),
        ('<meta property="og:description" content="Short text.">', 'property="og:description"'),
        ('<meta name="twitter:card" content="summary">', 'name="twitter:card"'),
        ('<meta charset="utf-8">', "<meta charset>"),
        ('lang="en"', "lang attribute"),
    ],
)
def test_each_missing_meta_tag_is_reported(dropped, fragment):
    problems = brand_gates.meta_problems("a.html", GOOD.replace(dropped, ""))
    assert len(problems) == 1 and fragment in problems[0], f"dropping {dropped} must give one problem about {fragment}, got {problems}"
    assert problems[0].startswith("a.html "), f"got {problems[0]}"


def test_an_empty_meta_content_is_reported():
    problems = brand_gates.meta_problems("a.html", GOOD.replace('<meta name="description" content="Short text.">', '<meta name="description" content=" ">'))
    assert len(problems) == 1 and 'name="description"' in problems[0], f"an empty content counts as missing, got {problems}"
    assert brand_gates.meta_problems("a.html", GOOD) == [], "the good page still passes"


def test_titles_and_descriptions_have_a_length_limit():
    long_title = brand_gates.meta_problems("a.html", GOOD.replace("<title>Tool</title>", f"<title>{'t' * 61}</title>"))
    assert len(long_title) == 1 and "title" in long_title[0], f"a 61 character title is too long, got {long_title}"
    long_description = brand_gates.meta_problems("a.html", GOOD.replace('content="Short text."><meta property="og:title"', f'content="{"d" * 161}"><meta property="og:title"'))
    assert len(long_description) == 1 and "161 characters" in long_description[0], f"a 161 character description is too long, got {long_description}"
    assert brand_gates.meta_problems("a.html", GOOD.replace("<title>Tool</title>", f"<title>{'t' * 60}</title>")) == [], "sixty characters fit"


def test_the_budgets_apply_per_file_and_in_total():
    per_file = brand_gates.budget_problems({"a.html": 65537, "b.css": 10})
    assert len(per_file) == 1 and per_file[0].startswith("a.html weighs"), f"one file is over budget, got {per_file}"
    total = brand_gates.budget_problems({f"p{index}.html": 65536 for index in range(3)})
    assert len(total) == 1 and total[0].startswith("the site weighs 196608"), f"three full pages exceed the total, got {total}"
    assert brand_gates.budget_problems({"a.html": 65536}) == [], "a page of 64 KiB passes"
    assert brand_gates.budget_problems({"a.html": 65536, "b.html": 65536}) == [], "two pages of 64 KiB are within 128 KiB"


def test_sentences_over_twenty_words_must_stay_under_a_fifth():
    one_in_five = "<p>" + " ".join(["Short one."] * 4 + [LONG_SENTENCE]) + "</p>"
    assert brand_gates.style_problems({"a.html": with_body(one_in_five)}) == [], "five of six sentences short is above the share"
    two_in_five = "<p>" + " ".join(["Short one."] * 3 + [LONG_SENTENCE] * 2) + "</p>"
    problems = brand_gates.style_problems({"a.html": with_body(two_in_five)})
    assert len(problems) == 1 and "66 percent" in problems[0], f"two long sentences in five break the share, got {problems}"
    assert "word word word" in problems[0], f"the problem must quote a long sentence, got {problems[0]}"


def test_twenty_words_is_not_long():
    twenty = " ".join(["word"] * 20) + "."
    page = with_body(f"<p>{twenty}</p><p>{twenty}</p>")
    assert brand_gates.style_problems({"a.html": page}) == [], "a sentence of exactly twenty words is allowed"
    assert brand_gates.style_problems({"a.html": with_body(f"<p>{LONG_SENTENCE}</p>")})[0].startswith("a.html has 50 percent"), "a single long sentence fails"


def test_a_hand_typed_number_in_a_template_is_reported():
    problems = brand_gates.typed_number_problems("t.html", '<h2 id="x1">We have 49 rules</h2>\n<p>$count2 items and $${cost}</p>\n')
    assert problems == ["t.html:1 types the number 49 by hand. Rule: every number comes from a data file. Fix: use a placeholder."], f"got {problems}"
    assert brand_gates.typed_number_problems("t.html", '<h1 class="a2">$title</h1>\n') == [], "digits in tags and placeholders are not typed numbers"


def test_a_rendered_number_must_come_from_the_data():
    page = with_body("<p>There are 49 items and 7 more.</p>")
    problems = brand_gates.rendered_number_problems("a.html", page, '{"count": 49}')
    assert problems == ["a.html shows the number 7, which no data file holds. Rule: digits come only from data. Fix: derive it from a data file."], f"got {problems}"
    assert brand_gates.rendered_number_problems("a.html", page, '{"a": 49, "b": "7"}') == [], "numbers in any data value are allowed"


def test_comments_are_found_in_python_css_and_html():
    sources = {"a.py": "x = 1  # why\n", "b.css": "a { } /* why */", "c.html": "<!-- why --><p>x</p>", "d.py": "x = '# not a comment'\n", "e.css": "a { }"}
    problems = brand_gates.comment_problems(sources)
    assert [problem.split(" ")[0] for problem in problems] == ["a.py:1", "b.css", "c.html"], f"only real comments are reported, got {problems}"
    assert all("Rule: names carry intent" in problem for problem in problems), f"each problem states the rule, got {problems}"


def test_a_markdown_file_in_a_site_folder_is_reported(tmp_path):
    write_tree(tmp_path, {**site_files(), "site/notes.md": "x", "build/site/deep/more.md": "x", "docs/ok.md": "x"})
    problems = brand_gates.stray_markdown_problems(tmp_path, SITE_FOLDERS)
    assert [problem.split(" ")[0] for problem in problems] == ["site/notes.md", "build/site/deep/more.md"], f"got {problems}"
    assert brand_gates.stray_markdown_problems(tmp_path, ("docs/none",)) == [], "a missing folder is skipped"
