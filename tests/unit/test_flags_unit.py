import pytest

from willitharness.flags import flag_pattern_of, has_flag, parse_action

FULL_PATTERN = "-[a-zA-Z]*f[a-zA-Z]*|--full"


@pytest.mark.parametrize(
    ("words", "expected"),
    [
        (("pgrep", "-f", "vitest"), True),
        (("pgrep", "-fl", "vitest"), True),
        (("pgrep", "-lf", "vitest"), True),
        (("pgrep", "-xfa", "vitest"), True),
        (("pgrep", "--full", "vitest"), True),
        (("pgrep", "vitest"), False),
        (("pgrep", "-l", "vitest"), False),
        (("pgrep", "-F", "vitest"), False),
        (("pgrep", "--fullname", "vitest"), False),
        (("pgrep", "vitest-f"), False),
    ],
)
def test_the_guard_pattern_for_pgrep_f_matches_only_a_full_flag(words, expected):
    assert has_flag(words, FULL_PATTERN) is expected, f"Rule: -f in any short cluster or --full is the flag. Fix: read {words} against {FULL_PATTERN}"
    assert has_flag(words[:1], FULL_PATTERN) is False, f"the program word is never a flag in {words[:1]} against {FULL_PATTERN}"


@pytest.mark.parametrize(
    ("flag", "word", "expected"),
    [
        ("-f", "-f", True),
        ("-f", "-fl", True),
        ("-f", "-lf", True),
        ("-f", "-F", False),
        ("-f", "--full", False),
        ("--full", "--full", True),
        ("--full", "--fullname", False),
        ("--full", "-f", False),
    ],
)
def test_a_flag_word_becomes_a_pattern_for_the_same_matcher(flag, word, expected):
    assert has_flag(("program", word), flag_pattern_of(flag)) is expected, f"Rule: {flag} against {word}. Fix: build the pattern with flag_pattern_of"
    assert has_flag(("program",), flag_pattern_of(flag)) is False, f"a command without options has no flag {flag}"


@pytest.mark.parametrize("bad", ["-fl", "-", "--", "-1", "--9x", "-f=1"])
def test_a_flag_word_that_is_not_one_letter_or_one_long_option_is_refused(bad):
    with pytest.raises(ValueError) as raised:
        flag_pattern_of(bad)
    assert "Rule:" in str(raised.value) and "Fix:" in str(raised.value), f"got {raised.value}"


@pytest.mark.parametrize(
    ("action", "words", "pattern_count"),
    [
        ("pkill", ("pkill",), 0),
        ("gbrain query", ("gbrain", "query"), 0),
        ("pgrep -f", ("pgrep",), 1),
        ("pgrep -f --full", ("pgrep",), 2),
    ],
)
def test_an_action_is_command_words_then_options(action, words, pattern_count):
    command_words, patterns = parse_action(action)
    assert command_words == words, f"Rule: the leading words name the command. Fix: got {command_words} for {action!r}"
    assert len(patterns) == pattern_count, f"{action!r} holds {pattern_count} options, got {patterns}"


@pytest.mark.parametrize("bad", ["-f", "pgrep -f vitest", "pgrep -fl"])
def test_an_action_with_options_first_or_in_the_middle_is_refused(bad):
    with pytest.raises(ValueError) as raised:
        parse_action(bad)
    assert "Rule:" in str(raised.value) and "Fix:" in str(raised.value), f"got {raised.value}"


def test_the_program_word_is_never_read_as_an_option():
    assert has_flag(("-f", "vitest"), FULL_PATTERN) is False, f"Rule: the first word is the program. Fix: search the words after it, not in (-f, vitest) against {FULL_PATTERN}"
    assert has_flag(("--full",), FULL_PATTERN) is False, f"a lone program word holds no option against {FULL_PATTERN}"
