import sys
from pathlib import Path

from willitharness.plan import PlanError, read_plan

EXIT_OK = 0
EXIT_DOMAIN_FAILURE = 1
EXIT_USAGE = 2
USAGE = "usage: willitharness plan check <plan.json>"
PLAN_ARGUMENT_COUNT = 3


def plan_check(path):
    assert isinstance(path, Path), f"plan_check needs a Path, got {path!r}. Fix: wrap the argument in Path."
    try:
        plan = read_plan(path)
    except PlanError as error:
        print(str(error), file=sys.stderr)
        return EXIT_DOMAIN_FAILURE
    print(f"plan ok: {plan.name} ({len(plan.arms)} arms, {plan.reps} reps)")
    assert plan.reps >= 1, f"a loaded plan has reps {plan.reps}. Rule: the loader keeps reps at 1 or more."
    return EXIT_OK


def main(argv):
    assert isinstance(argv, list), f"main needs a list of arguments, got {argv!r}. Fix: pass sys.argv[1:]."
    assert all(isinstance(item, str) for item in argv), f"every argument must be text, got {argv!r}"
    if len(argv) == PLAN_ARGUMENT_COUNT and argv[:2] == ["plan", "check"]:
        return plan_check(Path(argv[2]))
    print(f"unknown command {argv!r}. Rule: v0 has one command so far. Fix: {USAGE}", file=sys.stderr)
    return EXIT_USAGE


def entry_point():
    arguments = sys.argv[1:]
    assert all(isinstance(item, str) for item in arguments), f"command line arguments are text, got {arguments!r}"
    code = main(arguments)
    assert code in (EXIT_OK, EXIT_DOMAIN_FAILURE, EXIT_USAGE), f"main returned {code!r}. Rule: exit codes are 0, 1 or 2 so far. Fix: add the new code to the CLI."
    sys.exit(code)
