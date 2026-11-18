import copy
import json

import pytest

from willitharness import plan
from willitharness.plan import PlanError, load_plan, read_plan

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
    "world": "world/",
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


def test_an_arm_without_a_channel_gets_the_file_channel():
    channels = {arm.label: arm.channel for arm in load_plan(VALID).arms}
    assert channels == {"C": "file", "C2": "file", "B": "file"}, f"got {channels}"


def test_each_known_channel_is_kept():
    for channel in plan.CHANNELS:
        arms = [{"label": "B", "role": "rule", "overlay": "arms/B", "channel": channel}]
        assert load_plan(changed({"arms": arms})).arms[0].channel == channel, f"channel {channel} was not kept"


def test_an_unknown_channel_is_rejected_with_the_known_ones_and_a_fix():
    arms = [{"label": "B", "role": "rule", "overlay": "arms/B", "channel": "carrier-pigeon"}]
    message = rejection(changed({"arms": arms}))
    assert "carrier-pigeon" in message and "file, hook, skill, system_prompt" in message and "Fix:" in message, f"got {message!r}"


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


def test_a_plan_without_a_world_is_rejected_with_a_rule_and_a_fix():
    data = changed({})
    del data["world"]
    message = rejection(data)
    assert "world" in message and "Rule:" in message and "Fix:" in message, f"got {message!r}"


def test_a_plan_with_an_empty_or_non_text_world_is_rejected():
    for bad_world in ("", 7, None):
        message = rejection(changed({"world": bad_world}))
        assert "Rule:" in message and "Fix:" in message, f"world {bad_world!r} gave {message!r}"


def test_a_plan_whose_world_escapes_the_root_is_refused_when_read(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    (project / "plan.json").write_text(json.dumps(changed({"world": "../elsewhere"})))
    with pytest.raises(PlanError) as raised:
        read_plan(project, "plan.json")
    assert "outside" in str(raised.value) and "Fix:" in str(raised.value), f"got {raised.value}"


def test_a_plan_whose_world_stays_inside_the_root_is_read(tmp_path):
    (tmp_path / "plan.json").write_text(json.dumps(VALID))
    loaded = read_plan(tmp_path, "plan.json")
    assert loaded.world == VALID["world"], f"got {loaded.world!r}"
    assert loaded.name == VALID["name"], f"got {loaded.name!r}"
