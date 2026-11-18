import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from willitharness.detectors import shell_segments, starts_with_action
from willitharness.paths import inside
from willitharness.stream import BASH_TOOL
from willitharness.vocabulary import Coverage, GuardResult, Verdict

ENV_PROGRAM = "env"
ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
PLACEHOLDER = re.compile(r"^[A-Z][A-Z_]*(\.\.\.)?$")
BACKTICKED = re.compile(r"`([^`]+)`")
OPTION_PREFIX = "-"
MIN_TARGET_OPERANDS = 2
REJECTION = "rejected: no runnable alternative"
CHECK_MESSAGES = "check-messages"
USAGE_EXIT_CODE = 2
REJECTED_EXIT_CODE = 1
ACCEPTED_EXIT_CODE = 0

NOT_MATCHING_COMPLETED_VERDICTS = frozenset({Verdict.FIRST_LOWER})
UNTESTED_COMPLETED_VERDICTS = frozenset({Verdict.INCONCLUSIVE_SMALL_N})


def evaluate(completed: Verdict | None, coverage: Coverage, zero_bypass: bool) -> GuardResult:
    assert completed is None or completed in Verdict, f"unknown completed verdict {completed!r}"
    assert coverage in Coverage and isinstance(zero_bypass, bool), (
        f"coverage must be a Coverage and bypass a flag, got {coverage!r}, {zero_bypass!r}"
    )
    untested = completed is None or completed in UNTESTED_COMPLETED_VERDICTS or coverage is Coverage.NONE_SEEN
    if untested:
        result = GuardResult.GUARD_UNTESTED
    elif completed not in NOT_MATCHING_COMPLETED_VERDICTS and coverage is Coverage.FULL and zero_bypass:
        result = GuardResult.GUARD_MATCHES_RULE
    else:
        result = GuardResult.GUARD_WORSE
    assert (result is GuardResult.GUARD_UNTESTED) == untested, f"G1 broken: {result} for completed {completed!r}, {coverage}"
    assert result is not GuardResult.GUARD_MATCHES_RULE or (
        coverage is Coverage.FULL and zero_bypass and completed not in NOT_MATCHING_COMPLETED_VERDICTS
    ), f"G1 broken: {result} for {completed!r}, coverage {coverage}, bypass-free {zero_bypass}"
    return result


@dataclass(frozen=True)
class BlockedProgram:
    program: str
    flag_pattern: str
    writes_target: bool
    equivalent_markers: tuple[str, ...]


@dataclass(frozen=True)
class GuardRule:
    name: str
    message: str
    offered_alternatives: tuple[str, ...]
    blocked: tuple[BlockedProgram, ...]


@dataclass(frozen=True)
class Hit:
    rule: GuardRule
    entry: BlockedProgram
    segment: tuple[str, ...]


@dataclass(frozen=True)
class Decision:
    blocked: bool
    message: str


def guard_rule_of(entry: dict) -> GuardRule:
    assert isinstance(entry, dict) and entry.get("name") and entry.get("message"), (
        f"a guard rule needs a name and a message, got {entry!r}. Rule: a block says what to do. Fix: add both."
    )
    blocked = tuple(
        BlockedProgram(item["program"], item.get("flag_pattern", ""), item.get("writes_target", False), tuple(item.get("equivalent_markers", ())))
        for item in entry.get("blocked", ())
    )
    assert blocked, f"guard rule {entry['name']} blocks no program. Rule: a rule names a program. Fix: add a blocked entry."
    return GuardRule(entry["name"], entry["message"], tuple(entry.get("offered_alternatives", ())), blocked)


def load_rules(directory: Path, name: str) -> tuple[GuardRule, ...]:
    path = inside(directory, name)
    assert path.is_file(), f"{path} is not a file. Rule: the guard reads its rules from a JSON file in {directory}. Fix: pass the rules file name."
    rules = tuple(guard_rule_of(entry) for entry in json.loads(path.read_text()))
    assert rules, f"{path} holds no guard rules. Rule: a guard with no rules blocks nothing. Fix: add a rule."
    return rules


def program_words(segment: tuple[str, ...]) -> tuple[str, ...]:
    assert all(isinstance(word, str) for word in segment), f"a segment is words, got {segment!r}. Fix: build it with shell_segments."
    words = list(segment)
    while words and (words[0] == ENV_PROGRAM or ASSIGNMENT.match(words[0])):
        words.pop(0)
    assert len(words) <= len(segment), f"program_words grew the segment {segment!r} into {words!r}"
    return tuple(words)


def has_flag(words: tuple[str, ...], flag_pattern: str) -> bool:
    assert flag_pattern, "has_flag needs a pattern. Fix: pass a regular expression for the option."
    assert isinstance(words, tuple), f"has_flag needs words, got {words!r}. Fix: pass a tuple."
    return any(re.fullmatch(flag_pattern, word) for word in words[1:])


def entry_matches(entry: BlockedProgram, words: tuple[str, ...]) -> bool:
    assert entry.program, f"a blocked entry names a program, got {entry!r}. Rule: a rule names what it blocks. Fix: add program."
    assert all(words), f"entry_matches needs non-empty words, got {words!r}. Fix: build them with shell_segments."
    return bool(words) and words[0] == entry.program and (not entry.flag_pattern or has_flag(words, entry.flag_pattern))


def hits_of(command: str, rules: tuple[GuardRule, ...]) -> tuple[Hit, ...]:
    assert command.strip(), f"hits_of needs a command, got {command!r}. Fix: pass a command line."
    assert all(isinstance(rule, GuardRule) for rule in rules), f"hits_of needs GuardRules, got {rules!r}. Fix: load them with load_rules."
    found = tuple(
        Hit(rule, entry, segment)
        for segment in map(program_words, shell_segments(command))
        for rule in rules
        for entry in rule.blocked
        if entry_matches(entry, segment)
    )
    assert all(hit.segment for hit in found), f"a hit has no words in {found!r}"
    return found


def decide_command(command: str, rules: tuple[GuardRule, ...]) -> Decision:
    assert command.strip(), f"decide_command needs a command, got {command!r}. Fix: pass a command line."
    assert rules, "decide_command needs rules. Rule: a guard with no rules blocks nothing. Fix: load them with load_rules."
    found = hits_of(command, rules)
    decision = Decision(True, found[0].rule.message) if found else Decision(False, "")
    assert decision.blocked == bool(found), f"decision {decision} disagrees with {len(found)} hits"
    assert not decision.blocked or decision.message, f"G1: a block for {command!r} carries no message. Rule: a block says what to do."
    return decision


def target_of(hit: Hit) -> str | None:
    assert hit.segment, f"target_of needs a hit with words, got {hit!r}. Fix: build it with hits_of."
    assert hit.segment[0] == hit.entry.program, f"the hit {hit!r} starts with another program than its entry. Fix: build it with hits_of."
    operands = [word for word in hit.segment[1:] if not word.startswith(OPTION_PREFIX)]
    result = operands[-1] if hit.entry.writes_target and len(operands) >= MIN_TARGET_OPERANDS else None
    assert result is None or result in hit.segment, f"target {result!r} is not a word of {hit.segment!r}"
    return result


def offered_prefix(alternative: str) -> tuple[str, ...]:
    segments = shell_segments(alternative)
    first = segments[0] if segments else ()
    words = []
    for word in first:
        if PLACEHOLDER.match(word):
            break
        words.append(word)
    assert len(words) <= len(first), f"the prefix {words!r} is longer than the first segment {first!r}"
    assert all(not PLACEHOLDER.match(word) for word in words), f"a placeholder stayed in the prefix {words!r}"
    return tuple(words)


def rejection_of(entry: dict) -> str | None:
    message = entry.get("message", "")
    assert isinstance(message, str), f"a message is text, got {message!r}. Fix: write the message as a string."
    alternatives = entry.get("offered_alternatives", [])
    named = set(BACKTICKED.findall(message))
    runnable = bool(alternatives) and all(offered_prefix(alternative) and alternative in named for alternative in alternatives)
    result = None if runnable else f"{REJECTION}: {message}"
    assert (result is None) == runnable, f"rejection {result!r} disagrees with runnable {runnable}"
    assert result is None or result.startswith(REJECTION), f"rejection {result!r} lost the fixed wording"
    return result


def check_messages(entries: list) -> tuple[int, list[str]]:
    assert isinstance(entries, list) and entries, f"check_messages needs a non-empty list, got {entries!r}. Fix: list the messages."
    rejections = [found for found in map(rejection_of, entries) if found]
    accepted = len(entries) - len(rejections)
    assert accepted >= 0 and accepted + len(rejections) == len(entries), f"{accepted} accepted and {len(rejections)} rejected of {len(entries)}"
    assert all(line.startswith(REJECTION) for line in rejections), f"a rejection lost its wording: {rejections!r}"
    return accepted, rejections


def coverage_of(calls: tuple, action: str, rules: tuple[GuardRule, ...]) -> Coverage:
    assert action.strip(), f"coverage_of needs the violating action, got {action!r}. Rule: coverage counts violating commands. Fix: pass the detector action."
    assert rules, "coverage_of needs rules. Fix: load them with load_rules."
    violating = [call.command for call in calls if call.tool == BASH_TOOL and starts_with_action(call.command, action)]
    if not violating:
        result = Coverage.NONE_SEEN
    elif all(decide_command(command, rules).blocked for command in violating):
        result = Coverage.FULL
    else:
        result = Coverage.PARTIAL
    assert (result is Coverage.NONE_SEEN) == (not violating), f"coverage {result} for {len(violating)} violating commands"
    assert result is not Coverage.FULL or violating, "Full coverage needs at least one violating command"
    return result


def main(arguments: list[str]) -> int:
    assert isinstance(arguments, list), f"main needs a list of arguments, got {arguments!r}. Fix: pass sys.argv[1:]."
    if len(arguments) != 2 or arguments[0] != CHECK_MESSAGES:
        sys.stderr.write(f"usage: guard {CHECK_MESSAGES} <messages-file>, got {arguments!r}\n")
        return USAGE_EXIT_CODE
    accepted, rejections = check_messages(json.loads(Path(arguments[1]).read_text()))
    summary = f"messages: {accepted} accepted, {len(rejections)} rejected"
    stream = sys.stderr if rejections else sys.stdout
    stream.write("\n".join([*rejections, summary]) + "\n")
    code = REJECTED_EXIT_CODE if rejections else ACCEPTED_EXIT_CODE
    assert (code == ACCEPTED_EXIT_CODE) == (not rejections), f"exit code {code} disagrees with {len(rejections)} rejections"
    assert summary, "a run must print its summary"
    return code


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
