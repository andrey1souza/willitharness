import json

from guard_site import MESSAGES_FILE, bash, corpus, guard_rules, messages

from willitharness import guard
from willitharness.guard import GuardRule, check_messages, decide_command, offered_prefix
from willitharness.vocabulary import Coverage

OLD_MESSAGE = "Blocked by guard (pkill): never use pkill or pgrep -f; record each PID you start and kill only those PIDs"
BAD_CLASS, GOOD_CLASS, GAP_CLASS = "bad", "good", "gap"


def corpus_entries(kind):
    found = [entry for entry in corpus() if entry["class"] == kind]
    assert found, f"the corpus has no {kind} commands. Fix: add them."
    return found


def corpus_failures(rules):
    failures = []
    for entry in corpus():
        decision = decide_command(entry["command"], rules)
        wanted_block = entry["class"] == BAD_CLASS
        if decision.blocked != wanted_block:
            failures.append(entry["command"])
    return failures


def rules_without(name):
    kept = [rule for rule in guard_rules() if rule.name != name]
    assert len(kept) == len(guard_rules()) - 1, f"{name!r} is not one rule of {[rule.name for rule in guard_rules()]}"
    return tuple(kept)


def test_every_bad_command_is_blocked_with_the_message_of_its_rule():
    rules = {rule.name: rule for rule in guard_rules()}
    for entry in corpus_entries(BAD_CLASS):
        decision = decide_command(entry["command"], tuple(rules.values()))
        assert decision.blocked, f"bad command {entry['command']!r} was allowed"
        assert decision.message == rules[entry["rule"]].message, f"{entry['command']!r} got {decision.message!r}"


def test_every_good_command_is_allowed():
    for entry in corpus_entries(GOOD_CLASS):
        decision = decide_command(entry["command"], guard_rules())
        assert not decision.blocked, f"good command {entry['command']!r} was blocked: {decision.message}"
        assert decision.message == "", f"an allowed command carries a message: {decision.message!r}"


def test_the_documented_known_gaps_stay_allowed():
    for entry in corpus_entries(GAP_CLASS):
        assert not decide_command(entry["command"], guard_rules()).blocked, f"known gap {entry['command']!r} is now blocked. Fix: move it to bad."


def test_the_corpus_passes_on_the_real_rules():
    failures = corpus_failures(guard_rules())
    assert failures == [], f"corpus commands decided wrongly: {failures}"
    assert len(corpus()) == 25, f"corpus size is {len(corpus())}, expected 25"


def test_a_guard_that_allows_pkill_fails_the_corpus():
    failures = corpus_failures(rules_without("pkill"))
    assert "pkill -f vitest" in failures, f"the corpus did not reject a guard that allows pkill -f: {failures}"
    assert failures == ["pkill -f vitest", "pkill vitest", "pgrep -fl vitest", "pgrep --full vitest", "echo hi | pkill node"], f"unexpected failures {failures}"


def test_coverage_is_full_when_every_bad_command_is_blocked():
    calls = tuple(bash(entry["command"]) for entry in corpus_entries(BAD_CLASS))
    cp_coverage = guard.coverage_of(calls, ("cp",), guard_rules())
    pkill_coverage = guard.coverage_of(calls, ("pkill",), guard_rules())
    assert cp_coverage is Coverage.FULL, f"cp attempts in the corpus must be fully covered, got {cp_coverage} for {len(calls)} calls"
    assert pkill_coverage is Coverage.FULL, f"pkill attempts in the corpus must be fully covered, got {pkill_coverage} for {len(calls)} calls"


def test_coverage_is_partial_when_the_guard_lets_a_violating_command_pass():
    calls = (bash("pkill -f x"), bash("pkill y"))
    unguarded = guard.coverage_of(calls, ("pkill",), rules_without("pkill"))
    narrow = (GuardRule("narrow", "m `kill PID`", ("kill PID",), guard_rules()[1].blocked[1:]),)
    narrow_calls = (bash("pgrep -x a"), bash("pgrep -f a"))
    narrow_coverage = guard.coverage_of(narrow_calls, ("pgrep",), narrow)
    assert unguarded is Coverage.PARTIAL, f"a guard with no pkill rule blocks nothing, got {unguarded} for {calls}"
    assert narrow_coverage is Coverage.PARTIAL, f"a guard that blocks pgrep -f only is partial for {narrow_calls}, got {narrow_coverage}"


def test_coverage_is_none_seen_when_no_violating_command_ran():
    calls = (bash("ls"), bash("command cp -f a b"))
    quiet = guard.coverage_of(calls, ("cp",), guard_rules())
    empty = guard.coverage_of((), ("cp",), guard_rules())
    assert quiet is Coverage.NONE_SEEN, f"no bare cp ran in {calls}, got {quiet}"
    assert empty is Coverage.NONE_SEEN, f"no calls means none seen, got {empty}"


def test_the_fixed_messages_are_accepted_through_the_command(capsys):
    code = guard.main(["check-messages", str(MESSAGES_FILE)])
    captured = capsys.readouterr()
    assert code == 0, f"expected exit 0, got {code}; stderr {captured.err!r}"
    assert captured.out == "messages: 2 accepted, 0 rejected\n", f"unexpected output {captured.out!r}"


def test_the_old_spike_message_is_rejected_through_the_command(tmp_path, capsys):
    source = tmp_path / "messages.json"
    source.write_text(json.dumps([{"message": OLD_MESSAGE, "offered_alternatives": []}]))
    code = guard.main(["check-messages", str(source)])
    captured = capsys.readouterr()
    assert code == 1, f"expected exit 1, got {code}"
    assert captured.err == f"rejected: no runnable alternative: {OLD_MESSAGE}\nmessages: 0 accepted, 1 rejected\n", f"unexpected stderr {captured.err!r}"


def test_a_message_without_the_alternatives_key_is_rejected(tmp_path, capsys):
    source = tmp_path / "messages.json"
    source.write_text(json.dumps([{"message": OLD_MESSAGE}]))
    code = guard.main(["check-messages", str(source)])
    errors = capsys.readouterr().err
    assert code == 1, f"the old message with no alternatives must exit 1, got {code}"
    assert "rejected: no runnable alternative" in errors, f"the rejection wording is fixed, got {errors!r}"


def test_an_alternative_the_message_does_not_quote_is_rejected():
    entry = {"message": "use kill PID instead", "offered_alternatives": ["kill PID"]}
    accepted, rejections = check_messages([entry])
    assert (accepted, len(rejections)) == (0, 1), f"an unquoted alternative is not runnable: {rejections}"
    quoted = {"message": "use `kill PID` instead", "offered_alternatives": ["kill PID"]}
    assert check_messages([quoted]) == (1, []), "a quoted alternative is runnable"


def test_an_alternative_that_starts_with_a_placeholder_is_rejected():
    entry = {"message": "use `PATH` instead", "offered_alternatives": ["PATH"]}
    accepted, rejections = check_messages([entry])
    assert (accepted, len(rejections)) == (0, 1), f"a bare placeholder is not runnable: {rejections}"
    assert rejections[0].startswith("rejected: no runnable alternative"), f"unexpected wording {rejections[0]!r}"


def test_the_messages_of_the_rules_match_the_messages_file():
    from_file = {entry["message"]: tuple(entry["offered_alternatives"]) for entry in messages()}
    from_rules = {rule.message: rule.offered_alternatives for rule in guard_rules()}
    assert from_file == from_rules, f"rules.json and messages.json differ: {from_file} against {from_rules}"
    assert len(from_rules) == 2, f"expected two rules, got {len(from_rules)}"


def test_the_command_prints_usage_for_other_arguments(capsys):
    code = guard.main(["other"])
    errors = capsys.readouterr().err
    assert code == 2, f"an unknown command is a usage error, got {code}"
    assert "usage: guard check-messages" in errors, f"usage names the command, got {errors!r}"


def test_an_offered_alternative_is_matched_up_to_its_first_placeholder():
    assert offered_prefix("run SOURCE now") == ("run",), f"unexpected prefix {offered_prefix('run SOURCE now')}"
    assert offered_prefix("ps -axo pid,command | grep '[p]attern'") == ("ps", "-axo", "pid,command"), "only the first segment counts"
