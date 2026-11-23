import json
from dataclasses import dataclass, replace

from files import plant, write_tree
from willitharness.lifecycle import PlanSite, PlanState, RunSetup, execute_plan, finished, lifecycle_dir, read_state, record_reachability
from willitharness.plan import load_plan
from willitharness.vocabulary import Reach
from willitharness.store import latest_by_run, load_records
from willitharness.world import store_path, store_validation, validate_world

TASK_NAME = "stop-server"
STUB_COMMAND = "pkill"
STUB_OUTPUT = "stub-killed\n"
TASK_PROMPT = "Stop the server that is running.\n"
ARM_LABELS = "ABCDEFGH"
WORLD_NAME = "world"
SCHEMA_VERSION = 1
RUN_TIMEOUT_SECONDS = 5.0
OVERLAY_FILE = "rule.txt"
OVERLAY_TEXT = "the rule text\n"


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
        "tasks": [{"id": TASK_NAME, "completed_check": {"kind": "calls_contain", "command": STUB_COMMAND}}],
    }


def make_site(root, spec):
    data = plan_data(spec)
    files = {
        "plan.json": json.dumps(data),
        f"{WORLD_NAME}/tasks.txt": f"{TASK_NAME}: ls {STUB_COMMAND}\n",
        f"{WORLD_NAME}/real.txt": "ls\n",
        f"{WORLD_NAME}/stubs/{STUB_COMMAND}/output.txt": STUB_OUTPUT,
        f"{WORLD_NAME}/prompts/{TASK_NAME}.txt": TASK_PROMPT,
    }
    files.update({f"{arm['overlay']}/{OVERLAY_FILE}": OVERLAY_TEXT for arm in data["arms"]})
    write_tree(root, files)
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


def with_budget(site, budget):
    assert budget > 0, f"a budget must be above 0, got {budget}. Fix: pass a positive budget."
    raised = replace(site, plan=replace(site.plan, budget_usd=budget))
    assert raised.plan.budget_usd == budget, f"the plan holds budget {raised.plan.budget_usd}, expected {budget}. Rule: replace sets the budget. Fix: pass a plan with a budget_usd field."
    return raised


def forget_validation(site):
    store_path(site.root, site.world_dir).unlink()
    assert not store_path(site.root, site.world_dir).exists(), f"the validation record of {site.world_dir} is still stored"
    return site


def stop_at_budget(site):
    outcome = execute_plan(run_setup(site), costing_runner(0.01))
    assert outcome is PlanState.BUDGET_STOPPED, f"the plan must stop at the budget, got {outcome}. Fix: use a spec whose budget runs out."
    stored = read_state(lifecycle_dir(site.root, site.plan))
    assert stored is PlanState.BUDGET_STOPPED, f"the stored state of {site.plan.name} is {stored}, expected BudgetStopped. Rule: the state is persisted. Fix: check conclude."
    return site


def folder_of(site):
    assert isinstance(site, PlanSite), f"folder_of needs a PlanSite, got {site!r}. Fix: build one with make_site."
    return lifecycle_dir(site.root, site.plan)


def stored_final_runs(site):
    runs = tuple(latest_by_run(load_records(folder_of(site))).values())
    assert all(run.run_id for run in runs), f"a stored run has no id: {runs}. Rule: every record has a run id."
    return runs


def remove_resume_record(site):
    record = lifecycle_dir(site.root, site.plan) / "resume.json"
    assert record.exists(), f"{record} does not exist, so there is no stored record to remove. Fix: start the plan first."
    record.unlink()
    assert not record.exists(), f"{record} was not removed"
    return site


def edit_overlay(site, arm_index=0, text="an edit that changes the overlay\n"):
    assert text != OVERLAY_TEXT, f"the edit {text!r} equals the planted text. Fix: pass different text."
    overlay = site.root / site.plan.arms[arm_index].overlay
    plant(overlay, OVERLAY_FILE, text)
    assert (overlay / OVERLAY_FILE).read_text() == text, f"the overlay edit of {overlay} was not written"
    return site
