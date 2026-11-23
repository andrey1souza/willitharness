import argparse
import json
import sys
from pathlib import Path

from willitharness import claude_agent, fakeagent
from willitharness.claude_agent import AgentUnavailable
from willitharness.load_report import HOOK_TIMEOUT_SECONDS, LoadRefused, build_load_report, project_folder
from willitharness.decide_plan import DecideRefused, decision_line, rule_decisions
from willitharness.analyzed import finish_analysis
from willitharness.agent_line import read_agent_line
from willitharness.analysis import AnalysisInput, analyze_plan, has_verdict, messages_of, report_lines
from willitharness.fakeagent import Behavior, Location
from willitharness.world_facts import world_facts
from willitharness.lifecycle import (
    LifecycleRefused,
    PlanSite,
    PRE_RUN_ORDER,
    PlanState,
    RunSetup,
    abort_plan,
    analyze_gate,
    read_reach,
    read_state,
    record_reachability,
    resume_if_stopped,
    finished,
    lifecycle_dir,
    execute_plan,
)
from willitharness.outcomes import AnalysisError
from willitharness.plan import PlanError, read_plan
from willitharness.paths import PathOutsideRoot, inside
from willitharness.three_arm_report import is_three_arm, three_arm_decision_lines
from willitharness.plan_builder import BuildOptions, BuildRefused, build_component_plan, hook_component, read_detector_file, read_task_file, skill_component
from willitharness.report import ReportRefused, build_report, report_location
from willitharness.real_runner import claude_runner, skill_names, system_prompt_file
from willitharness.probe import DEFAULT_LABEL, PROMPT_TEMPLATE, ProbeRefused, check_requested_runs, parse_run, probe
from willitharness.store import latest_by_run, load_records, spent
from willitharness.world import WorldError, store_validation, task_commands, validate_world

EXIT_OK = 0
EXIT_DOMAIN_FAILURE = 1
EXIT_USAGE = 2
EXIT_AGENT_MISSING = 3
EXIT_BUDGET_STOPPED = 4
USAGE = (
    "usage: willitharness plan check <plan.json> | willitharness world check <world-dir> "
    "| willitharness probe --agent fake|claude --directory D --runs N --target-token T --control-token C [--boundary B --seed S] [--model M] [--plan P --arm A] "
    "| willitharness run <plan.json> --agent fake|claude [--timeout-seconds S] [--model M] | willitharness abort <plan.json> | willitharness analyze <plan.json> | willitharness decide <plan.json> | willitharness report <plan-dir or plan.json> | willitharness load-report [project-dir] [--run-hooks] | willitharness build-plan --skill NAME or --hook EVENT --run-hook --detector FILE --task-file FILE --out DIR --budget-usd B --run-cap-usd R [--project DIR --name N --placebo]"
)
EXIT_CODES = (EXIT_OK, EXIT_DOMAIN_FAILURE, EXIT_USAGE, EXIT_AGENT_MISSING, EXIT_BUDGET_STOPPED)
FAKE_RUN_COST_USD = 0.01
DEFAULT_RUN_TIMEOUT_SECONDS = 600.0
ENDS_RESUME_WARNING = "warning: analyze ends resume; the plan is Analyzed and cannot run again"
NO_VERDICT_MESSAGE = "no verdict produced; the plan keeps its state"
NO_TASKS = "the world has no tasks. Rule: a plan runs its arms on the tasks of tasks.txt. Fix: add a task line to the world."
PLAN_ARGUMENT_COUNT = 3
RECORD_NEEDS_BOTH = "--plan and --arm go together. Rule: a result is recorded for one arm of one plan. Fix: give both, or give neither to only print the result."
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
    if arguments.skills:
        return claude_agent.run_command(arguments.directory, claude_agent.skill_probe_argv(prompt, arguments.model, arguments.run_budget_usd, arguments.skills))
    return claude_agent.run_command(arguments.directory, claude_agent.probe_argv(prompt, arguments.model, arguments.run_budget_usd, arguments.system_prompt_file))


RUNNERS = {"fake": scripted_fake_runner, "claude": claude_runner_for_cli}
FAKE_NEEDS = "the fake agent needs --seed and --boundary. Rule: the fake agent walks up from a seeded start to a boundary. Fix: pass both."


def recording_site(plan_name, arm):
    assert (plan_name is None) == (arm is None), f"plan {plan_name!r} and arm {arm!r} go together. Fix: check both options before calling."
    if plan_name is None:
        return None, EXIT_OK
    try:
        site = plan_site_from(Path.cwd(), plan_name)
    except (PlanError, WorldError, PathOutsideRoot) as error:
        print(str(error), file=sys.stderr)
        return None, EXIT_DOMAIN_FAILURE
    labels = [known.label for known in site.plan.arms]
    if arm not in labels:
        print(f"arm {arm!r} is not an arm of plan {site.plan.name}. Rule: reachability belongs to a plan arm. Fix: use one of {', '.join(labels)}.", file=sys.stderr)
        return None, EXIT_DOMAIN_FAILURE
    state = read_state(lifecycle_dir(site.root, site.plan))
    if state not in PRE_RUN_ORDER:
        print(f"plan {site.plan.name} is {state}. Rule: reachability is recorded before the first run. Fix: probe before willitharness run.", file=sys.stderr)
        return None, EXIT_DOMAIN_FAILURE
    assert site.plan.arms and arm in labels, f"recording_site returned a site where {arm!r} is not an arm of {labels}"
    return site, EXIT_OK


def arm_system_prompt_file(site, arm_label):
    assert (site is None) == (arm_label is None), f"site {site!r} and arm {arm_label!r} go together. Fix: check both options before calling."
    assert site is None or arm_label in [arm.label for arm in site.plan.arms], f"arm {arm_label!r} is not an arm of the plan. Fix: check the arm before calling."
    if site is None:
        return claude_agent.NO_SYSTEM_PROMPT_FILE
    path = system_prompt_file(site, next(arm for arm in site.plan.arms if arm.label == arm_label))
    assert isinstance(path, str), f"system_prompt_file returned {path!r}, not text. Rule: the probe passes a path or an empty value."
    return path


def arm_skill_names(site, arm_label):
    assert (site is None) == (arm_label is None), f"site {site!r} and arm {arm_label!r} go together. Fix: check both options before calling."
    assert site is None or arm_label in [arm.label for arm in site.plan.arms], f"arm {arm_label!r} is not an arm of the plan. Fix: check the arm before calling."
    if site is None:
        return ()
    names = skill_names(site, next(arm for arm in site.plan.arms if arm.label == arm_label))
    assert isinstance(names, tuple), f"skill_names returned {names!r}, not a tuple. Rule: the probe passes skill names or an empty tuple."
    return names


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
    parser.add_argument("--plan")
    parser.add_argument("--arm")
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
    if (arguments.plan is None) != (arguments.arm is None):
        print(RECORD_NEEDS_BOTH, file=sys.stderr)
        return EXIT_USAGE
    site, refused = recording_site(arguments.plan, arguments.arm)
    if refused != EXIT_OK:
        return refused
    try:
        arguments.system_prompt_file = arm_system_prompt_file(site, arguments.arm)
        arguments.skills = arm_skill_names(site, arguments.arm)
    except PlanError as error:
        print(str(error), file=sys.stderr)
        return EXIT_DOMAIN_FAILURE
    transcripts = [runners[arguments.agent](arguments, index) for index in range(arguments.runs)]
    result = probe([parse_run(lines, arguments.target_token, arguments.control_token) for lines in transcripts])
    print(f"reachability: {result.reach}")
    print(result.message)
    print(f"cost: ${sum(claude_agent.transcript_cost(lines) for lines in transcripts):.4f}")
    if site is not None:
        recorded_state = record_reachability(site, arguments.arm, result.reach)
        print(f"recorded: arm {arguments.arm} is {result.reach} in plan {site.plan.name}; plan state {recorded_state}")
    assert result.message, f"a probe result must print a message, got reach {result.reach}"
    return EXIT_OK


def fake_cell_runner(cell, rep, attempt):
    assert rep >= 1 and attempt >= 1, f"rep {rep} and attempt {attempt} start at 1. Rule: run ids count from 1."
    assert cell.arm and cell.task, f"cell {cell} lacks an arm or a task. Rule: every run belongs to a cell."
    event = {"type": "result", "subtype": "success", "is_error": False, "result": "done", "total_cost_usd": FAKE_RUN_COST_USD}
    return finished([json.dumps(event, sort_keys=True)])


RUN_RUNNERS = {"fake": fake_cell_runner}
SETUP_RUNNERS = {"claude": claude_runner}


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
    print(f"plan {state}: {len(latest_by_run(records))} runs, spent ${spent(records):.2f}")
    codes = {PlanState.COMPLETE: EXIT_OK, PlanState.BUDGET_STOPPED: EXIT_BUDGET_STOPPED}
    if state not in codes:
        print(f"plan is {state}; no further runs started. Rule: a plan ends as Complete or BudgetStopped. Fix: read the plan state, then run willitharness run again or start a new plan.", file=sys.stderr)
    return codes.get(state, EXIT_DOMAIN_FAILURE)


def run_model(arguments, setup_runners):
    assert arguments.agent, f"run_model needs the parsed run arguments, got {arguments!r}. Fix: parse them first."
    model = arguments.model if arguments.agent in setup_runners else arguments.agent
    assert model, f"run_model found no model for agent {arguments.agent!r}. Rule: T73, every run records a model name. Fix: pass --model with a name."
    return model


def run_plan_command(argv, runners, setup_runners):
    assert isinstance(argv, list), f"run_plan_command needs a list of arguments, got {argv!r}. Fix: pass the arguments after run."
    assert all(isinstance(item, str) for item in argv), f"every argument must be text, got {argv!r}"
    parser = argparse.ArgumentParser(prog="willitharness run")
    parser.add_argument("plan")
    parser.add_argument("--agent", choices=sorted([*runners, *setup_runners]), required=True)
    parser.add_argument("--timeout-seconds", type=float, default=DEFAULT_RUN_TIMEOUT_SECONDS)
    parser.add_argument("--model", default=claude_agent.DEFAULT_MODEL)
    arguments = parser.parse_args(argv)
    try:
        site = plan_site_from(Path.cwd(), arguments.plan)
        tasks = tuple(sorted(task_commands(site.world_dir)))
        if not tasks:
            raise WorldError(NO_TASKS)
        setup = RunSetup(site, tasks, arguments.timeout_seconds, run_model(arguments, setup_runners))
        runner = runners[arguments.agent] if arguments.agent in runners else setup_runners[arguments.agent](setup, arguments.model)
        resume_if_stopped(site)
        state = execute_plan(setup, runner)
    except AgentUnavailable as error:
        print(str(error), file=sys.stderr)
        return EXIT_AGENT_MISSING
    except (PathOutsideRoot, PlanError, WorldError, LifecycleRefused) as error:
        print(str(error), file=sys.stderr)
        return EXIT_DOMAIN_FAILURE
    return run_report(site, state)


def plan_command(argv, name):
    assert isinstance(argv, list), f"{name} needs a list of arguments, got {argv!r}. Fix: pass the arguments after {name}."
    assert name == "abort", f"plan_command serves abort, got {name!r}. Fix: route analyze to analyze_command."
    parser = argparse.ArgumentParser(prog=f"willitharness {name}")
    parser.add_argument("plan")
    arguments = parser.parse_args(argv)
    root = Path.cwd()
    try:
        abort_plan(root, read_plan(root, arguments.plan))
    except (PlanError, LifecycleRefused) as error:
        print(str(error), file=sys.stderr)
        return EXIT_DOMAIN_FAILURE
    print(f"plan {PlanState.ABORTED}")
    return EXIT_OK


def analyze_command(argv):
    assert isinstance(argv, list), f"analyze_command needs a list of arguments, got {argv!r}. Fix: pass the arguments after analyze."
    assert all(isinstance(item, str) for item in argv), f"every argument must be text, got {argv!r}"
    parser = argparse.ArgumentParser(prog="willitharness analyze")
    parser.add_argument("plan")
    parser.add_argument("--pooled", action="store_true")
    arguments = parser.parse_args(argv)
    root = Path.cwd()
    try:
        plan = read_plan(root, arguments.plan)
        analyze_gate(root, plan)
        folder = lifecycle_dir(root, plan)
        analysis = analyze_plan(AnalysisInput(plan, load_records(folder), read_reach(folder), arguments.pooled, world_facts(root, plan)), True)
    except (PathOutsideRoot, PlanError, LifecycleRefused, AnalysisError) as error:
        print(str(error), file=sys.stderr)
        return EXIT_DOMAIN_FAILURE
    print("\n".join([read_agent_line(root, plan), *report_lines(analysis)]))
    if not has_verdict(analysis):
        print("\n".join([*messages_of(analysis), NO_VERDICT_MESSAGE]), file=sys.stderr)
        return EXIT_DOMAIN_FAILURE
    if finish_analysis(root, plan) is PlanState.BUDGET_STOPPED:
        print(ENDS_RESUME_WARNING, file=sys.stderr)
    return EXIT_OK


def decide_plan_command(argv):
    assert isinstance(argv, list), f"decide_plan_command needs a list of arguments, got {argv!r}. Fix: pass the arguments after decide."
    assert all(isinstance(item, str) for item in argv), f"every argument must be text, got {argv!r}"
    parser = argparse.ArgumentParser(prog="willitharness decide")
    parser.add_argument("plan")
    arguments = parser.parse_args(argv)
    root = Path.cwd()
    try:
        plan = read_plan(root, arguments.plan)
        lines = list(three_arm_decision_lines(root, plan)) if is_three_arm(plan) else [decision_line(item) for item in rule_decisions(root, plan)]
    except (PathOutsideRoot, PlanError, LifecycleRefused, AnalysisError, DecideRefused) as error:
        print(str(error), file=sys.stderr)
        return EXIT_DOMAIN_FAILURE
    print("\n".join(lines))
    assert lines, "a decision run prints a line for each rule and task"
    return EXIT_OK


def report_command(argv):
    assert isinstance(argv, list), f"report_command needs a list of arguments, got {argv!r}. Fix: pass the arguments after report."
    assert all(isinstance(item, str) for item in argv), f"every argument must be text, got {argv!r}"
    parser = argparse.ArgumentParser(prog="willitharness report")
    parser.add_argument("plan")
    arguments = parser.parse_args(argv)
    try:
        root, name = report_location(Path.cwd(), arguments.plan)
        text = build_report(root, read_plan(root, name))
    except (PathOutsideRoot, PlanError, AnalysisError, DecideRefused, ReportRefused) as error:
        print(str(error), file=sys.stderr)
        return EXIT_DOMAIN_FAILURE
    print(text, end="")
    assert text, "a report is never empty"
    return EXIT_OK


def load_report_command(argv):
    assert isinstance(argv, list), f"load_report_command needs a list of arguments, got {argv!r}. Fix: pass the arguments after load-report."
    assert all(isinstance(item, str) for item in argv), f"every argument must be text, got {argv!r}"
    parser = argparse.ArgumentParser(prog="willitharness load-report")
    parser.add_argument("project_dir", nargs="?", default=".")
    parser.add_argument("--run-hooks", action="store_true")
    arguments = parser.parse_args(argv)
    timeout = HOOK_TIMEOUT_SECONDS if arguments.run_hooks else None
    try:
        lines = build_load_report(project_folder(Path.cwd(), arguments.project_dir), timeout)
    except LoadRefused as error:
        print(str(error), file=sys.stderr)
        return EXIT_DOMAIN_FAILURE
    text = "\n".join(lines)
    print(text)
    assert text, f"a load report prints at least one line, got {lines!r}"
    return EXIT_OK


def build_plan_command(argv):
    assert isinstance(argv, list), f"build_plan_command needs a list of arguments, got {argv!r}. Fix: pass the arguments after build-plan."
    assert all(isinstance(item, str) for item in argv), f"every argument must be text, got {argv!r}"
    parser = argparse.ArgumentParser(prog="willitharness build-plan")
    component = parser.add_mutually_exclusive_group(required=True)
    component.add_argument("--skill")
    component.add_argument("--hook")
    parser.add_argument("--run-hook", action="store_true")
    parser.add_argument("--detector", type=Path)
    parser.add_argument("--task-file", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--budget-usd", type=float, required=True)
    parser.add_argument("--run-cap-usd", type=float, required=True)
    parser.add_argument("--project", default=".")
    parser.add_argument("--name", default="")
    parser.add_argument("--placebo", action="store_true")
    arguments = parser.parse_args(argv)
    try:
        project = project_folder(Path.cwd(), arguments.project)
        detector = read_detector_file(arguments.detector)
        tasks = read_task_file(arguments.task_file)
        found = skill_component(project, arguments.skill) if arguments.skill else hook_component(project, arguments.hook, arguments.run_hook)
        options = BuildOptions(project, arguments.out, detector, tasks, arguments.budget_usd, arguments.run_cap_usd, arguments.placebo, arguments.name)
        path = build_component_plan(found, options)
    except (BuildRefused, LoadRefused) as error:
        print(str(error), file=sys.stderr)
        return EXIT_DOMAIN_FAILURE
    print(f"plan written: {path}")
    assert path.is_file(), f"build_component_plan reported {path}, which is not a file"
    return EXIT_OK


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
        return run_plan_command(rest, RUN_RUNNERS, SETUP_RUNNERS)
    if command == ["abort"]:
        return plan_command(rest, argv[0])
    if command == ["analyze"]:
        return analyze_command(rest)
    if command == ["decide"]:
        return decide_plan_command(rest)
    if command == ["report"]:
        return report_command(rest)
    if command == ["load-report"]:
        return load_report_command(rest)
    if command == ["build-plan"]:
        return build_plan_command(rest)
    print(f"unknown command {argv!r}. Rule: v0 has plan check, world check, probe, run, abort, analyze, decide, report, load-report and build-plan so far. Fix: {USAGE}", file=sys.stderr)
    return EXIT_USAGE


def entry_point():
    arguments = sys.argv[1:]
    assert all(isinstance(item, str) for item in arguments), f"command line arguments are text, got {arguments!r}"
    code = main(arguments)
    assert code in EXIT_CODES, f"main returned {code!r}. Rule: exit codes are 0, 1, 2, 3 or 4 so far. Fix: add the new code to the CLI."
    sys.exit(code)
