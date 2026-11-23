from dataclasses import replace

import pytest
from files import plant
from lifecycle_site import STUB_COMMAND, TASK_NAME, TASK_PROMPT, SiteSpec, make_site, reach_every_arm, validate_site

from willitharness.lifecycle import LifecycleRefused, PlanState, lifecycle_dir, read_state, start_running
from willitharness.plan import CompletedCheck, Task
from willitharness.vocabulary import Reach

SMALL = SiteSpec(arm_count=2, budget_usd=1.0, run_cap_usd=0.05, reps=1, max_retries=0)
EXTRA_TASK = "restart-server"
WORLD_TASKS_FILE = "tasks.txt"
PROMPTS_DIRECTORY = "prompts"


def plan_task(task_id):
    return Task(task_id, CompletedCheck("calls_contain", STUB_COMMAND))


def validated_and_reached(site):
    validate_site(site)
    reach_every_arm(site, Reach.LOADED)
    return site


def with_plan_tasks(site, task_ids):
    return replace(site, plan=replace(site.plan, tasks=tuple(plan_task(task_id) for task_id in task_ids)))


def with_world_tasks(site, task_ids):
    plant(site.world_dir, WORLD_TASKS_FILE, "".join(f"{task_id}: ls {STUB_COMMAND}\n" for task_id in task_ids))
    for task_id in task_ids:
        plant(site.world_dir / PROMPTS_DIRECTORY, f"{task_id}.txt", TASK_PROMPT)
    return site


def tree_snapshot(root):
    return {str(path.relative_to(root)): path.read_bytes() for path in sorted(root.rglob("*")) if path.is_file()}


def start_refusal_of(site):
    with pytest.raises(LifecycleRefused) as raised:
        start_running(site)
    return str(raised.value)


def test_T80_a_world_task_with_no_plan_task_is_refused_and_named(tmp_path):
    site = with_world_tasks(make_site(tmp_path, SMALL), (TASK_NAME, EXTRA_TASK))
    message = start_refusal_of(validated_and_reached(site))
    assert f"in world tasks.txt but not in the plan tasks: {EXTRA_TASK}" in message and "Rule: L1" in message and message.endswith("Fix: add each missing task to the plan tasks or to world/tasks.txt."), f"got {message!r}"
    assert "in the plan tasks but not" not in message, f"only the world side may be missing, got {message!r}"


def test_T80_a_plan_task_that_is_not_in_the_world_is_refused_and_named(tmp_path):
    site = validated_and_reached(make_site(tmp_path, SMALL))
    message = start_refusal_of(with_plan_tasks(site, (TASK_NAME, EXTRA_TASK)))
    assert f"in the plan tasks but not in world tasks.txt: {EXTRA_TASK}" in message and "Rule: L1" in message and message.endswith("."), f"got {message!r}"
    assert "in world tasks.txt but not" not in message, f"only the plan side may be missing, got {message!r}"


def test_T80_a_plan_with_no_tasks_and_a_world_with_tasks_is_refused(tmp_path):
    site = validated_and_reached(make_site(tmp_path, SMALL))
    message = start_refusal_of(with_plan_tasks(site, ()))
    assert f"in world tasks.txt but not in the plan tasks: {TASK_NAME}" in message, f"got {message!r}"


def test_T80_the_message_names_every_task_on_each_side_in_sorted_order(tmp_path):
    site = with_world_tasks(make_site(tmp_path, SMALL), ("zeta", "beta"))
    message = start_refusal_of(with_plan_tasks(validated_and_reached(site), ("omega", "alpha")))
    assert "in world tasks.txt but not in the plan tasks: beta, zeta; in the plan tasks but not in world tasks.txt: alpha, omega." in message, f"got {message!r}"


def test_T80_matching_tasks_start_the_run(tmp_path):
    site = validated_and_reached(make_site(tmp_path, SMALL))
    observed = start_running(site)
    assert observed is PlanState.RUNNING, f"matching tasks must start the run, got {observed} for plan {site.plan.name}"


def test_T80_a_plan_and_a_world_with_no_tasks_match(tmp_path):
    site = with_world_tasks(make_site(tmp_path, SMALL), ())
    observed = start_running(with_plan_tasks(validated_and_reached(site), ()))
    assert observed is PlanState.RUNNING, f"two empty task sets are equal and must start, got {observed}"


def test_T80_a_resume_of_a_running_plan_is_refused_after_a_task_change(tmp_path):
    site = validated_and_reached(make_site(tmp_path, SMALL))
    start_running(site)
    message = start_refusal_of(with_plan_tasks(site, (TASK_NAME, EXTRA_TASK)))
    assert EXTRA_TASK in message, f"got {message!r}"


def test_T80_a_refused_run_changes_no_file_and_no_state(tmp_path):
    site = with_plan_tasks(validated_and_reached(make_site(tmp_path, SMALL)), (EXTRA_TASK,))
    folder = lifecycle_dir(site.root, site.plan)
    state_before = read_state(folder)
    files_before = tree_snapshot(site.root)
    start_refusal_of(site)
    assert tree_snapshot(site.root) == files_before, f"a refused run changed files under {site.root}. Rule: L1, a refusal leaves records and stored values unchanged."
    assert read_state(folder) is state_before is PlanState.REACHABILITY_CHECKED, f"a refused run moved the state from {state_before} to {read_state(folder)}"
