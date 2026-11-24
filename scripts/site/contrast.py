import re

HEX_COLOUR = re.compile(r"^#([0-9a-fA-F]{2})([0-9a-fA-F]{2})([0-9a-fA-F]{2})$")
TOKEN_DECLARATION = re.compile(r"--([a-z][a-z-]*):\s*(#[0-9a-fA-F]{6})\s*;")
CHANNEL_MAX = 255
HEX_BASE = 16
LINEAR_THRESHOLD = 0.03928
LINEAR_DIVISOR = 12.92
GAMMA_OFFSET = 0.055
GAMMA_SCALE = 1.055
GAMMA_EXPONENT = 2.4
RED_WEIGHT = 0.2126
GREEN_WEIGHT = 0.7152
BLUE_WEIGHT = 0.0722
FLARE = 0.05
DECIMALS = 2
TEXT_MINIMUM = 4.5
BACKGROUND = "bg"
TEXT_TOKENS = ("text", "muted", "link", "keep", "warn", "bad")
FILL_TOKENS = ("yellow", "orange", "panel")
TEXT_ON_FILL = "text"
PAIRS = tuple((token, BACKGROUND, TEXT_MINIMUM) for token in TEXT_TOKENS) + tuple((TEXT_ON_FILL, fill, TEXT_MINIMUM) for fill in FILL_TOKENS)


def channel_luminance(value):
    assert 0 <= value <= CHANNEL_MAX, f"a colour channel runs from 0 to {CHANNEL_MAX}, got {value}. Fix: pass a hex digit pair."
    assert isinstance(value, int), f"a colour channel is an integer, got {type(value).__name__}. Fix: parse the hex digits."
    scaled = value / CHANNEL_MAX
    if scaled <= LINEAR_THRESHOLD:
        return scaled / LINEAR_DIVISOR
    return ((scaled + GAMMA_OFFSET) / GAMMA_SCALE) ** GAMMA_EXPONENT


def luminance(colour):
    matched = HEX_COLOUR.match(colour)
    assert matched, f"a colour is #rrggbb, got {colour!r}. Fix: write six hex digits."
    red, green, blue = (channel_luminance(int(digits, HEX_BASE)) for digits in matched.groups())
    result = RED_WEIGHT * red + GREEN_WEIGHT * green + BLUE_WEIGHT * blue
    assert 0 <= result <= 1, f"luminance of {colour} is {result}, outside 0 to 1. Fix: correct the weights."
    return result


def ratio(foreground, background):
    first, second = luminance(foreground), luminance(background)
    assert foreground and background, f"ratio needs two colours, got {foreground!r} and {background!r}. Fix: pass hex colours."
    lighter, darker = max(first, second), min(first, second)
    result = (lighter + FLARE) / (darker + FLARE)
    assert result >= 1, f"a contrast ratio is at least 1, got {result}. Fix: correct the formula."
    return round(result, DECIMALS)


def tokens_of(css):
    assert isinstance(css, str), f"tokens_of needs css text, got {type(css).__name__}. Fix: pass the stylesheet."
    tokens = dict(TOKEN_DECLARATION.findall(css))
    assert tokens, "the stylesheet declares no colour tokens. Rule: colours are --name: #rrggbb tokens. Fix: declare them in :root."
    return tokens


def contrast_problems(css):
    tokens = tokens_of(css)
    assert BACKGROUND in tokens, f"the stylesheet has no --{BACKGROUND} token, got {sorted(tokens)}. Rule: every pair sits on the page background. Fix: declare it."
    problems = []
    assert PAIRS, "no colour pairs are checked. Rule: a check with no pairs proves nothing. Fix: restore PAIRS."
    for foreground, background, minimum in PAIRS:
        absent = [name for name in (foreground, background) if name not in tokens]
        if absent:
            problems += [f"the stylesheet has no --{name} token. Rule: every text colour is a token. Fix: declare it." for name in absent]
            continue
        for first, second in ((foreground, background), (background, foreground)):
            measured = ratio(tokens[first], tokens[second])
            if measured < minimum:
                problems.append(f"--{first} on --{second} measures {measured}:1, under {minimum}:1. Rule: WCAG AA text contrast in both directions. Fix: darken or lighten --{foreground}.")
    assert all(isinstance(problem, str) for problem in problems), f"problems must be text, got {problems!r}"
    return problems
