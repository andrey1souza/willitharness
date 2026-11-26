import re
from dataclasses import dataclass
from pathlib import Path

from willitharness.load_report import CODE_SPAN, FENCES
from willitharness.paths import PathOutsideRoot, inside

ENFORCED = "enforced by a script"
COMMAND = "command rule, testable candidate"
NOT_TESTABLE = "not testable by behaviour"
FORBIDS = "forbids"
REQUIRES = "requires"
SCRIPT_SUFFIXES = (".sh", ".bash", ".zsh", ".py", ".js", ".mjs", ".ts", ".rb")
BULLET = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+(.*)$")
CONTINUATION = re.compile(r"^\s+\S")
WORD = re.compile(r"[\w']+")
FORBID_CUE = re.compile(r"\b(?:never|do not|don't|must not)\b")
REQUIRE_CUE = re.compile(r"\b(?:always|use|run|prefer|push|call|execute|invoke)\b")
SENTENCE_END = re.compile(r"[.;!?]\s")
WHOLE_COMMAND = re.compile(r"^`([^`]+)`[.:]?$")
FORBID_USE = re.compile(r"\b(?:never|do not|don't|must not) (?:use|run|call)$")
SPAN_EDGE = "`"

REASON_ENFORCED = "names {path}, which exists in the repo; a script already checks it"
REASON_COMMAND = "{direction} the command `{command}`; a behaviour test can watch the calls"
REASON_MISSING_PATH = "names `{path}`, which does not exist in the repo; no script backs it, and no command is named"
REASON_WHOLE_COMMAND = "the whole rule is the command `{command}`, so it requires that command; a behaviour test can watch the calls"
REASON_SPAN_NOT_COMMAND = "its backticked text {spans} is not a command the rule forbids or requires; a behaviour test has no call to watch"
REASON_PROSE = "names no command in backticks and no script that exists; a behaviour test has no call to watch"


@dataclass(frozen=True)
class Rule:
    source: str
    line: int
    text: str


@dataclass(frozen=True)
class Classification:
    label: str
    reason: str
    direction: str | None
    command: str | None


def extract_rules(source, text):
    assert isinstance(text, str), f"extract_rules needs text, got {text!r}. Fix: pass the file text."
    rules = []
    fenced = False
    open_rule = False
    for number, line in enumerate(text.splitlines(), start=1):
        bullet = BULLET.match(line)
        if line.lstrip().startswith(FENCES):
            fenced = not fenced
            open_rule = False
        elif fenced:
            continue
        elif bullet:
            rules.append(Rule(source, number, bullet.group(1).strip()))
            open_rule = True
        elif open_rule and CONTINUATION.match(line):
            previous = rules[-1]
            rules[-1] = Rule(previous.source, previous.line, f"{previous.text} {line.strip()}")
        else:
            open_rule = False
    assert all(rule.text for rule in rules), f"a rule of {source} has no text: {rules!r}"
    return rules


def spans_of(text):
    assert isinstance(text, str), f"spans_of needs text, got {text!r}. Fix: pass the rule text."
    spans = [(found.start(), found.group(0).strip(SPAN_EDGE)) for found in CODE_SPAN.finditer(text)]
    assert all(span for _, span in spans) or SPAN_EDGE in text, f"spans_of returned {spans!r} for {text!r}. Rule: a span has text."
    return spans


def script_candidate(span):
    assert isinstance(span, str), f"script_candidate needs the text of a span, got {span!r}. Fix: pass a string."
    words = span.split()
    candidate = words[0] if words and words[0].endswith(SCRIPT_SUFFIXES) else None
    assert candidate is None or candidate in span, f"script_candidate returned {candidate!r} for {span!r}. Rule: it is a word of the span."
    return candidate


def existing_script(root, span):
    assert isinstance(root, Path) and root.is_dir(), f"existing_script needs the project folder, got {root!r}. Fix: pass the folder."
    assert isinstance(span, str), f"existing_script needs the text of a span, got {span!r}. Fix: pass a string."
    candidate = script_candidate(span)
    if candidate is None:
        return None
    try:
        found = inside(root, candidate).is_file()
    except (PathOutsideRoot, OSError):
        found = False
    assert found in (True, False), f"existing_script computed {found!r} for {candidate!r}. Rule: a file exists or it does not."
    return candidate if found else None


def script_like_paths(spans):
    assert isinstance(spans, list), f"script_like_paths needs a list of spans, got {spans!r}. Fix: pass the output of spans_of."
    found = [candidate for _, span in spans if (candidate := script_candidate(span))]
    assert len(found) <= len(spans), f"script_like_paths found {found!r} in {spans!r}. Rule: one candidate per span at most."
    return found


def clause_before(text, start):
    assert isinstance(text, str) and 0 <= start <= len(text), f"clause_before needs a start inside the text, got {start!r} for {text!r}. Fix: pass a span start."
    before = text[:start]
    ends = [found.end() for found in SENTENCE_END.finditer(before)]
    clause = before[ends[-1]:] if ends else before
    assert before.endswith(clause), f"clause_before returned {clause!r}, which does not end {before!r}. Rule: a clause is the tail of the text."
    return clause


def direction_of(text, start, span):
    assert isinstance(text, str) and isinstance(start, int), f"direction_of needs the rule text and a start, got {text!r} and {start!r}. Fix: pass both."
    assert isinstance(span, str) and span, f"direction_of needs a span, got {span!r}. Fix: pass the span text."
    window = " ".join(WORD.findall(clause_before(text, start))).lower()
    bare = len(span.split()) == 1
    if bare:
        direction = FORBIDS if FORBID_USE.search(window) else None
    elif FORBID_CUE.search(window):
        direction = FORBIDS
    else:
        direction = REQUIRES if REQUIRE_CUE.search(window) else None
    assert direction in (FORBIDS, REQUIRES, None), f"direction_of returned {direction!r} for {span!r}. Rule: forbids, requires or none."
    return direction


def classify_rule(text, root):
    assert isinstance(text, str) and text, f"classify_rule needs the rule text, got {text!r}. Fix: pass the text of a rule."
    assert isinstance(root, Path) and root.is_dir(), f"classify_rule needs the project folder, got {root!r}. Fix: pass the folder."
    spans = spans_of(text)
    scripts = [found for found in (existing_script(root, span) for _, span in spans) if found]
    if scripts:
        return Classification(ENFORCED, REASON_ENFORCED.format(path=scripts[0]), None, None)
    whole = WHOLE_COMMAND.match(text.strip())
    command = whole.group(1) if whole else ""
    if len(command.split()) > 1:
        return Classification(COMMAND, REASON_WHOLE_COMMAND.format(command=command), REQUIRES, command)
    for start, span in spans:
        direction = direction_of(text, start, span)
        if direction:
            return Classification(COMMAND, REASON_COMMAND.format(direction=direction, command=span), direction, span)
    missing = script_like_paths(spans)
    shown = ", ".join(f"`{span}`" for _, span in spans)
    reason = REASON_MISSING_PATH.format(path=missing[0]) if missing else REASON_SPAN_NOT_COMMAND.format(spans=shown) if spans else REASON_PROSE
    return Classification(NOT_TESTABLE, reason, None, None)
