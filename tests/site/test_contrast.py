import pytest

import contrast
from site_tree import STYLE

TOKENS = ":root { --bg: #FAF8F3; --text: #1B1B1B; --muted: #58584F; --link: #0B4F9C; --keep: #1B6B3A; --warn: #8A4B00; --bad: #A31F34; --yellow: #F8D000; --orange: #F0A818; --panel: #E8E8E8; }"
LEDGER_RATIOS = {"text": 16.23, "muted": 6.77, "link": 7.57, "keep": 6.16, "warn": 6.41, "bad": 7.06}
FILL_RATIOS = {"yellow": 12.1, "orange": 8.5, "panel": 14.0}


@pytest.mark.parametrize("token", sorted(LEDGER_RATIOS))
def test_ledger_tokens_measure_the_published_ratios_in_both_directions(token):
    tokens = contrast.tokens_of(TOKENS)
    assert contrast.ratio(tokens[token], tokens["bg"]) == LEDGER_RATIOS[token], f"{token} on bg must measure {LEDGER_RATIOS[token]}"
    assert contrast.ratio(tokens["bg"], tokens[token]) == LEDGER_RATIOS[token], f"bg on {token} must measure {LEDGER_RATIOS[token]}"


def test_the_shipped_stylesheet_passes():
    problems = contrast.contrast_problems(STYLE)
    assert problems == [], f"the shipped stylesheet must pass AA, got {problems}"
    assert contrast.tokens_of(STYLE)["bg"] == "#FAF8F3", "the shipped background is the Ledger paper colour"


def test_a_weak_colour_fails_in_both_directions():
    problems = contrast.contrast_problems(TOKENS.replace("#58584F", "#AAAAAA"))
    assert len(problems) == 2, f"muted fails in both directions, got {problems}"
    assert problems[0].startswith("--muted on --bg measures 2.19:1") and problems[1].startswith("--bg on --muted"), f"got {problems}"


def test_a_colour_just_under_the_minimum_fails():
    problems = contrast.contrast_problems(TOKENS.replace("#58584F", "#767676"))
    assert len(problems) == 2 and "measures 4.28:1, under 4.5:1" in problems[0], f"4.28 is under AA, got {problems}"
    assert contrast.contrast_problems(TOKENS.replace("#58584F", "#6B6B6B")) == [], "a colour above 4.5 passes"


def test_a_missing_token_is_reported():
    problems = contrast.contrast_problems(TOKENS.replace("--bad: #A31F34;", ""))
    assert problems == ["the stylesheet has no --bad token. Rule: every text colour is a token. Fix: declare it."], f"got {problems}"
    assert contrast.contrast_problems(TOKENS) == [], "the full token set passes"


def test_a_stylesheet_without_background_fails_loudly():
    with pytest.raises(AssertionError, match="no --bg token") as raised:
        contrast.contrast_problems(":root { --text: #1B1B1B; }")
    assert "'text'" in str(raised.value), f"the failure must list the tokens, got {raised.value}"
    assert raised.type is AssertionError, f"expected an assertion failure, got {raised.type}"


def test_a_stylesheet_without_tokens_fails_loudly():
    with pytest.raises(AssertionError, match="declares no colour tokens") as raised:
        contrast.tokens_of("body { color: red; }")
    assert "Fix" in str(raised.value), f"the failure must say how to fix it, got {raised.value}"
    assert raised.type is AssertionError, f"expected an assertion failure, got {raised.type}"


def test_a_bad_colour_literal_fails_loudly():
    with pytest.raises(AssertionError, match="#rrggbb") as raised:
        contrast.luminance("red")
    assert "'red'" in str(raised.value), f"the failure must show the value, got {raised.value}"
    assert contrast.luminance("#FFFFFF") == pytest.approx(1.0) and contrast.luminance("#000000") == pytest.approx(0.0), "white is 1 and black is 0"


@pytest.mark.parametrize("fill", sorted(FILL_RATIOS))
def test_dark_text_on_each_fill_is_measured_in_both_directions(fill):
    tokens = contrast.tokens_of(TOKENS)
    assert contrast.ratio(tokens["text"], tokens[fill]) >= contrast.TEXT_MINIMUM, f"text on {fill} must reach AA"
    assert contrast.ratio(tokens[fill], tokens["text"]) == contrast.ratio(tokens["text"], tokens[fill]), f"{fill} on text must measure the same"


def test_a_pale_fill_fails_and_a_missing_fill_is_reported():
    problems = contrast.contrast_problems(TOKENS.replace("#F8D000", "#2A2A2A"))
    assert len(problems) == 2 and problems[0].startswith("--text on --yellow measures"), f"dark on dark fails, got {problems}"
    missing = contrast.contrast_problems(TOKENS.replace("--orange: #F0A818;", ""))
    assert missing == ["the stylesheet has no --orange token. Rule: every text colour is a token. Fix: declare it."], f"got {missing}"
