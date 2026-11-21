import json

import pytest

from git_repo import TEST_EMAIL, commit_files, init_repo, run_git
from guards import pr_text, private_names

LOG = (
    "7 passed in 1.00s\n== analysis\nmutants killed: 3/3\n== arms\nmutants killed: 2/2\n"
    "trace-check: all 49 IDs covered; pending: DI-1 (lean)\nrepo-checks: 22 checks passed\n"
    "1291 passed in 12.34s\n"
)
FACTS = {"tests": 1291, "mutants_killed": 5, "mutants_total": 5, "trace_ids": 49, "repo_checks": 22}
ATTRIBUTION = "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
PRIVATE_TERM = "zzprivateterm"
FIRST = {"sha": "a" * 40, "subject": "feat: add the writer", "body_lines": ["Explains the writer.", ATTRIBUTION]}
SECOND = {"sha": "b" * 40, "subject": "fix: handle 3 empty logs", "body_lines": []}
LONG_SENTENCE = "This sentence keeps going and going with so many words that no reader can hold it in mind while the next clause starts."


def test_one_commit_gives_its_subject_as_the_title():
    title = pr_text.title_line([FIRST])
    assert title == "feat: add the writer", f"a single commit gives its own subject, got {title!r}"
    assert "commits" not in title, f"a single commit has no summary suffix, got {title!r}"


def test_several_commits_give_the_newest_subject_and_the_count():
    title = pr_text.title_line([SECOND, FIRST])
    assert title == "fix: handle 3 empty logs (+1 commits)", f"got {title!r}"
    assert pr_text.title_line([SECOND, FIRST, FIRST]).endswith("(+2 commits)"), "the count is commits minus the newest"


def test_attribution_lines_are_copied_once_and_never_invented():
    assert pr_text.attribution_lines([FIRST, FIRST]) == [ATTRIBUTION], "a repeated trailer is copied once"
    assert pr_text.attribution_lines([SECOND]) == [], "no trailer in the commits means none in the result"


def test_the_body_lists_every_subject_the_sha_and_the_checks():
    body = pr_text.build_body([SECOND, FIRST], FACTS)
    for expected in ("- feat: add the writer", "- fix: handle 3 empty logs", "Commit: " + "b" * pr_text.SHA_LENGTH, "- Tests: 1291 passed", "- Mutants: 5 of 5 killed", "- Contract IDs covered: 49", "- Repository checks passed: 22"):
        assert expected in body, f"the body lacks {expected!r}: {body!r}"


def test_the_body_ends_with_the_attribution_only_when_the_commits_carry_it():
    with_trailer = pr_text.build_body([FIRST], FACTS)
    without = pr_text.build_body([SECOND], FACTS)
    assert with_trailer.endswith(ATTRIBUTION + "\n"), f"the trailer closes the body, got {with_trailer!r}"
    assert "Co-Authored-By" not in without and "Generated with" not in without, f"nothing is invented, got {without!r}"


def test_facts_come_from_the_log():
    assert pr_text.facts_from_log(LOG) == FACTS, "the facts quote the gate lines of the log"
    assert set(pr_text.facts_from_log(LOG)) == set(pr_text.FACT_KEYS), "the keys follow FACT_KEYS"


def test_a_log_with_a_survivor_gives_no_facts():
    with pytest.raises(AssertionError, match="failed gates") as survivor:
        pr_text.facts_from_log(LOG.replace("mutants killed: 2/2", "mutants killed: 1/2"))
    assert "Mutants" in str(survivor.value), f"the failed gate is named, got {survivor.value}"
    with pytest.raises(AssertionError, match="failed gates") as failure:
        pr_text.facts_from_log(LOG.replace("1291 passed in", "1 failed, 1290 passed in"))
    assert "Tests" in str(failure.value), f"the failed gate is named, got {failure.value}"


def test_facts_missing_a_key_give_no_check_lines():
    with pytest.raises(AssertionError, match="trace_ids"):
        pr_text.check_lines({key: 1 for key in pr_text.FACT_KEYS if key != "trace_ids"})
    assert len(pr_text.check_lines(FACTS)) == 4, "four checks are listed"


def test_a_generated_body_passes_every_check():
    body = pr_text.build_body([SECOND, FIRST], FACTS)
    problems = pr_text.body_problems(body, FACTS, [SECOND, FIRST], [PRIVATE_TERM])
    assert problems == [], f"a body built from data must pass, got {problems}"


def test_a_hand_typed_number_fails():
    body = pr_text.build_body([SECOND, FIRST], FACTS) + "\nThe change touches 777 files.\n"
    problems = pr_text.number_problems(body, FACTS, [SECOND, FIRST])
    assert len(problems) == 1 and "777" in problems[0], f"the typed number must be named, got {problems}"
    assert "Fix:" in problems[0], f"the message needs a fix, got {problems[0]!r}"


def test_a_number_from_a_commit_subject_passes():
    problems = pr_text.number_problems("The writer handles 3 empty logs.\n", FACTS, [SECOND])
    assert problems == [], f"a number from the commit data is allowed, got {problems}"


def test_a_number_that_is_only_part_of_the_sha_is_not_read_as_a_number():
    digits_only = {"sha": "123456789012" + "a" * 28, "subject": "feat: x", "body_lines": []}
    problems = pr_text.number_problems(f"Commit: {digits_only['sha'][:pr_text.SHA_LENGTH]}\n", FACTS, [digits_only])
    assert problems == [], f"the sha is data, not a typed number, got {problems}"


def test_a_private_term_fails_and_the_message_does_not_repeat_it():
    problems = pr_text.private_problems(f"Line one.\nMentions {PRIVATE_TERM.upper()} here.\n", [PRIVATE_TERM])
    assert len(problems) == 1 and "line 2" in problems[0], f"line 2 carries the term, got {problems}"
    assert PRIVATE_TERM not in problems[0].lower(), f"the message must not leak the term, got {problems[0]!r}"
    assert pr_text.private_problems("Clean text.\n", [PRIVATE_TERM]) == [], "clean text passes"


@pytest.mark.parametrize("phrase", pr_text.BLOCKED_PHRASES)
def test_each_hold_back_phrase_fails(phrase):
    problems = pr_text.phrase_problems(f"The result is {phrase} today.")
    assert len(problems) == 1 and phrase in problems[0], f"{phrase!r} must be named, got {problems}"
    assert pr_text.phrase_problems("The result is plain.") == [], "plain text passes"


def test_the_list_holds_the_site_phrases_and_the_two_added_ones():
    assert {"proven", "reproduced", "released", "nobody", "works on Linux", "guaranteed", "fully tested"} <= set(pr_text.BLOCKED_PHRASES), f"got {pr_text.BLOCKED_PHRASES}"
    assert "Proven" in pr_text.phrase_problems("Proven result.")[0] or "proven" in pr_text.phrase_problems("Proven result.")[0], "the match ignores case"


def test_long_sentences_over_the_share_fail():
    body = "\n".join([LONG_SENTENCE, LONG_SENTENCE, "Short one."])
    problems = pr_text.sentence_problems(body, [])
    assert len(problems) == 1 and "33 percent" in problems[0], f"got {problems}"
    assert "Fix:" in problems[0], f"the message needs a fix, got {problems[0]!r}"


def test_four_short_sentences_and_one_long_pass_at_the_threshold():
    body = "\n".join(["One.", "Two.", "Three.", "Four.", LONG_SENTENCE])
    assert pr_text.sentence_problems(body, []) == [], f"80 percent short is enough, got {body!r}"
    assert pr_text.sentence_problems(body + "\n" + LONG_SENTENCE, []) != [], f"66 percent short is not enough, got {body!r}"


def test_the_attribution_line_is_not_counted_as_a_sentence():
    long_attribution = "Co-Authored-By: " + " ".join(["word"] * 30)
    problems = pr_text.sentence_problems("One.\n" + long_attribution, [long_attribution])
    assert problems == [], f"trailers are data, got {problems} for {long_attribution!r}"
    assert pr_text.sentence_problems("One.\n" + long_attribution, []) != [], f"the same line counts when it is not a trailer: {long_attribution!r}"


def test_an_empty_body_is_refused():
    with pytest.raises(AssertionError, match="empty") as empty:
        pr_text.body_problems("  \n", FACTS, [FIRST], [PRIVATE_TERM])
    assert "Fix:" in str(empty.value), f"the refusal says how to fix, got {empty.value}"
    with pytest.raises(AssertionError, match="no commits") as failure:
        pr_text.body_problems("Text.\n", FACTS, [], [PRIVATE_TERM])
    assert "Fix:" in str(failure.value), f"the refusal says how to fix, got {failure.value}"


@pytest.fixture
def repo(tmp_path):
    prepared = init_repo(tmp_path, TEST_EMAIL)
    commit_files(prepared, "chore: start", ["README.md"])
    run_git(prepared, ["update-ref", "refs/remotes/origin/main", "HEAD"])
    run_git(prepared, ["switch", "-c", "feat/change"])
    commit_files(prepared, "feat: change", ["change.txt"])
    return prepared


@pytest.fixture
def environment(tmp_path):
    denylist = tmp_path / "denylist"
    denylist.write_text(PRIVATE_TERM + "\n")
    return {private_names.DENYLIST_VARIABLE: str(denylist)}


@pytest.fixture
def facts_file(tmp_path):
    target = tmp_path / "facts.json"
    target.write_text(json.dumps(FACTS))
    return target


def test_main_writes_the_facts_file_from_a_log(tmp_path):
    log_file = tmp_path / "check.log"
    log_file.write_text(LOG)
    target = tmp_path / "out.json"
    code = pr_text.main(["--log", str(log_file), "--write-facts", str(target)], str(tmp_path), {})
    assert code == pr_text.EXIT_CLEAN, f"expected exit 0, got {code}"
    assert json.loads(target.read_text()) == FACTS, f"the file holds the facts, got {target.read_text()!r}"


def test_main_refuses_a_log_with_no_gate_lines(tmp_path, capsys):
    log_file = tmp_path / "check.log"
    log_file.write_text("nothing useful\n")
    target = tmp_path / "out.json"
    code = pr_text.main(["--log", str(log_file), "--write-facts", str(target)], str(tmp_path), {})
    assert code == pr_text.EXIT_FAILED, f"expected exit 1, got {code}"
    assert not target.exists(), "no facts file is written from a bad log"
    assert "pr_text:" in capsys.readouterr().err, f"the refusal is printed, code {code}"


def test_main_writes_the_body_for_the_branch_commits(repo, facts_file, tmp_path):
    target = tmp_path / "body.md"
    code = pr_text.main(["--base", "origin/main", "--facts", str(facts_file), "--out", str(target)], str(repo), {})
    body = target.read_text()
    assert code == pr_text.EXIT_CLEAN, f"expected exit 0, got {code}"
    assert body.startswith("feat: change\n") and "- feat: change" in body and "chore: start" not in body, f"only the branch commit belongs, got {body!r}"


def test_main_prints_the_body_when_no_out_is_given(repo, facts_file, capsys):
    code = pr_text.main(["--base", "origin/main", "--facts", str(facts_file)], str(repo), {})
    assert code == pr_text.EXIT_CLEAN, f"expected exit 0, got {code}"
    assert capsys.readouterr().out.startswith("feat: change\n"), "the body goes to stdout"


def test_main_checks_a_good_body_and_a_typed_number(repo, facts_file, environment, tmp_path, capsys):
    body_file = tmp_path / "body.md"
    pr_text.main(["--base", "origin/main", "--facts", str(facts_file), "--out", str(body_file)], str(repo), {})
    arguments = ["--base", "origin/main", "--facts", str(facts_file), "--check", str(body_file)]
    assert pr_text.main(arguments, str(repo), environment) == pr_text.EXIT_CLEAN, "a generated body passes"
    body_file.write_text(body_file.read_text() + "\nIt fixes 999 bugs.\n")
    assert pr_text.main(arguments, str(repo), environment) == pr_text.EXIT_FAILED, "a typed number fails"
    reported = capsys.readouterr().err
    assert "999" in reported, f"the number is named, got {reported!r}"


def test_main_blocks_the_check_when_the_denylist_is_missing(repo, facts_file, tmp_path):
    body_file = tmp_path / "body.md"
    body_file.write_text("Text.\n")
    missing = {private_names.DENYLIST_VARIABLE: str(tmp_path / "absent")}
    code = pr_text.main(["--facts", str(facts_file), "--check", str(body_file)], str(repo), missing)
    assert code == pr_text.EXIT_BLOCKED, f"a missing denylist must block, got {code}"


def test_a_file_outside_the_repository_is_refused(repo, tmp_path_factory, capsys):
    outside = tmp_path_factory.mktemp("elsewhere") / "check.log"
    outside.write_text(LOG)
    code = pr_text.main(["--log", str(outside), "--write-facts", "facts.json"], str(repo), {})
    message = capsys.readouterr().err
    assert code == pr_text.EXIT_FAILED, f"expected exit 1, got {code}"
    assert "outside" in message and "Fix:" in message, f"unexpected message {message!r}"


def test_the_tests_pattern_takes_the_last_passed_count_and_ignores_other_words():
    assert pr_text.last_count(pr_text.TESTS_LINE, "7 passed in 1s\n1291 passed in 2s\n") == 1291, "the last count wins"
    with pytest.raises(AssertionError, match="no line matching") as missing:
        pr_text.last_count(pr_text.TESTS_LINE, "nothing here\n")
    assert "Fix:" in str(missing.value), f"the refusal says how to fix, got {missing.value}"


def test_the_failed_pattern_matches_only_failed_counts():
    assert pr_text.TESTS_FAILED.search("2 failed, 3 passed in 1s"), "a failed count is found"
    assert not pr_text.TESTS_FAILED.search("3 passed in 1s"), "a clean line has no failed count"


def test_mutant_lines_are_summed_over_the_whole_log():
    facts = pr_text.facts_from_log(LOG.replace("repo-checks", "mutants killed: 4/4\nrepo-checks"))
    assert (facts["mutants_killed"], facts["mutants_total"]) == (9, 9), f"3+2+4 of 3+2+4 expected, got {facts}"
    assert facts["tests"] == 1291, f"the other facts stay, got {facts}"


def test_a_mutant_line_with_extra_text_is_not_counted():
    facts = pr_text.facts_from_log(LOG + "note: mutants killed: 9/9 extra\n")
    assert (facts["mutants_killed"], facts["mutants_total"]) == (5, 5), f"only whole lines count, got {facts}"
    assert pr_text.MUTANTS_LINE.search("mutants killed: 9/9 extra") is None, "the anchors reject trailing text"


def test_the_trace_pattern_gives_the_covered_count():
    assert pr_text.last_count(pr_text.TRACE_LINE, "trace-check: all 49 IDs covered; pending: DI-1\n") == 49, "the count comes from the trace line"
    assert pr_text.facts_from_log(LOG)["trace_ids"] == 49, "the facts carry it"


def test_the_repo_pattern_gives_the_checks_passed_and_ignores_extra_text():
    assert pr_text.last_count(pr_text.REPO_LINE, "repo-checks: 22 checks passed\nrepo-checks: 99 checks passed (stale)\n") == 22, "a line with trailing text is ignored"
    assert pr_text.facts_from_log(LOG)["repo_checks"] == 22, "the facts carry it"


def test_an_empty_log_gives_no_facts():
    with pytest.raises(AssertionError, match="empty") as empty:
        pr_text.facts_from_log("  \n")
    assert "Fix:" in str(empty.value), f"the refusal says how to fix, got {empty.value}"
