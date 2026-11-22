from itertools import takewhile

from willitharness.counts import Counts
from willitharness.detectors import Call, shell_segments
from willitharness.guard import program_words
from willitharness.stream import BASH_TOOL

FLAG_PREFIX = "-"
MIN_RATE_GAP = 0.2
MIN_ARMS = 2
NO_DIFFERENCE_LINE = "no command differs between arms"
NOT_PART_OF_RULE_LINE = "not part of the rule under test"
CHANNELS_HEADING = "alternative channels (tools other than Bash):"


def command_key(segment: tuple[str, ...]) -> str:
    words = program_words(segment)
    assert words, f"command_key needs a program, got only assignments in {segment!r}. Fix: skip such segments."
    flags = takewhile(lambda word: word.startswith(FLAG_PREFIX), words[1:])
    result = " ".join((words[0], *flags))
    assert result.startswith(words[0]), f"command_key lost the program of {segment!r}: {result!r}"
    return result


def commands_of_run(run: tuple[Call, ...]) -> frozenset[str]:
    assert all(isinstance(call, Call) for call in run), f"commands_of_run needs calls, got {run!r}. Fix: build them with calls_of."
    segments = (segment for call in run if call.tool == BASH_TOOL for segment in shell_segments(call.command))
    result = frozenset(command_key(segment) for segment in segments if program_words(segment))
    assert all(result), f"commands_of_run built an empty command from {run!r}"
    return result


def channels_of_run(run: tuple[Call, ...]) -> frozenset[str]:
    assert all(isinstance(call, Call) for call in run), f"channels_of_run needs calls, got {run!r}. Fix: build them with calls_of."
    result = frozenset(call.tool for call in run if call.tool != BASH_TOOL)
    assert BASH_TOOL not in result, f"channels_of_run listed {BASH_TOOL} as an alternative channel"
    return result


def counts_by_name(runs_by_arm: dict, names_of_run) -> dict[str, dict[str, Counts]]:
    assert runs_by_arm and callable(names_of_run), f"counts_by_name needs arms and a name reader, got {runs_by_arm!r}, {names_of_run!r}. Fix: pass both."
    names_by_arm = {arm: [names_of_run(run) for run in runs] for arm, runs in runs_by_arm.items()}
    every_name = sorted(set().union(*(names for per_run in names_by_arm.values() for names in per_run)))
    result = {
        name: {arm: Counts(sum(name in names for names in per_run), len(per_run)) for arm, per_run in names_by_arm.items()}
        for name in every_name
    }
    assert all(set(per_arm) == set(runs_by_arm) for per_arm in result.values()), f"a name lost an arm in {result!r}"
    return result


def differs(per_arm: dict[str, Counts]) -> bool:
    assert len(per_arm) >= MIN_ARMS, f"differs needs {MIN_ARMS} arms, got {list(per_arm)!r}. Fix: pass every arm."
    rates = [counts.rate() for counts in per_arm.values()]
    result = max(rates) - min(rates) >= MIN_RATE_GAP
    assert all(0.0 <= rate <= 1.0 for rate in rates), f"differs got a rate outside [0, 1]: {rates!r}"
    return result


def counted_line(name: str, per_arm: dict[str, Counts]) -> str:
    assert per_arm, f"counted_line needs counts for {name!r}. Fix: pass one Counts per arm."
    shown = ", ".join(f"{arm} {counts.successes} of {counts.runs} runs" for arm, counts in per_arm.items())
    assert name in f"{name}: {shown}", f"counted_line lost the name {name!r}"
    return f"{name}: {shown}"


def side_effect_report_lines(runs_by_arm: dict) -> list[str]:
    assert len(runs_by_arm) >= MIN_ARMS, f"the side-effect report needs {MIN_ARMS} arms, got {list(runs_by_arm)!r}. Rule: it compares arms. Fix: pass every arm."
    assert all(runs for runs in runs_by_arm.values()), f"an arm has no runs in {list(runs_by_arm)!r}. Rule: counts divide by runs. Fix: pass the usable runs of each arm."
    differing = [counted_line(name, per_arm) for name, per_arm in counts_by_name(runs_by_arm, commands_of_run).items() if differs(per_arm)]
    lines = [*differing, NOT_PART_OF_RULE_LINE] if differing else [NO_DIFFERENCE_LINE]
    channels = counts_by_name(runs_by_arm, channels_of_run)
    if channels:
        lines += [CHANNELS_HEADING, *(counted_line(name, per_arm) for name, per_arm in channels.items())]
    assert lines, "the side-effect report is empty"
    assert (NO_DIFFERENCE_LINE in lines) != bool(differing), f"the no-difference line disagrees with the listed commands: {lines!r}"
    return lines
