import pytest
from analysis_site import FULL_ROLES, NO_PAIR_ROLES, analysis_plan_data

from willitharness.counts import Counts
from willitharness.noise import NoisePair, loo_label_of, noise_pair_of, noise_status_in
from willitharness.plan import load_plan
from willitharness.store import Cell
from willitharness.vocabulary import NoiseStatus

TASK = "stop-server"
PAIR = NoisePair("C", "C2")


def counts_of(first, second):
    return {Cell("C", TASK): Counts(*first), Cell("C2", TASK): Counts(*second)}


def test_the_noise_pair_is_the_loo_arm_and_its_repeat():
    plan = load_plan(analysis_plan_data(FULL_ROLES))
    assert noise_pair_of(plan) == PAIR, f"got {noise_pair_of(plan)}"
    assert loo_label_of(plan) == "C", f"got {loo_label_of(plan)}"


def test_a_plan_without_a_repeat_has_no_noise_pair_and_a_plan_without_a_loo_arm_has_no_label():
    assert noise_pair_of(load_plan(analysis_plan_data(NO_PAIR_ROLES))) is None, f"no repeat, no pair; roles {NO_PAIR_ROLES}"
    assert loo_label_of(load_plan(analysis_plan_data({"B": "rule"}))) is None, "no LOO arm, no label"


@pytest.mark.parametrize(
    "first, second, expected",
    [
        ((2, 20), (16, 20), NoiseStatus.NOISE_FLOOR_TOO_HIGH),
        ((16, 20), (2, 20), NoiseStatus.NOISE_FLOOR_TOO_HIGH),
        ((17, 20), (16, 20), NoiseStatus.NOISE_OK),
        ((10, 20), (2, 4), NoiseStatus.NOISE_UNMEASURED),
        ((2, 4), (10, 20), NoiseStatus.NOISE_UNMEASURED),
        ((0, 0), (0, 0), NoiseStatus.NOISE_UNMEASURED),
    ],
)
def test_V6_noise_status_follows_the_two_identical_arms(first, second, expected):
    assert noise_status_in(PAIR, counts_of(first, second), TASK) is expected, f"{first} against {second} gave {noise_status_in(PAIR, counts_of(first, second), TASK)}"
    assert noise_status_in(PAIR, counts_of(second, first), TASK) is expected, f"swapping {first} and {second} must not change the status {expected}; pair {PAIR}, task {TASK}"


def test_noise_is_read_from_the_named_task_only():
    counts = {**counts_of((17, 20), (16, 20)), Cell("C", "other"): Counts(2, 20), Cell("C2", "other"): Counts(16, 20)}
    assert noise_status_in(PAIR, counts, TASK) is NoiseStatus.NOISE_OK, f"the other task must not leak into {TASK}; pair {PAIR}, counts {counts}, expected {NoiseStatus.NOISE_OK}"
    assert noise_status_in(PAIR, counts, "other") is NoiseStatus.NOISE_FLOOR_TOO_HIGH, f"the other task has its own status; pair {PAIR}, counts {counts}, expected {NoiseStatus.NOISE_FLOOR_TOO_HIGH}"
