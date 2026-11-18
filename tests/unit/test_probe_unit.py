import json

import pytest

from willitharness import plan
from willitharness.probe import (
    MIN_PROBE_RUNS,
    ProbeRefused,
    ProbeRun,
    check_requested_runs,
    classify,
    loo_arm_valid,
    parse_run,
    probe,
)
from willitharness.vocabulary import Reach

TARGET = "ZQ-8841-lumen"
CONTROL = "purple-giraffe-91"
PROBE_RUNS = 5
EXPECTED_MIN_PROBE_RUNS = 3


def test_min_probe_runs_is_three():
    assert MIN_PROBE_RUNS == EXPECTED_MIN_PROBE_RUNS, f"{MIN_PROBE_RUNS=}"


def test_P1_too_few_runs_is_unknown_whatever_the_hits():
    short = classify(MIN_PROBE_RUNS - 1, MIN_PROBE_RUNS - 1, 0)
    empty = classify(0, 0, 0)
    assert short is Reach.UNKNOWN, f"{short=} with {MIN_PROBE_RUNS - 1} runs"
    assert empty is Reach.UNKNOWN, f"{empty=} with no runs"


def test_P2_any_control_hit_is_unknown():
    every_target = classify(PROBE_RUNS, PROBE_RUNS, 1)
    no_target = classify(PROBE_RUNS, 0, 1)
    assert every_target is Reach.UNKNOWN, f"{every_target=} with one control hit"
    assert no_target is Reach.UNKNOWN, f"{no_target=} with one control hit"


def test_P3_every_run_hit_is_loaded():
    many = classify(PROBE_RUNS, PROBE_RUNS, 0)
    minimum = classify(MIN_PROBE_RUNS, MIN_PROBE_RUNS, 0)
    assert many is Reach.LOADED, f"{many=} for {PROBE_RUNS} of {PROBE_RUNS}"
    assert minimum is Reach.LOADED, f"{minimum=} for {MIN_PROBE_RUNS} of {MIN_PROBE_RUNS}"


def test_P3_no_run_hit_is_masked():
    result = classify(PROBE_RUNS, 0, 0)
    assert result is Reach.MASKED, f"{result=} for 0 of {PROBE_RUNS}"


def test_P3_some_runs_hit_is_unknown():
    result = classify(PROBE_RUNS, 2, 0)
    assert result is Reach.UNKNOWN, f"{result=} for 2 of {PROBE_RUNS}"


@pytest.mark.parametrize(("probe", "valid"), [(Reach.LOADED, True), (Reach.MASKED, False), (Reach.UNKNOWN, False)])
def test_P4_only_a_loaded_loo_probe_is_valid(probe, valid):
    result = loo_arm_valid(probe)
    assert result is valid, f"{result=} expected {valid=} for {probe=}"


def transcript_with_result(result_event):
    return [json.dumps({"type": "system"}), json.dumps(result_event)]


def success(text):
    return {"type": "result", "subtype": "success", "is_error": False, "result": text}


def test_P1_a_probe_ignores_unusable_runs_when_counting():
    runs = [ProbeRun(True, True, False), ProbeRun(True, True, False), ProbeRun(False, True, False)]
    result = probe(runs)
    assert result.reach is Reach.UNKNOWN, f"two usable runs must give Unknown, got {result}"


def test_P2_the_control_message_is_exact():
    runs = [ProbeRun(True, True, True), ProbeRun(True, True, False), ProbeRun(True, True, False)]
    result = probe(runs)
    assert result.message == "control token appeared; the probe cannot be trusted", f"unexpected message {result.message!r}"


def test_P3_a_loaded_probe_reports_the_counts():
    result = probe([ProbeRun(True, True, False)] * PROBE_RUNS)
    assert (result.reach, result.message) == (Reach.LOADED, "the target token appeared in 5 of 5 runs"), f"got {result}"


def test_a_transcript_without_a_result_event_is_unusable():
    run = parse_run([json.dumps({"type": "system"})], TARGET, CONTROL)
    assert not run.usable, f"a transcript with no result event must be unusable, got {run}"


def test_a_transcript_with_an_error_result_is_unusable():
    event = {"type": "result", "subtype": "success", "is_error": True, "result": TARGET}
    run = parse_run(transcript_with_result(event), TARGET, CONTROL)
    assert not run.usable, f"an error result must be unusable even when it holds the token, got {run}"


def test_a_transcript_with_a_failure_subtype_is_unusable():
    event = {"type": "result", "subtype": "error_max_turns", "is_error": False, "result": TARGET}
    run = parse_run(transcript_with_result(event), TARGET, CONTROL)
    assert not run.usable, f"a non-success subtype must be unusable, got {run}"


def test_a_transcript_with_a_broken_line_is_unusable():
    run = parse_run(["{not json"], TARGET, CONTROL)
    assert not run.usable, f"a line that is not JSON must make the run unusable, got {run}"


def test_a_reply_with_the_target_token_is_a_target_hit_only():
    run = parse_run(transcript_with_result(success(f"it is {TARGET}")), TARGET, CONTROL)
    assert (run.usable, run.target_hit, run.control_hit) == (True, True, False), f"got {run}"


def test_a_reply_with_the_control_token_is_a_control_hit():
    run = parse_run(transcript_with_result(success(f"maybe {CONTROL}")), TARGET, CONTROL)
    assert (run.usable, run.target_hit, run.control_hit) == (True, False, True), f"got {run}"


def test_the_two_tokens_must_differ():
    with pytest.raises(AssertionError) as raised:
        parse_run([], TARGET, TARGET)
    assert "must differ" in str(raised.value), f"unexpected message {str(raised.value)!r}"


def test_requesting_fewer_runs_than_the_minimum_is_refused_with_the_fix():
    with pytest.raises(ProbeRefused) as raised:
        check_requested_runs(MIN_PROBE_RUNS - 1)
    expected = "at least 3 probe runs per arm are needed; use --runs 3 or more"
    assert str(raised.value) == expected, f"unexpected message {str(raised.value)!r}"


def test_requesting_the_minimum_runs_is_accepted():
    check_requested_runs(MIN_PROBE_RUNS)
    assert MIN_PROBE_RUNS == plan.MIN_PROBE_RUNS, "the probe and the plan must share one MIN_PROBE_RUNS"
