import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from guards.gitcommand import git_lines
from guards.push_window import current_moment

TRUNK = "main"
BRANCH_PATTERN = re.compile(r"^(feat|fix|chore|docs|test)/[a-z0-9][a-z0-9-]*$")
MAX_BRANCH_AGE_HOURS = 24
MAX_BRANCH_COMMITS = 10
SECONDS_PER_HOUR = 3600
EXIT_CLEAN = 0
EXIT_BREAKS_TRUNK_RULES = 1
EXIT_USAGE = 2
MODES = ("commit", "push", "push-ref")
HEAD_REFERENCE_PREFIX = "refs/heads/"


def trunk_exists(repo):
    assert repo, f"trunk_exists got repo {repo!r}. Fix: pass the repository directory."
    listed = git_lines(repo, ["branch", "--list", TRUNK])
    assert len(listed) <= 1, f"git listed {len(listed)} branches for the exact name {TRUNK!r}: {listed}"
    return bool(listed)


def current_branch(repo):
    assert repo, f"current_branch got repo {repo!r}. Fix: pass the repository directory."
    names = git_lines(repo, ["branch", "--show-current"])
    assert names, "HEAD is detached. Rule: work happens on a named branch. Fix: git switch -c feat/<name>."
    assert len(names) == 1, f"git reported {len(names)} current branches: {names}"
    return names[0]


def ahead_timestamps(repo, branch):
    assert branch != TRUNK, f"ahead_timestamps got {branch!r}. Rule: only a short-lived branch is compared with {TRUNK}."
    assert repo, f"ahead_timestamps got repo {repo!r}. Fix: pass the repository directory."
    return [int(line) for line in git_lines(repo, ["log", "--format=%ct", f"{TRUNK}..{branch}"])]


def branch_errors(repo, branch, now_seconds):
    assert branch != TRUNK, f"branch_errors got {branch!r}. Rule: the trunk is not a short-lived branch."
    assert now_seconds > 0, f"now_seconds is {now_seconds!r}. Rule: ages are measured from a real moment."
    errors = []
    if not BRANCH_PATTERN.match(branch):
        errors.append(
            f"trunk: branch {branch!r} does not match {BRANCH_PATTERN.pattern}. "
            "Rule: a short-lived branch is named type/slug. Fix: git branch -m feat/<name>."
        )
    timestamps = ahead_timestamps(repo, branch)
    if len(timestamps) > MAX_BRANCH_COMMITS:
        errors.append(
            f"trunk: branch {branch!r} is {len(timestamps)} commits ahead of {TRUNK}, above {MAX_BRANCH_COMMITS}. "
            "Rule: integrate small changes. Fix: run scripts/guards/integrate.py now, then split the rest into a new branch."
        )
    if timestamps:
        age_hours = (now_seconds - min(timestamps)) / SECONDS_PER_HOUR
        if age_hours > MAX_BRANCH_AGE_HOURS:
            errors.append(
                f"trunk: branch {branch!r} is {age_hours:.1f} hours old, above {MAX_BRANCH_AGE_HOURS}. "
                "Rule: a branch lives less than a day. Fix: run scripts/guards/integrate.py, or delete the branch."
            )
    return errors


def commit_errors(repo, now_seconds):
    assert repo, f"commit_errors got repo {repo!r}. Fix: pass the repository directory."
    assert now_seconds > 0, f"now_seconds is {now_seconds!r}. Rule: ages are measured from a real moment."
    if not trunk_exists(repo):
        return []
    branch = current_branch(repo)
    if branch == TRUNK:
        return [
            f"trunk: a commit on {TRUNK} is blocked. Rule: work lands on {TRUNK} only through scripts/guards/integrate.py, "
            "after the checks pass. Fix: git switch -c feat/<name>, then commit there."
        ]
    return branch_errors(repo, branch, now_seconds)


def merge_errors(repo):
    assert repo, f"merge_errors got repo {repo!r}. Fix: pass the repository directory."
    assert TRUNK, "the trunk name is empty. Rule: the trunk is a named branch. Fix: set TRUNK."
    if not trunk_exists(repo):
        return []
    merges = git_lines(repo, ["rev-list", "--merges", TRUNK])
    if not merges:
        return []
    return [
        f"trunk: {TRUNK} holds {len(merges)} merge commit(s). Rule: the trunk history is linear. "
        f"Fix: rebase the branch on {TRUNK} and fast-forward, as scripts/guards/integrate.py does."
    ]


def stale_errors(repo, now_seconds):
    assert repo, f"stale_errors got repo {repo!r}. Fix: pass the repository directory."
    assert now_seconds > 0, f"now_seconds is {now_seconds!r}. Rule: ages are measured from a real moment."
    if not trunk_exists(repo):
        return []
    names = git_lines(repo, ["for-each-ref", "--format=%(refname:short)", HEAD_REFERENCE_PREFIX])
    errors = []
    for branch in (name for name in names if name != TRUNK):
        errors.extend(error for error in branch_errors(repo, branch, now_seconds) if "hours old" in error or "commits ahead" in error)
    return errors


def push_ref_errors(remote_ref):
    assert remote_ref, "push_ref_errors got an empty ref. Rule: the hook passes each remote ref. Fix: pass the remote ref name."
    name = remote_ref.removeprefix(HEAD_REFERENCE_PREFIX)
    assert name, f"the ref {remote_ref!r} has no branch name. Rule: a push targets a named branch. Fix: pass refs/heads/<name>."
    if name == TRUNK or BRANCH_PATTERN.match(name):
        return []
    return [
        f"trunk: pushing {remote_ref!r} is blocked. Rule: only {TRUNK} and type/slug branches are pushed. "
        "Fix: push main, or rename the branch with git branch -m feat/<name>."
    ]


def main(arguments, repo, environment):
    assert isinstance(arguments, list), f"main needs a list of arguments, got {arguments!r}. Fix: pass sys.argv[1:]."
    assert isinstance(environment, dict) or hasattr(environment, "get"), f"environment must map names to values, got {environment!r}"
    if not arguments or arguments[0] not in MODES:
        print(f"usage: trunk.py {'|'.join(MODES)} [remote-ref]. Fix: name one mode.", file=sys.stderr)
        return EXIT_USAGE
    mode = arguments[0]
    now = int(current_moment(environment).timestamp())
    if mode == "commit":
        errors = commit_errors(repo, now)
    elif mode == "push":
        errors = merge_errors(repo) + stale_errors(repo, now)
    else:
        errors = push_ref_errors(arguments[1] if len(arguments) > 1 else "")
    for error in errors:
        print(error, file=sys.stderr)
    return EXIT_BREAKS_TRUNK_RULES if errors else EXIT_CLEAN


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:], os.getcwd(), os.environ))
