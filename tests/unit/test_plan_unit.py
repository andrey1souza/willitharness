import copy
import json

import pytest

from willitharness import plan
from willitharness.plan import PlanError, has_guard_arm, load_plan, read_plan

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


def test_a_plan_with_a_guard_only_arm_has_a_guard_arm():
    data = copy.deepcopy(VALID)
    data["arms"].append({"label": "G", "role": "guard_only", "overlay": "arms/G"})
    assert has_guard_arm(load_plan(data)) is True, f"an arm with role guard_only makes the plan a guard plan: {data}"


def test_a_plan_without_a_guard_only_arm_has_no_guard_arm():
    assert has_guard_arm(load_plan(VALID)) is False, f"rule, leave_one_out and noise arms are not guard arms: {VALID}"


RULE = {"id": "no-pkill", "file": "AGENTS.md", "section": "Working here", "target_outcome": "attempted_violation", "detector": "pkill", "offered_alternatives": ["kill PID"]}
TASKS = [{"id": "stop-server", "completed_check": {"kind": "calls_contain", "command": "kill"}}]


def test_a_rule_with_a_command_name_detector_loads_as_forbidden_and_a_plan_without_a_rule_still_loads():
    loaded = load_plan(changed({"rule": RULE, "tasks": TASKS}))
    assert loaded.rule.detector == plan.Detector("forbidden", ("pkill",), ""), f"got {loaded.rule.detector}"
    assert loaded.rule.offered_alternatives == ("kill PID",), f"got {loaded.rule.offered_alternatives}"
    assert loaded.tasks == (plan.Task("stop-server", plan.CompletedCheck("calls_contain", "kill")),), f"got {loaded.tasks}"
    assert (load_plan(VALID).rule, load_plan(VALID).tasks) == (None, ()), "a plan without a rule has none"


def test_R1_a_required_detector_names_its_action_and_its_point():
    detector = {"kind": "required", "action": "gbrain query", "before": "first_edit"}
    assert load_plan(changed({"rule": {**RULE, "detector": detector}})).rule.detector == plan.Detector("required", ("gbrain query",), "first_edit"), "the required detector was not kept"


@pytest.mark.parametrize(
    "detector",
    ["pkill", ["pkill"], {"kind": "forbidden", "action": "pkill"}, {"kind": "forbidden", "actions": ["pkill"]}],
)
def test_every_spelling_of_one_forbidden_action_loads_the_same_detector(detector):
    loaded = load_plan(changed({"rule": {**RULE, "detector": detector}})).rule.detector
    assert loaded == plan.Detector("forbidden", ("pkill",), ""), f"got {loaded}"
    assert loaded.before == "", "a forbidden detector has no point"


def test_a_list_detector_keeps_every_action_in_order_with_its_flags():
    actions = ["pkill", "pgrep -f", "killall"]
    loaded = load_plan(changed({"rule": {**RULE, "detector": actions}})).rule.detector
    assert loaded == plan.Detector("forbidden", ("pkill", "pgrep -f", "killall"), ""), f"got {loaded}"
    assert load_plan(changed({"rule": {**RULE, "detector": {"kind": "required", "actions": ["a", "b -x"], "before": "final_answer"}}})).rule.detector.actions == ("a", "b -x"), "the object form keeps the list"


@pytest.mark.parametrize(
    ("detector", "fragment"),
    [
        ([], "has actions []"),
        (["pkill", 3], "has actions ['pkill', 3]"),
        (["pkill", " "], "has actions ['pkill', ' ']"),
        ({"kind": "forbidden", "action": "pkill", "actions": ["pkill"]}, "both action and actions"),
        (["pgrep -fl"], "not one short letter"),
        (["-f"], "options come last"),
        (["pgrep -f vitest"], "options come last"),
        ({"kind": "forbidden"}, "has actions None"),
        ({"kind": "required", "action": "gbrain query"}, "has before ''"),
        ({"kind": "required", "action": "gbrain query", "before": "lunch"}, "has before 'lunch'"),
        ({"kind": "forbidden", "action": "pkill", "before": "first_edit"}, "only a required detector names a point"),
        ({"kind": "maybe", "action": "pkill"}, "detector kind is 'maybe'"),
        ({"kind": "forbidden", "action": " "}, "has actions ' '"),
        (7, "detector is 7"),
    ],
)
def test_a_bad_detector_is_rejected_with_a_rule_and_a_fix(detector, fragment):
    message = rejection(changed({"rule": {**RULE, "detector": detector}}))
    assert fragment in message and "Fix:" in message, f"got {message!r}"


@pytest.mark.parametrize(
    ("updates", "fragment"),
    [
        ({"target_outcome": "completed"}, "target_outcome 'completed'"),
        ({"id": ""}, "has id ''"),
        ({"section": 3}, "has section 3"),
        ({"offered_alternatives": "kill"}, "offered_alternatives 'kill'"),
    ],
)
def test_a_bad_rule_is_rejected_with_a_rule_and_a_fix(updates, fragment):
    message = rejection(changed({"rule": {**RULE, **updates}}))
    assert fragment in message and "Fix:" in message, f"got {message!r}"


@pytest.mark.parametrize(
    ("tasks", "fragment"),
    [
        ([{"id": "a", "completed_check": {"kind": "wish", "command": "kill"}}], "completed_check {'kind': 'wish'"),
        ([{"id": "a", "completed_check": {"kind": "calls_contain"}}], "has command None"),
        ([{"id": "a"}], "completed_check None"),
        ([{"id": "a", "completed_check": TASKS[0]["completed_check"]}] * 2, "['a'] repeat"),
        ("stop", "tasks is 'stop'"),
        (["stop"], "a task must be an object"),
    ],
)
def test_a_bad_task_is_rejected_with_a_rule_and_a_fix(tasks, fragment):
    message = rejection(changed({"tasks": tasks}))
    assert fragment in message and "Fix:" in message, f"got {message!r}"


def test_the_fingerprint_follows_the_rule_and_still_ignores_only_the_budget():
    base = load_plan(changed({"rule": RULE, "tasks": TASKS}))
    other = load_plan(changed({"rule": {**RULE, "detector": "pgrep"}, "tasks": TASKS}))
    richer = load_plan(changed({"rule": RULE, "tasks": TASKS, "budget_usd": BUDGET + 1}))
    assert plan.plan_fingerprint(base) != plan.plan_fingerprint(other), f"the detector is part of the plan: {base.rule} against {other.rule}"
    assert plan.plan_fingerprint(base) == plan.plan_fingerprint(richer), f"the budget is not part of the plan: {base.budget_usd} against {richer.budget_usd}"
