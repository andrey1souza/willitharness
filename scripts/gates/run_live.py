import argparse
import json
import sys
import tempfile
from pathlib import Path

from willitharness import claude_agent
from willitharness.cli import plan_site_from
from willitharness.lifecycle import PlanState, RunSetup, execute_plan, lifecycle_dir, record_reachability
from willitharness.real_runner import claude_runner
from willitharness.store import RunState, latest_by_run, load_records, spent
from willitharness.vocabulary import Reach
from willitharness.world import store_validation, validate_world

COST_CAP_USD = 0.10
RUN_CAP_USD = 0.05
REPS = 2
ARM_LABEL = "A"
TASK_NAME = "say-hello"
PLAN_NAME = "run-live"
PLAN_FILE = "plan.json"
WORLD_DIRECTORY = "world"
OVERLAY_DIRECTORY = "arms/A"
SCHEMA_VERSION = 1
EXIT_PASSED = 0
EXIT_FAILED = 1
NOT_PROVEN_MESSAGE = "run not proven"


def write_project(root):
    assert root.is_dir(), f"{root} is not a directory. Fix: pass the temporary project folder."
    plan = {
        "schema": SCHEMA_VERSION,
        "name": PLAN_NAME,
        "world": WORLD_DIRECTORY,
        "budget_usd": COST_CAP_USD,
        "run_cap_usd": RUN_CAP_USD,
        "reps": REPS,
        "max_retries": 0,
        "arms": [{"label": ARM_LABEL, "role": "rule", "overlay": OVERLAY_DIRECTORY}],
    }
    (root / PLAN_FILE).write_text(json.dumps(plan))
    world = root / WORLD_DIRECTORY
    world.mkdir()
    (world / "tasks.txt").write_text(f"{TASK_NAME}: echo\n")
    (world / "real.txt").write_text("echo\n")
    (root / OVERLAY_DIRECTORY).mkdir(parents=True)
    (root / OVERLAY_DIRECTORY / "AGENTS.md").write_text("# Rules\n\nReply with one short sentence.\n")
    assert (root / PLAN_FILE).is_file() and (root / OVERLAY_DIRECTORY / "AGENTS.md").is_file(), f"the project in {root} is incomplete"
    return root


def run_project(root, runner_factory, model):
    assert callable(runner_factory), f"runner_factory must build the runner, got {runner_factory!r}. Fix: pass claude_runner."
    assert model, "run_project needs a model. Fix: pass the model name."
    site = plan_site_from(root, PLAN_FILE)
    store_validation(root, site.world_dir, validate_world(site.world_dir))
    record_reachability(site, ARM_LABEL, Reach.LOADED)
    setup = RunSetup(site, (TASK_NAME,), claude_agent.RUN_TIMEOUT_SECONDS)
    state = execute_plan(setup, runner_factory(setup, model))
    records = load_records(lifecycle_dir(root, site.plan))
    usable = [run for run in latest_by_run(records).values() if run.state is RunState.RECORDED_USABLE]
    assert state in PlanState, f"execute_plan ended in {state!r}, not a plan state"
    return state, len(usable), float(spent(records))


def main(argv, runner_factory):
    assert isinstance(argv, list), f"main needs a list of arguments, got {argv!r}. Fix: pass sys.argv[1:]."
    assert callable(runner_factory), f"runner_factory must build the runner, got {runner_factory!r}. Fix: pass claude_runner."
    parser = argparse.ArgumentParser(prog="run_live")
    parser.add_argument("--model", default=claude_agent.DEFAULT_MODEL)
    arguments = parser.parse_args(argv)
    with tempfile.TemporaryDirectory(prefix="willitharness-run-live-") as directory:
        state, usable, cost = run_project(write_project(Path(directory).resolve()), runner_factory, arguments.model)
    print(f"plan: {state}; usable runs: {usable} of {REPS}")
    print(f"cost: ${cost:.4f}")
    if usable != REPS or cost > COST_CAP_USD:
        print(NOT_PROVEN_MESSAGE)
        return EXIT_FAILED
    print("GATE G3.10 PASS")
    return EXIT_PASSED


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:], claude_runner))
