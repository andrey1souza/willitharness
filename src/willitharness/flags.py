import re

OPTION_PREFIX = "-"
SHORT_FLAG = re.compile(r"-([a-zA-Z])")
LONG_FLAG = re.compile(r"--[a-zA-Z][a-zA-Z0-9-]*")
SHORT_CLUSTER_PATTERN = "-[a-zA-Z]*{letter}[a-zA-Z]*"


def has_flag(words: tuple[str, ...], flag_pattern: str) -> bool:
    assert flag_pattern, "has_flag needs a pattern. Fix: pass a regular expression for the option."
    assert isinstance(words, tuple), f"has_flag needs words, got {words!r}. Fix: pass a tuple."
    return any(re.fullmatch(flag_pattern, word) for word in words[1:])


def flag_pattern_of(flag: str) -> str:
    assert flag.startswith(OPTION_PREFIX), f"flag_pattern_of needs an option, got {flag!r}. Fix: pass a word that starts with {OPTION_PREFIX!r}."
    short = SHORT_FLAG.fullmatch(flag)
    if short is None and not LONG_FLAG.fullmatch(flag):
        raise ValueError(f"flag {flag!r} is not one short letter such as -f or one long option such as --full. Rule: an action names one option per word. Fix: write -f or --full.")
    pattern = SHORT_CLUSTER_PATTERN.format(letter=short[1]) if short else re.escape(flag)
    assert has_flag(("program", flag), pattern), f"the pattern {pattern!r} misses the flag {flag!r} as an operand"
    return pattern


def parse_action(action: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
    assert isinstance(action, str) and action.strip(), f"parse_action needs text, got {action!r}. Fix: pass the action from the plan."
    words = action.split()
    first_flag = next((index for index, word in enumerate(words) if word.startswith(OPTION_PREFIX)), len(words))
    command_words, flag_words = tuple(words[:first_flag]), words[first_flag:]
    if not command_words or not all(word.startswith(OPTION_PREFIX) for word in flag_words):
        raise ValueError(f"action {action!r} must be command words, then options. Rule: options come last. Fix: write for example `pgrep -f`.")
    patterns = tuple(flag_pattern_of(word) for word in flag_words)
    assert len(patterns) == len(flag_words), f"parse_action lost an option of {action!r}"
    return command_words, patterns
