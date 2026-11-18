import argparse
import sys
from pathlib import Path

from willitharness import fakeagent
from willitharness.fakeagent import Behavior, Location
from willitharness.plan import PlanError, read_plan
from willitharness.probe import ProbeRefused, check_requested_runs, parse_run, probe

EXIT_OK = 0
EXIT_DOMAIN_FAILURE = 1
EXIT_USAGE = 2
USAGE = "usage: willitharness plan check <plan.json> | willitharness probe --agent fake --directory D --boundary B --runs N --seed S --target-token T --control-token C"
PLAN_ARGUMENT_COUNT = 3


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


def probe_command(argv):
    assert isinstance(argv, list), f"probe_command needs a list of arguments, got {argv!r}. Fix: pass the arguments after probe."
    assert all(isinstance(item, str) for item in argv), f"every argument must be text, got {argv!r}"
    parser = argparse.ArgumentParser(prog="willitharness probe")
    parser.add_argument("--agent", choices=["fake"], required=True)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--boundary", type=Path, required=True)
    parser.add_argument("--runs", type=int, required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--target-token", required=True)
    parser.add_argument("--control-token", required=True)
    parser.add_argument("--label", default=fakeagent.DEFAULT_LABEL)
    parser.add_argument("--recall", type=float, default=fakeagent.CERTAIN_RECALL)
    arguments = parser.parse_args(argv)
    try:
        check_requested_runs(arguments.runs)
    except ProbeRefused as refusal:
        print(str(refusal), file=sys.stderr)
        return EXIT_USAGE
    behavior = Behavior(arguments.seed, arguments.recall)
    location = Location(arguments.directory, arguments.boundary)
    runs = [
        parse_run(fakeagent.run_agent(behavior, location, arguments.label, index), arguments.target_token, arguments.control_token)
        for index in range(arguments.runs)
    ]
    result = probe(runs)
    print(f"reachability: {result.reach}")
    print(result.message)
    assert result.message, f"a probe result must print a message, got reach {result.reach}"
    return EXIT_OK


def main(argv):
    assert isinstance(argv, list), f"main needs a list of arguments, got {argv!r}. Fix: pass sys.argv[1:]."
    assert all(isinstance(item, str) for item in argv), f"every argument must be text, got {argv!r}"
    if len(argv) == PLAN_ARGUMENT_COUNT and argv[:2] == ["plan", "check"]:
        return plan_check(Path.cwd(), argv[2])
    if argv[:1] == ["probe"]:
        return probe_command(argv[1:])
    print(f"unknown command {argv!r}. Rule: v0 has plan check and probe so far. Fix: {USAGE}", file=sys.stderr)
    return EXIT_USAGE


def entry_point():
    arguments = sys.argv[1:]
    assert all(isinstance(item, str) for item in arguments), f"command line arguments are text, got {arguments!r}"
    code = main(arguments)
    assert code in (EXIT_OK, EXIT_DOMAIN_FAILURE, EXIT_USAGE), f"main returned {code!r}. Rule: exit codes are 0, 1 or 2 so far. Fix: add the new code to the CLI."
    sys.exit(code)
