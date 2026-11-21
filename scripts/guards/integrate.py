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
ORIGIN_TRUNK = f"origin/{TRUNK}"
LAND_LOCAL_FLAG = "--land-local"
SYNC_FLAG = "--sync"
REMOTE = "origin"
VERIFIED_NOTICE = "integrate: verified. Local main is unchanged. To publish: git push origin {branch}, then open a pull request from it (see scripts/guards/pr_text.py)"
LAND_LOCAL_NOTICE = "integrate: main is local only. Publishing needs a branch: recreate it with git branch <name> <sha>"
DIVERGED_FIX = f"git fetch {REMOTE}, then git switch {TRUNK}, then git merge --ff-only {ORIGIN_TRUNK}. If that fails, local {TRUNK} holds unpublished commits: list them with git log {ORIGIN_TRUNK}..{TRUNK} --oneline before any reset"


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


def commits_behind_origin(repo):
    assert repo, f"commits_behind_origin got repo {repo!r}. Fix: pass the repository directory."
    assert ORIGIN_TRUNK.endswith(TRUNK), f"ORIGIN_TRUNK {ORIGIN_TRUNK!r} does not name {TRUNK}. Fix: build it from TRUNK."
    if run_checked(repo, ["git", "rev-parse", "--verify", "--quiet", ORIGIN_TRUNK]).returncode != 0:
        return 0
    return int(git_lines(repo, ["rev-list", "--count", f"{TRUNK}..{ORIGIN_TRUNK}"])[0])


def require_fresh_trunk(repo):
    assert repo, f"require_fresh_trunk got repo {repo!r}. Fix: pass the repository directory."
    assert TRUNK, "the trunk name is empty. Rule: the trunk is a named branch. Fix: set TRUNK."
    behind = commits_behind_origin(repo)
    if behind:
        raise Refused(f"integrate: local {TRUNK} lacks {behind} commit(s) of {ORIGIN_TRUNK}. Rule: GitHub squash-merges, so a stale {TRUNK} is a stale base. Fix: {DIVERGED_FIX}, then run integrate again.")


def rebase_on_trunk(repo, branch, base):
    assert branch != TRUNK, f"rebase_on_trunk got {branch!r}. Rule: only a short-lived branch is rebased."
    assert repo and base, f"rebase_on_trunk got repo {repo!r} and base {base!r}. Fix: pass the repository directory and a base."
    result = run_checked(repo, ["git", "rebase", base])
    if result.returncode != 0:
        run_checked(repo, ["git", "rebase", "--abort"])
        raise Refused(f"integrate: rebasing {branch} on {base} failed: {result.stderr.strip()}. Rule: the branch must sit on top of {base}. Fix: resolve the conflict by hand, then run integrate again.")


def require_origin_trunk(repo):
    assert repo, f"require_origin_trunk got repo {repo!r}. Fix: pass the repository directory."
    assert ORIGIN_TRUNK.endswith(TRUNK), f"ORIGIN_TRUNK {ORIGIN_TRUNK!r} does not name {TRUNK}. Fix: build it from TRUNK."
    if run_checked(repo, ["git", "rev-parse", "--verify", "--quiet", ORIGIN_TRUNK]).returncode != 0:
        raise Refused(f"integrate: {ORIGIN_TRUNK} does not exist here. Rule: a branch is verified against the remote trunk. Fix: git fetch {REMOTE}.")


def require_based_on_origin(repo, branch):
    assert branch != TRUNK, f"require_based_on_origin got {branch!r}. Rule: only a short-lived branch is verified."
    assert repo, f"require_based_on_origin got repo {repo!r}. Fix: pass the repository directory."
    require_origin_trunk(repo)
    if run_checked(repo, ["git", "merge-base", "--is-ancestor", ORIGIN_TRUNK, branch]).returncode != 0:
        raise Refused(f"integrate: {ORIGIN_TRUNK} is not an ancestor of {branch}. Rule: the pull request branch sits on top of {ORIGIN_TRUNK}. Fix: git fetch {REMOTE}, then run integrate again.")


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


def verify(repo, command):
    assert repo, f"verify got repo {repo!r}. Fix: pass the repository directory."
    assert command, f"verify got command {command!r}. Rule: no branch is verified without checks. Fix: pass the check command."
    branch = require_clean_branch(repo)
    require_origin_trunk(repo)
    rebase_on_trunk(repo, branch, ORIGIN_TRUNK)
    require_based_on_origin(repo, branch)
    run_branch_checks(repo, command)
    assert current_branch(repo) == branch, f"verify left HEAD off {branch!r}"
    return branch


def land_local(repo, command):
    assert repo, f"land_local got repo {repo!r}. Fix: pass the repository directory."
    assert command, f"land_local got command {command!r}. Rule: no branch is integrated without checks. Fix: pass the check command."
    branch = require_clean_branch(repo)
    require_fresh_trunk(repo)
    rebase_on_trunk(repo, branch, TRUNK)
    run_branch_checks(repo, command)
    fast_forward_trunk(repo, branch)
    assert branch != TRUNK, f"land_local finished on {branch!r}"
    return branch


def sync(repo):
    assert repo, f"sync got repo {repo!r}. Fix: pass the repository directory."
    assert ORIGIN_TRUNK.endswith(TRUNK), f"ORIGIN_TRUNK {ORIGIN_TRUNK!r} does not name {TRUNK}. Fix: build it from TRUNK."
    fetched = run_checked(repo, ["git", "fetch", REMOTE])
    if fetched.returncode != 0:
        raise Refused(f"integrate: fetching {REMOTE} failed: {fetched.stderr.strip()}. Rule: sync starts from the remote state. Fix: check the network and the remote.")
    switched = run_checked(repo, ["git", "switch", TRUNK])
    if switched.returncode != 0:
        raise Refused(f"integrate: switching to {TRUNK} failed: {switched.stderr.strip()}. Fix: commit or stash the work first.")
    merged = run_checked(repo, ["git", "merge", "--ff-only", ORIGIN_TRUNK])
    if merged.returncode != 0:
        raise Refused(f"integrate: {TRUNK} cannot fast-forward to {ORIGIN_TRUNK}: {merged.stderr.strip()}. Rule: sync never discards commits. Fix: {DIVERGED_FIX}.")
    merged_branches = [name for name in git_lines(repo, ["branch", "--format=%(refname:short)", "--merged", TRUNK]) if name != TRUNK]
    for name in merged_branches:
        run_checked(repo, ["git", "branch", "-d", name])
    return merged_branches


def main(arguments, repo, environment):
    assert isinstance(arguments, list), f"main needs a list of arguments, got {arguments!r}. Fix: pass sys.argv[1:]."
    assert hasattr(environment, "get"), f"environment must map names to values, got {environment!r}"
    command = environment.get(CHECK_VARIABLE, DEFAULT_CHECK_COMMAND)
    try:
        if SYNC_FLAG in arguments:
            deleted = sync(repo)
            print(f"integrate: {TRUNK} is level with {ORIGIN_TRUNK}; deleted merged branches: {', '.join(deleted) or 'none'}")
        elif LAND_LOCAL_FLAG in arguments:
            branch = land_local(repo, command)
            print(f"integrate: {branch} is on {TRUNK} and the branch is deleted")
            print(LAND_LOCAL_NOTICE)
        else:
            branch = verify(repo, command)
            print(VERIFIED_NOTICE.format(branch=branch))
    except Refused as refusal:
        print(str(refusal), file=sys.stderr)
        return EXIT_REFUSED
    return EXIT_INTEGRATED


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:], os.getcwd(), os.environ))
