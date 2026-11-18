import copy

import pytest

from willitharness import plan
from willitharness.plan import PlanError, load_plan

EXPECTED_DEFAULT_REPS = 20
EXPECTED_MAX_RETRIES = 2
EXPECTED_MIN_PROBE_RUNS = 3
BUDGET = 2.0
RUN_CAP = 0.5
VALID = {
    "schema": 1,
    "name": "pilot",
    "budget_usd": BUDGET,
    "run_cap_usd": RUN_CAP,
    "arms": [
        {"label": "C", "role": "leave_one_out", "overlay": "arms/C"},
        {"label": "C2", "role": "noise_of:C", "overlay": "arms/C"},
        {"label": "B", "role": "rule", "overlay": "arms/B"},
    ],
}


def changed(updates):
    data = copy.deepcopy(VALID)
    data.update(updates)
    return data


def rejection(data):
    with pytest.raises(PlanError) as raised:
        load_plan(data)
    return str(raised.value)


def test_the_constants_match_the_contract():
    assert plan.DEFAULT_REPS == EXPECTED_DEFAULT_REPS, f"{plan.DEFAULT_REPS=}"
    assert plan.MAX_RETRIES == EXPECTED_MAX_RETRIES, f"{plan.MAX_RETRIES=}"
    assert plan.MIN_PROBE_RUNS == EXPECTED_MIN_PROBE_RUNS, f"{plan.MIN_PROBE_RUNS=}"


def test_a_plan_without_reps_or_retries_gets_the_defaults():
    loaded = load_plan(VALID)
    assert loaded.reps == EXPECTED_DEFAULT_REPS, f"reps default is {loaded.reps}"
    assert loaded.max_retries == EXPECTED_MAX_RETRIES, f"max_retries default is {loaded.max_retries}"


def test_explicit_reps_and_retries_are_kept():
    loaded = load_plan(changed({"reps": 7, "max_retries": 0}))
    assert (loaded.reps, loaded.max_retries) == (7, 0), f"got reps {loaded.reps}, retries {loaded.max_retries}"


def test_L8_a_noise_repeat_of_the_rule_arm_is_rejected_with_the_named_arms():
    data = changed({"arms": [
        {"label": "C", "role": "leave_one_out", "overlay": "arms/C"},
        {"label": "B", "role": "rule", "overlay": "arms/B"},
        {"label": "B2", "role": "noise_of:B", "overlay": "arms/B"},
    ]})
    message = rejection(data)
    assert "noise pair must repeat the LOO arm C; B2 repeats B" in message, f"unexpected message {message!r}"
    assert "Fix:" in message, f"the message must end with a fix, got {message!r}"


def test_L8_a_noise_repeat_with_no_loo_arm_is_rejected():
    data = changed({"arms": [
        {"label": "B", "role": "rule", "overlay": "arms/B"},
        {"label": "B2", "role": "noise_of:B", "overlay": "arms/B"},
    ]})
    message = rejection(data)
    assert "has no LOO arm" in message, f"unexpected message {message!r}"


def test_two_loo_arms_are_rejected():
    data = changed({"arms": [
        {"label": "C", "role": "leave_one_out", "overlay": "arms/C"},
        {"label": "D", "role": "leave_one_out", "overlay": "arms/D"},
    ]})
    message = rejection(data)
    assert "all leave_one_out" in message, f"unexpected message {message!r}"


def test_repeated_labels_are_rejected():
    data = changed({"arms": [
        {"label": "B", "role": "rule", "overlay": "arms/B"},
        {"label": "B", "role": "guard_only", "overlay": "arms/D"},
    ]})
    message = rejection(data)
    assert "['B'] repeat" in message, f"unexpected message {message!r}"


def test_an_unknown_role_is_rejected():
    data = changed({"arms": [{"label": "B", "role": "banana", "overlay": "arms/B"}]})
    message = rejection(data)
    assert "role 'banana'" in message, f"unexpected message {message!r}"


def test_a_run_cap_above_the_budget_is_rejected():
    message = rejection(changed({"run_cap_usd": BUDGET * 2}))
    assert "above budget_usd" in message, f"unexpected message {message!r}"


def test_a_boolean_budget_is_rejected():
    message = rejection(changed({"budget_usd": True}))
    assert "budget_usd is True" in message, f"unexpected message {message!r}"


def test_zero_reps_are_rejected():
    message = rejection(changed({"reps": 0}))
    assert "reps is 0" in message, f"unexpected message {message!r}"


def test_another_schema_version_is_rejected():
    message = rejection(changed({"schema": 2}))
    assert "schema is 2" in message, f"unexpected message {message!r}"
