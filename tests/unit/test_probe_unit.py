import pytest

from willitharness.probe import MIN_PROBE_RUNS, classify, loo_arm_valid
from willitharness.vocabulary import Reach

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
