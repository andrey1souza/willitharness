import pytest
import repo_checks
from files import write_tree

HEADING = "## Limits of isolation"
SENTENCES = (
    "Effect runs use Claude's own sandbox and have no network. Guard runs use macOS `sandbox-exec` and their network is open. The Linux sandbox path is untested.\n"
    "Run only plans you have read. Isolation is not a security boundary against a hostile plan.\n"
    "The `claude` process itself is not confined.\n"
)
NETWORK_SENTENCE = "Effect runs use Claude's own sandbox and have no network. "
GOOD = f"# t\n\nIntro.\n\n{HEADING}\n{SENTENCES}\n## Honest limits\n- x\n"


def test_the_good_paragraph_has_no_errors():
    errors = repo_checks.isolation_limit_errors(GOOD)
    assert errors == [], f"the full paragraph must pass, got {errors}"
    assert repo_checks.isolation_limit_errors(f"{HEADING}\n{SENTENCES}") == [], "a paragraph at the end of the file passes"


def test_the_check_reads_the_readme_of_the_root(tmp_path):
    write_tree(tmp_path, {"README.md": GOOD})
    assert repo_checks.readme_isolation_errors(tmp_path) == [], "a good README passes"
    write_tree(tmp_path, {"README.md": "# t\n"})
    errors = repo_checks.readme_isolation_errors(tmp_path)
    assert errors == ["the README has 0 '## Limits of isolation' headings, not one. Rule: the limits have one home. Fix: restore the heading once."], f"got {errors}"


@pytest.mark.parametrize(
    "removed, phrase",
    [
        (NETWORK_SENTENCE, "effect runs use claude's own sandbox and have no network"),
        ("Guard runs use macOS `sandbox-exec` and their network is open. ", "guard runs use macos sandbox-exec and their network is open"),
        ("The Linux sandbox path is untested.", "the linux sandbox path is untested"),
        ("Run only plans you have read. ", "run only plans you have read"),
        ("Isolation is not a security boundary against a hostile plan.", "not a security boundary against a hostile plan"),
        ("The `claude` process itself is not confined.", "the claude process itself is not confined"),
    ],
)
def test_each_missing_sentence_is_reported_by_name(removed, phrase):
    errors = repo_checks.isolation_limit_errors(GOOD.replace(removed, ""))
    assert errors == [f"the isolation limits lack the phrase {phrase!r}. Rule: the README states each limit. Fix: restore the sentence."], f"got {errors}"
    assert removed in GOOD, f"the fixture holds {removed!r}"


def test_a_phrase_outside_the_section_does_not_count():
    moved = f"# t\n\nEffect runs use Claude's own sandbox and have no network.\n\n{HEADING}\n{SENTENCES.replace(NETWORK_SENTENCE, '')}\n## Honest limits\n"
    errors = repo_checks.isolation_limit_errors(moved)
    assert len(errors) == 1 and repr("effect runs use claude's own sandbox and have no network") in errors[0], f"got {errors}"
    assert "have no network." in moved, "the phrase sits above the heading"


def test_a_wrapped_sentence_still_counts():
    wrapped = GOOD.replace("have no network.", "have no\nnetwork.")
    assert repo_checks.isolation_limit_errors(wrapped) == [], "a line break inside a sentence is not a missing phrase"
    assert "network." in wrapped, "the fixture wraps the sentence"


def test_a_missing_or_repeated_heading_is_reported():
    assert repo_checks.isolation_limit_errors(GOOD.replace(HEADING, "## Limits")) == [
        "the README has 0 '## Limits of isolation' headings, not one. Rule: the limits have one home. Fix: restore the heading once."
    ], "a renamed heading is reported"
    twice = repo_checks.isolation_limit_errors(GOOD + f"{HEADING}\n")
    assert len(twice) == 1 and "has 2 '## Limits of isolation' headings" in twice[0], f"got {twice}"


def test_a_paragraph_over_six_lines_is_reported():
    long_paragraph = GOOD.replace("The `claude` process itself is not confined.\n", "The `claude` process itself is not confined.\nOne.\nTwo.\nThree.\nFour.\n")
    errors = repo_checks.isolation_limit_errors(long_paragraph)
    assert errors == ["the isolation limits run 7 lines, over 6. Rule: keep the paragraph short. Fix: cut it."], f"got {errors}"
    assert repo_checks.isolation_limit_errors(GOOD.replace("The `claude` process itself is not confined.\n", "The `claude` process itself is not confined.\nOne.\nTwo.\nThree.\n")) == [], "exactly six lines pass"


def test_the_check_is_registered():
    assert "readme-isolation-limits" in repo_checks.CHECKS, f"the check is registered, got {sorted(repo_checks.CHECKS)}"
    assert repo_checks.CHECKS["readme-isolation-limits"] is repo_checks.readme_isolation_errors, "it runs the README check"
