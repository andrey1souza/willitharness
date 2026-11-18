import json
from dataclasses import dataclass

from files import plant, write_tree
from willitharness.lifecycle import PlanSite, RunSetup, finished, record_reachability
from willitharness.plan import load_plan
from willitharness.vocabulary import Reach
from willitharness.world import store_validation, validate_world

TASK_NAME = "stop-server"
ARM_LABELS = "ABCDEFGH"
WORLD_NAME = "world"
SCHEMA_VERSION = 1
RUN_TIMEOUT_SECONDS = 5.0


@dataclass(frozen=True)
class SiteSpec:
    arm_count: int
    budget_usd: float
    run_cap_usd: float
    reps: int
    max_retries: int


def plan_data(spec):
    assert 1 <= spec.arm_count <= len(ARM_LABELS), f"arm_count {spec.arm_count} is out of range. Fix: ask for 1 to {len(ARM_LABELS)} arms."
    assert spec.reps >= 1 and spec.max_retries >= 0, f"reps {spec.reps} and max_retries {spec.max_retries} are out of range. Fix: use reps 1 or more."
    arms = [{"label": label, "role": "rule", "overlay": f"{label}.md"} for label in ARM_LABELS[:spec.arm_count]]
    return {
        "schema": SCHEMA_VERSION,
        "name": "demo",
        "world": WORLD_NAME,
        "budget_usd": spec.budget_usd,
        "run_cap_usd": spec.run_cap_usd,
        "reps": spec.reps,
        "max_retries": spec.max_retries,
        "arms": arms,
    }


def make_site(root, spec):
    data = plan_data(spec)
    write_tree(root, {"plan.json": json.dumps(data), f"{WORLD_NAME}/tasks.txt": f"{TASK_NAME}: ls\n", f"{WORLD_NAME}/real.txt": "ls\n"})
    site = PlanSite(root, load_plan(data), root / WORLD_NAME)
    assert site.world_dir.is_dir(), f"{site.world_dir} was not created. Fix: write the world files."
    assert len(site.plan.arms) == spec.arm_count, f"the plan holds {len(site.plan.arms)} arms, expected {spec.arm_count}. Rule: the spec names the arms. Fix: correct plan_data."
    return site


def validate_site(site):
    validated = validate_world(site.world_dir)
    store_validation(site.root, site.world_dir, validated)
    assert validated, "the world produced no hash. Fix: plant world files."
    return validated


def reach_every_arm(site, reach):
    state = None
    for arm in site.plan.arms:
        state = record_reachability(site, arm.label, reach)
    assert state is not None, "the plan has no arms. Rule: a plan needs arms."
    return state


def ready_site(root, spec):
    site = make_site(root, spec)
    validate_site(site)
    reach_every_arm(site, Reach.LOADED)
    assert site.world_dir.is_dir(), f"{site.world_dir} vanished while the site was prepared"
    return site


def edit_world(site):
    plant(site.world_dir, "note.txt", "an edit that changes the world hash")
    assert (site.world_dir / "note.txt").is_file(), "the world edit was not written"
    return site


def run_setup(site):
    assert site.world_dir.is_dir(), f"{site.world_dir} is not a directory. Fix: build the site with make_site."
    setup = RunSetup(site, (TASK_NAME,), RUN_TIMEOUT_SECONDS)
    assert setup.tasks == (TASK_NAME,), f"unexpected tasks {setup.tasks}"
    return setup


def success_transcript(cost_usd):
    assert cost_usd >= 0, f"a cost cannot be negative, got {cost_usd}. Fix: pass 0 or more."
    event = {"type": "result", "subtype": "success", "is_error": False, "result": "done", "total_cost_usd": cost_usd}
    lines = [json.dumps(event, sort_keys=True)]
    assert len(lines) == 1, f"expected one transcript line, got {lines}"
    return finished(lines)


def costing_runner(cost_usd):
    assert cost_usd >= 0, f"a cost cannot be negative, got {cost_usd}. Fix: pass 0 or more."
    result = success_transcript(cost_usd)

    def runner(cell, rep, attempt):
        assert cell.arm and rep >= 1 and attempt >= 1, f"runner got {cell}, {rep}, {attempt} for cost {cost_usd}. Rule: runs count from 1. Fix: claim jobs through claim_next_job."
        return result

    assert callable(runner), f"costing_runner returned {runner!r} for cost {cost_usd}. Fix: return the runner function."
    return runner
