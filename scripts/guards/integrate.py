import os
import shlex
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from guards.gitcommand import git_lines
from guards.trunk import TRUNK, current_branch

CHECK_VARIABLE = "WILLITHARNESS_CHECK_COMMAND"
DEFAULT_CHECK_COMMAND = "make check"
EXIT_INTEGRATED = 0
EXIT_REFUSED = 1


class Refused(Exception):
    pass


def run_checked(repo, arguments):
    assert repo, f"run_checked got repo {repo!r}. Fix: pass the repository directory."
    assert arguments, f"run_checked got arguments {arguments!r}. Fix: pass a command."
    return subprocess.run(arguments, cwd=repo, capture_output=True, text=True)


def require_clean_branch(repo):
    assert repo, f"require_clean_branch got repo {repo!r}. Fix: pass the repository directory."
    assert TRUNK, "the trunk name is empty. Rule: the trunk is a named branch. Fix: set TRUNK."
    branch = current_branch(repo)
    if branch == TRUNK:
        raise Refused(f"integrate: you are on {TRUNK}. Rule: only a short-lived branch is integrated. Fix: git switch to the branch first.")
    dirty = git_lines(repo, ["status", "--porcelain"])
    if dirty:
        raise Refused(f"integrate: the working tree has {len(dirty)} uncommitted change(s). Rule: the checks run on committed work. Fix: commit or discard them.")
    return branch


def rebase_on_trunk(repo, branch):
    assert branch != TRUNK, f"rebase_on_trunk got {branch!r}. Rule: only a short-lived branch is rebased."
    assert repo, f"rebase_on_trunk got repo {repo!r}. Fix: pass the repository directory."
    result = run_checked(repo, ["git", "rebase", TRUNK])
    if result.returncode != 0:
        run_checked(repo, ["git", "rebase", "--abort"])
        raise Refused(f"integrate: rebasing {branch} on {TRUNK} failed: {result.stderr.strip()}. Rule: the branch must sit on top of {TRUNK}. Fix: resolve the conflict by hand, then run integrate again.")


def run_branch_checks(repo, command):
    assert command.strip(), f"the check command is {command!r}. Rule: no branch is integrated without checks. Fix: set {CHECK_VARIABLE} or unset it."
    assert repo, f"run_branch_checks got repo {repo!r}. Fix: pass the repository directory."
    result = run_checked(repo, shlex.split(command))
    if result.returncode != 0:
        tail = "\n".join((result.stdout + result.stderr).splitlines()[-5:])
        raise Refused(f"integrate: the checks failed with exit {result.returncode}:\n{tail}\nRule: {TRUNK} stays green. Fix: fix the failure on the branch, then run integrate again.")


def fast_forward_trunk(repo, branch):
    assert branch != TRUNK, f"fast_forward_trunk got {branch!r}. Rule: the trunk is not merged into itself."
    assert repo, f"fast_forward_trunk got repo {repo!r}. Fix: pass the repository directory."
    switched = run_checked(repo, ["git", "switch", TRUNK])
    if switched.returncode != 0:
        raise Refused(f"integrate: switching to {TRUNK} failed: {switched.stderr.strip()}. Fix: check the repository state.")
    merged = run_checked(repo, ["git", "merge", "--ff-only", branch])
    if merged.returncode != 0:
        raise Refused(f"integrate: {TRUNK} moved while the checks ran: {merged.stderr.strip()}. Fix: run integrate again.")
    run_checked(repo, ["git", "branch", "-d", branch])


def integrate(repo, command):
    assert repo, f"integrate got repo {repo!r}. Fix: pass the repository directory."
    assert command, f"integrate got command {command!r}. Rule: no branch is integrated without checks. Fix: pass the check command."
    branch = require_clean_branch(repo)
    rebase_on_trunk(repo, branch)
    run_branch_checks(repo, command)
    fast_forward_trunk(repo, branch)
    assert branch != TRUNK, f"integrate finished on {branch!r}"
    return branch


def main(arguments, repo, environment):
    assert isinstance(arguments, list), f"main needs a list of arguments, got {arguments!r}. Fix: pass sys.argv[1:]."
    assert hasattr(environment, "get"), f"environment must map names to values, got {environment!r}"
    command = environment.get(CHECK_VARIABLE, DEFAULT_CHECK_COMMAND)
    try:
        branch = integrate(repo, command)
    except Refused as refusal:
        print(str(refusal), file=sys.stderr)
        return EXIT_REFUSED
    print(f"integrate: {branch} is on {TRUNK} and the branch is deleted")
    return EXIT_INTEGRATED


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:], os.getcwd(), os.environ))
