from pathlib import Path

from willitharness.plan import Plan
from willitharness.world import task_commands


def task_mismatch(world_dir, plan):
    assert isinstance(world_dir, Path), f"task_mismatch needs the world folder as a Path, got {world_dir!r}. Fix: pass site.world_dir."
    assert isinstance(plan, Plan), f"task_mismatch needs a Plan, got {plan!r}. Fix: pass site.plan."
    world_tasks = set(task_commands(world_dir))
    plan_tasks = {task.id for task in plan.tasks}
    absent_in_plan = sorted(world_tasks - plan_tasks)
    absent_in_world = sorted(plan_tasks - world_tasks)
    if not absent_in_plan and not absent_in_world:
        return None
    sides = []
    if absent_in_plan:
        sides.append(f"in world tasks.txt but not in the plan tasks: {', '.join(absent_in_plan)}")
    if absent_in_world:
        sides.append(f"in the plan tasks but not in world tasks.txt: {', '.join(absent_in_world)}")
    message = f"the tasks of the world and of plan {plan.name} differ; {'; '.join(sides)}. Rule: L1, a run needs the same tasks in the world and in the plan, so that analyze can read every run. Fix: add each missing task to the plan tasks or to world/tasks.txt."
    assert "Rule:" in message and "Fix:" in message, f"the task mismatch message {message!r} lacks Rule: or Fix:. Rule: a refusal states a rule and a fix."
    return message
