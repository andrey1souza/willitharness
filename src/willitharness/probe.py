import json
from dataclasses import dataclass

from willitharness.plan import MIN_PROBE_RUNS
from willitharness.vocabulary import Reach

CONTROL_MESSAGE = "control token appeared; the probe cannot be trusted"
TOO_FEW_MESSAGE = "fewer than {minimum} usable probe runs; run more probes"
SOME_RUNS_MESSAGE = "the target token appeared in {hits} of {runs} runs; the probe is inconclusive"
REFUSED_MESSAGE = "at least {minimum} probe runs per arm are needed; use --runs {minimum} or more"
RESULT_EVENT = "result"
SUCCESS_SUBTYPE = "success"


class ProbeRefused(Exception):
    pass


@dataclass(frozen=True)
class ProbeRun:
    usable: bool
    target_hit: bool
    control_hit: bool


@dataclass(frozen=True)
class ProbeResult:
    reach: Reach
    message: str


def classify(runs: int, target_hits: int, control_hits: int) -> Reach:
    assert runs >= 0, f"runs must not be negative, got {runs}"
    assert 0 <= target_hits <= runs and 0 <= control_hits <= runs, (
        f"hits must lie between 0 and runs: target {target_hits}, control {control_hits}, runs {runs}"
    )
    if runs < MIN_PROBE_RUNS or control_hits > 0:
        result = Reach.UNKNOWN
    elif target_hits == runs:
        result = Reach.LOADED
    elif target_hits == 0:
        result = Reach.MASKED
    else:
        result = Reach.UNKNOWN
    assert result is not Reach.LOADED or (runs >= MIN_PROBE_RUNS and control_hits == 0 and target_hits == runs), (
        f"P3 broken: {result} for runs {runs}, target {target_hits}, control {control_hits}"
    )
    assert result is not Reach.MASKED or (runs >= MIN_PROBE_RUNS and control_hits == 0 and target_hits == 0), (
        f"P3 broken: {result} for runs {runs}, target {target_hits}, control {control_hits}"
    )
    return result


def loo_arm_valid(loo_probe: Reach) -> bool:
    assert loo_probe in Reach, f"unknown reach {loo_probe!r}"
    result = loo_probe is Reach.LOADED
    assert result == (loo_probe == Reach.LOADED.value), f"P4 broken: {loo_probe} gave {result}"
    assert result or loo_probe is not Reach.LOADED, f"P4 broken: a Loaded LOO probe gave {result}"
    return result


def check_requested_runs(requested):
    assert isinstance(requested, int) and not isinstance(requested, bool), (
        f"requested runs must be a whole number, got {requested!r}. Fix: pass --runs N."
    )
    assert MIN_PROBE_RUNS >= 1, f"MIN_PROBE_RUNS is {MIN_PROBE_RUNS}. Rule: a probe needs at least one run."
    if requested < MIN_PROBE_RUNS:
        raise ProbeRefused(REFUSED_MESSAGE.format(minimum=MIN_PROBE_RUNS))


def parse_run(transcript, target, control):
    assert target and control, f"both tokens are needed, got target {target!r} and control {control!r}. Fix: pass both."
    assert target != control, f"the target and control tokens must differ, both are {target!r}. Fix: use two tokens."
    unusable = ProbeRun(usable=False, target_hit=False, control_hit=False)
    events = []
    for line in transcript:
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            return unusable
    finished = [event for event in events if isinstance(event, dict) and event.get("type") == RESULT_EVENT]
    if not finished:
        return unusable
    last = finished[-1]
    if last.get("subtype") != SUCCESS_SUBTYPE or last.get("is_error"):
        return unusable
    reply = str(last.get("result", ""))
    return ProbeRun(usable=True, target_hit=target in reply, control_hit=control in reply)


def probe(runs):
    assert all(isinstance(run, ProbeRun) for run in runs), f"every item must be a ProbeRun, got {runs!r}. Fix: use parse_run."
    usable = [run for run in runs if run.usable]
    usable_count = len(usable)
    target_hits = sum(run.target_hit for run in usable)
    control_hits = sum(run.control_hit for run in usable)
    reach = classify(usable_count, target_hits, control_hits)
    if usable_count < MIN_PROBE_RUNS:
        message = TOO_FEW_MESSAGE.format(minimum=MIN_PROBE_RUNS)
    elif control_hits > 0:
        message = CONTROL_MESSAGE
    elif reach is Reach.UNKNOWN:
        message = SOME_RUNS_MESSAGE.format(hits=target_hits, runs=usable_count)
    else:
        message = f"the target token appeared in {target_hits} of {usable_count} runs"
    assert message, f"a probe result needs a message, got reach {reach} for {usable_count} usable runs"
    assert (reach is Reach.UNKNOWN) or (usable_count >= MIN_PROBE_RUNS and control_hits == 0), (
        f"P1 or P2 broken: {reach} for {usable_count} usable runs and {control_hits} control hits"
    )
    return ProbeResult(reach, message)
