import argparse
import json
import sys
from pathlib import Path

from willitharness import claude_agent, fakeagent
from willitharness.fakeagent import Behavior, Location
from willitharness.lifecycle import (
    LifecycleRefused,
    PlanSite,
    PlanState,
    RunSetup,
    abort_plan,
    ANALYZE_ENDS_RESUME,
    end_plan_by_analysis,
    resume_if_stopped,
    finished,
    lifecycle_dir,
    execute_plan,
)
from willitharness.plan import PlanError, read_plan
from willitharness.paths import PathOutsideRoot, inside
from willitharness.probe import DEFAULT_LABEL, PROMPT_TEMPLATE, ProbeRefused, check_requested_runs, parse_run, probe
from willitharness.store import load_records, spent
from willitharness.world import WorldError, store_validation, task_commands, validate_world

EXIT_OK = 0
EXIT_DOMAIN_FAILURE = 1
EXIT_USAGE = 2
EXIT_BUDGET_STOPPED = 4
USAGE = (
    "usage: willitharness plan check <plan.json> | willitharness world check <world-dir> "
    "| willitharness probe --agent fake|claude --directory D --runs N --target-token T --control-token C [--boundary B --seed S] [--model M] "
    "| willitharness run <plan.json> --agent fake | willitharness abort <plan.json> | willitharness analyze <plan.json>"
)
EXIT_CODES = (EXIT_OK, EXIT_DOMAIN_FAILURE, EXIT_USAGE, EXIT_BUDGET_STOPPED)
FAKE_RUN_COST_USD = 0.01
DEFAULT_RUN_TIMEOUT_SECONDS = 600.0
ANALYSIS_PENDING = "analysis is built in M4"
NO_TASKS = "the world has no tasks. Rule: a plan runs its arms on the tasks of tasks.txt. Fix: add a task line to the world."
PLAN_ARGUMENT_COUNT = 3
WORLD_ARGUMENT_COUNT = 3


def plan_check(root, name):
    assert isinstance(root, Path), f"plan_check needs a Path root, got {root!r}. Fix: pass the project directory."
    assert name, "plan_check needs a plan file name. Fix: pass the path of a plan.json."
    try:
        plan = read_plan(root, name)
    except PlanError as error:
        print(str(error), file=sys.stderr)
        return EXIT_DOMAIN_FAILURE
    print(f"plan ok: {plan.name} ({len(plan.arms)} arms, {plan.reps} reps)")
    assert plan.reps >= 1, f"a loaded plan has reps {plan.reps}. Rule: the loader keeps reps at 1 or more."
    return EXIT_OK


def world_check(root, name):
    assert isinstance(root, Path), f"world_check needs a Path root, got {root!r}. Fix: pass the project directory."
    assert name, "world_check needs a world directory. Fix: pass the path of the world directory."
    try:
        world_dir = inside(root, name)
        if not world_dir.is_dir():
            raise WorldError(f"world directory {world_dir} does not exist. Rule: a world is a directory of stubs. Fix: pass the path of a world directory.")
        validated = validate_world(world_dir)
    except (PathOutsideRoot, WorldError) as error:
        print(str(error), file=sys.stderr)
        return EXIT_DOMAIN_FAILURE
    store_validation(root, world_dir, validated)
    print(f"world: valid (hash {validated})")
    assert validated, "a valid world prints a hash"
    return EXIT_OK


def scripted_fake_runner(arguments, index):
    assert arguments.seed is not None and arguments.boundary is not None, "the fake agent needs --seed and --boundary"
    assert index >= 0, f"index is {index}. Rule: runs are counted from 0."
    behavior = Behavior(arguments.seed, arguments.recall)
    return fakeagent.run_agent(behavior, Location(arguments.directory, arguments.boundary), arguments.label, index)


def claude_runner_for_cli(arguments, index):
    assert index >= 0, f"index is {index}. Rule: runs are counted from 0."
    assert arguments.directory.is_dir(), f"{arguments.directory} is not a directory. Rule: the agent starts in the directory under test."
    prompt = PROMPT_TEMPLATE.format(label=arguments.label)
    return claude_agent.ask_claude(arguments.directory, prompt, arguments.model, arguments.run_budget_usd)


RUNNERS = {"fake": scripted_fake_runner, "claude": claude_runner_for_cli}
FAKE_NEEDS = "the fake agent needs --seed and --boundary. Fix: pass both."


def probe_command(argv, runners):
    assert isinstance(argv, list), f"probe_command needs a list of arguments, got {argv!r}. Fix: pass the arguments after probe."
    assert all(isinstance(item, str) for item in argv), f"every argument must be text, got {argv!r}"
    parser = argparse.ArgumentParser(prog="willitharness probe")
    parser.add_argument("--agent", choices=sorted(runners), required=True)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--boundary", type=Path)
    parser.add_argument("--runs", type=int, required=True)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--target-token", required=True)
    parser.add_argument("--control-token", required=True)
    parser.add_argument("--label", default=DEFAULT_LABEL)
    parser.add_argument("--recall", type=float, default=fakeagent.CERTAIN_RECALL)
    parser.add_argument("--model", default=claude_agent.DEFAULT_MODEL)
    parser.add_argument("--run-budget-usd", type=float, default=claude_agent.DEFAULT_RUN_BUDGET_USD)
    arguments = parser.parse_args(argv)
    if arguments.agent == "fake" and (arguments.seed is None or arguments.boundary is None):
        print(FAKE_NEEDS, file=sys.stderr)
        return EXIT_USAGE
    try:
        check_requested_runs(arguments.runs)
    except ProbeRefused as refusal:
        print(str(refusal), file=sys.stderr)
        return EXIT_USAGE
    transcripts = [runners[arguments.agent](arguments, index) for index in range(arguments.runs)]
    result = probe([parse_run(lines, arguments.target_token, arguments.control_token) for lines in transcripts])
    print(f"reachability: {result.reach}")
    print(result.message)
    print(f"cost: ${sum(claude_agent.transcript_cost(lines) for lines in transcripts):.4f}")
    assert result.message, f"a probe result must print a message, got reach {result.reach}"
    return EXIT_OK


def fake_cell_runner(cell, rep, attempt):
    assert rep >= 1 and attempt >= 1, f"rep {rep} and attempt {attempt} start at 1. Rule: run ids count from 1."
    assert cell.arm and cell.task, f"cell {cell} lacks an arm or a task. Rule: every run belongs to a cell."
    event = {"type": "result", "subtype": "success", "is_error": False, "result": "done", "total_cost_usd": FAKE_RUN_COST_USD}
    return finished([json.dumps(event, sort_keys=True)])


RUN_RUNNERS = {"fake": fake_cell_runner}


def plan_site_from(root, plan_name):
    assert isinstance(root, Path), f"plan_site_from needs a Path root, got {root!r}. Fix: pass the project directory."
    assert plan_name, "plan_site_from needs a plan file name. Fix: pass the path of a plan.json."
    plan = read_plan(root, plan_name)
    world_dir = inside(root, plan.world)
    if not world_dir.is_dir():
        raise WorldError(f"world directory {world_dir} does not exist. Rule: a world is a directory of stubs. Fix: create the directory the plan names in world.")
    return PlanSite(root, plan, world_dir)


def run_report(site, state):
    assert isinstance(state, PlanState), f"run_report needs a PlanState, got {state!r}. Fix: pass the state execute_plan returned."
    assert isinstance(site, PlanSite), f"run_report needs a PlanSite, got {site!r}. Fix: build one with plan_site_from."
    records = load_records(lifecycle_dir(site.root, site.plan))
    print(f"plan {state}: {len(records)} runs, spent ${spent(records):.2f}")
    codes = {PlanState.COMPLETE: EXIT_OK, PlanState.BUDGET_STOPPED: EXIT_BUDGET_STOPPED}
    if state not in codes:
        print(f"plan is {state}; no further runs started", file=sys.stderr)
    return codes.get(state, EXIT_DOMAIN_FAILURE)


def run_plan_command(argv, runners):
    assert isinstance(argv, list), f"run_plan_command needs a list of arguments, got {argv!r}. Fix: pass the arguments after run."
    assert all(isinstance(item, str) for item in argv), f"every argument must be text, got {argv!r}"
    parser = argparse.ArgumentParser(prog="willitharness run")
    parser.add_argument("plan")
    parser.add_argument("--agent", choices=sorted(runners), required=True)
    parser.add_argument("--timeout-seconds", type=float, default=DEFAULT_RUN_TIMEOUT_SECONDS)
    arguments = parser.parse_args(argv)
    try:
        site = plan_site_from(Path.cwd(), arguments.plan)
        tasks = tuple(sorted(task_commands(site.world_dir)))
        if not tasks:
            raise WorldError(NO_TASKS)
        resume_if_stopped(site)
        state = execute_plan(RunSetup(site, tasks, arguments.timeout_seconds), runners[arguments.agent])
    except (PathOutsideRoot, PlanError, WorldError, LifecycleRefused) as error:
        print(str(error), file=sys.stderr)
        return EXIT_DOMAIN_FAILURE
    return run_report(site, state)


def plan_command(argv, name):
    assert isinstance(argv, list), f"{name} needs a list of arguments, got {argv!r}. Fix: pass the arguments after {name}."
    assert name in ("abort", "analyze"), f"plan_command serves abort and analyze, got {name!r}. Fix: route only those two."
    parser = argparse.ArgumentParser(prog=f"willitharness {name}")
    parser.add_argument("plan")
    arguments = parser.parse_args(argv)
    root = Path.cwd()
    try:
        plan = read_plan(root, arguments.plan)
        if name == "abort":
            abort_plan(root, plan)
            print(f"plan {PlanState.ABORTED}")
            return EXIT_OK
        analyzed_from = end_plan_by_analysis(root, plan)
        if analyzed_from is PlanState.BUDGET_STOPPED:
            print(ANALYZE_ENDS_RESUME, file=sys.stderr)
    except (PlanError, LifecycleRefused) as error:
        print(str(error), file=sys.stderr)
        return EXIT_DOMAIN_FAILURE
    print(ANALYSIS_PENDING, file=sys.stderr)
    return EXIT_USAGE


def main(argv):
    assert isinstance(argv, list), f"main needs a list of arguments, got {argv!r}. Fix: pass sys.argv[1:]."
    assert all(isinstance(item, str) for item in argv), f"every argument must be text, got {argv!r}"
    if len(argv) == PLAN_ARGUMENT_COUNT and argv[:2] == ["plan", "check"]:
        return plan_check(Path.cwd(), argv[2])
    if len(argv) == WORLD_ARGUMENT_COUNT and argv[:2] == ["world", "check"]:
        return world_check(Path.cwd(), argv[2])
    command, rest = argv[:1], argv[1:]
    if command == ["probe"]:
        return probe_command(rest, RUNNERS)
    if command == ["run"]:
        return run_plan_command(rest, RUN_RUNNERS)
    if command in (["abort"], ["analyze"]):
        return plan_command(rest, argv[0])
    print(f"unknown command {argv!r}. Rule: v0 has plan check, world check, probe, run, abort and analyze so far. Fix: {USAGE}", file=sys.stderr)
    return EXIT_USAGE


def entry_point():
    arguments = sys.argv[1:]
    assert all(isinstance(item, str) for item in arguments), f"command line arguments are text, got {arguments!r}"
    code = main(arguments)
    assert code in EXIT_CODES, f"main returned {code!r}. Rule: exit codes are 0, 1, 2 or 4 so far. Fix: add the new code to the CLI."
    sys.exit(code)
