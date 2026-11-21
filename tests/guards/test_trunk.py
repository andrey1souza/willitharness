from datetime import datetime

import pytest

from git_repo import TEST_EMAIL, commit_files, git_output, init_repo, run_git
from guards import trunk

NOW_VARIABLE = "WILLITHARNESS_NOW"
FAR_FUTURE = "2999-01-01T12:00:00"
JUST_UNDER_A_DAY = 23
JUST_OVER_A_DAY = 25
SIZE_LIMIT = 10


@pytest.fixture
def repo(tmp_path):
    prepared = init_repo(tmp_path, TEST_EMAIL)
    commit_files(prepared, "chore: start", ["README.md"])
    return prepared


def start_branch(repo, name):
    run_git(repo, ["switch", "-c", name])


def check(repo, arguments, now=None):
    environment = {NOW_VARIABLE: now} if now else {}
    return trunk.main(arguments, str(repo), environment)


def test_a_commit_on_main_is_blocked_with_the_fix(repo, capsys):
    code = check(repo, ["commit"])
    message = capsys.readouterr().err
    assert code == trunk.EXIT_BREAKS_TRUNK_RULES, f"expected exit 1, got {code}"
    assert "git switch -c feat/<name>" in message, f"the message must give the fix, got {message!r}"
    expected = "Rule: work reaches main through a pull request from a branch, not by a commit on it. Fix: git switch -c feat/<name>, then commit there. python3 scripts/guards/integrate.py --land-local moves local main for local-only experiments and is not for publishing."
    assert expected in message, f"the message must name the pull request and --land-local, got {message!r}"


def test_the_first_commit_of_a_new_repository_is_allowed(tmp_path):
    prepared = init_repo(tmp_path, TEST_EMAIL)
    code = check(prepared, ["commit"])
    assert code == trunk.EXIT_CLEAN, f"a repository with no trunk yet must allow its first commit, got {code}"


def test_a_commit_on_a_short_lived_branch_is_allowed(repo):
    start_branch(repo, "feat/small-change")
    commit_files(repo, "feat: one", ["a.txt"])
    code = check(repo, ["commit"])
    assert code == trunk.EXIT_CLEAN, f"a fresh short-lived branch must pass, got {code}"


def test_a_branch_name_without_a_type_is_rejected_with_the_fix(repo, capsys):
    start_branch(repo, "wip")
    code = check(repo, ["commit"])
    message = capsys.readouterr().err
    assert code == trunk.EXIT_BREAKS_TRUNK_RULES, f"expected exit 1, got {code}"
    assert "git branch -m feat/<name>" in message, f"the message must give the fix, got {message!r}"


def test_a_branch_with_too_many_commits_is_rejected(repo, capsys):
    start_branch(repo, "feat/big-change")
    for index in range(SIZE_LIMIT + 1):
        commit_files(repo, f"feat: step {index}", [f"file{index}.txt"])
    code = check(repo, ["commit"])
    message = capsys.readouterr().err
    assert code == trunk.EXIT_BREAKS_TRUNK_RULES, f"expected exit 1, got {code}"
    assert f"{SIZE_LIMIT + 1} commits ahead" in message, f"unexpected message {message!r}"
    expected = "Rule: publish small changes. Fix: run python3 scripts/guards/integrate.py to verify the branch, then git push origin <branch>, then open a pull request, and split the rest into a new branch."
    assert expected in message, f"the fix must name verify, push and the pull request, got {message!r}"


def test_a_branch_ten_commits_ahead_is_still_allowed(repo):
    start_branch(repo, "feat/exact-size")
    for index in range(SIZE_LIMIT):
        commit_files(repo, f"feat: step {index}", [f"file{index}.txt"])
    code = check(repo, ["commit"])
    assert code == trunk.EXIT_CLEAN, f"a branch at the size limit must pass, got {code}"


def test_a_branch_older_than_a_day_is_rejected(repo, capsys):
    start_branch(repo, "feat/old-change")
    commit_files(repo, "feat: one", ["a.txt"])
    code = check(repo, ["commit"], now=FAR_FUTURE)
    message = capsys.readouterr().err
    assert code == trunk.EXIT_BREAKS_TRUNK_RULES, f"expected exit 1, got {code}"
    assert "hours old" in message, f"unexpected message {message!r}"
    expected = "Rule: a branch lives less than a day. Fix: run python3 scripts/guards/integrate.py to verify the branch, then git push origin <branch>, then open a pull request, or delete the branch."
    assert expected in message, f"the fix must name verify, push and the pull request, got {message!r}"


def test_a_merge_commit_on_main_is_reported(repo, capsys):
    start_branch(repo, "feat/side")
    commit_files(repo, "feat: side", ["side.txt"])
    run_git(repo, ["switch", "main"])
    commit_files(repo, "chore: main moved", ["main.txt"])
    run_git(repo, ["merge", "--no-ff", "-q", "-m", "merge side", "feat/side"])
    code = check(repo, ["push"])
    message = capsys.readouterr().err
    assert code == trunk.EXIT_BREAKS_TRUNK_RULES, f"expected exit 1, got {code}"
    assert "1 merge commit" in message, f"unexpected message {message!r}"
    expected = "Fix: rebase the branch on main and fast-forward, as python3 scripts/guards/integrate.py --land-local does."
    assert expected in message, f"the fix must name --land-local, got {message!r}"


def test_a_linear_trunk_with_no_stale_branch_passes_the_push_check(repo):
    code = check(repo, ["push"])
    assert code == trunk.EXIT_CLEAN, f"a clean linear trunk must pass, got {code}"


def test_a_stale_branch_blocks_the_push_check(repo, capsys):
    start_branch(repo, "feat/forgotten")
    commit_files(repo, "feat: one", ["a.txt"])
    run_git(repo, ["switch", "main"])
    code = check(repo, ["push"], now=FAR_FUTURE)
    message = capsys.readouterr().err
    assert code == trunk.EXIT_BREAKS_TRUNK_RULES, f"expected exit 1, got {code}"
    assert "feat/forgotten" in message and "hours old" in message, f"unexpected message {message!r}"


@pytest.mark.parametrize("remote_ref", ["refs/heads/main", "refs/heads/feat/x", "refs/heads/fix/parser-crash"])
def test_main_and_typed_branches_may_be_pushed(repo, remote_ref):
    code = check(repo, ["push-ref", remote_ref])
    assert code == trunk.EXIT_CLEAN, f"{remote_ref} must be pushable, got {code}"


@pytest.mark.parametrize("remote_ref", ["refs/heads/wip", "refs/heads/feature/x", "refs/heads/Feat/x"])
def test_other_branch_names_may_not_be_pushed(repo, remote_ref, capsys):
    code = check(repo, ["push-ref", remote_ref])
    message = capsys.readouterr().err
    assert code == trunk.EXIT_BREAKS_TRUNK_RULES, f"{remote_ref} must be blocked, got {code}"
    assert "Fix:" in message, f"the message must end with a fix, got {message!r}"


def test_an_unknown_mode_exits_two_with_the_usage(repo, capsys):
    code = check(repo, ["banana"])
    message = capsys.readouterr().err
    assert code == trunk.EXIT_USAGE, f"expected exit {trunk.EXIT_USAGE}, got {code}"
    assert "usage: trunk.py" in message, f"unexpected message {message!r}"


def iso_after_first_branch_commit(repo, hours):
    first = int(git_output(repo, ["log", "--format=%ct", "main..HEAD"]).splitlines()[-1])
    return datetime.fromtimestamp(first + hours * trunk.SECONDS_PER_HOUR).isoformat()


def test_a_branch_just_under_a_day_old_is_allowed(repo):
    start_branch(repo, "feat/fresh")
    commit_files(repo, "feat: one", ["a.txt"])
    code = check(repo, ["commit"], now=iso_after_first_branch_commit(repo, JUST_UNDER_A_DAY))
    assert code == trunk.EXIT_CLEAN, f"a branch {JUST_UNDER_A_DAY} hours old must pass, got {code}"


def test_a_branch_just_over_a_day_old_is_rejected(repo, capsys):
    start_branch(repo, "feat/late")
    commit_files(repo, "feat: one", ["a.txt"])
    code = check(repo, ["commit"], now=iso_after_first_branch_commit(repo, JUST_OVER_A_DAY))
    message = capsys.readouterr().err
    assert code == trunk.EXIT_BREAKS_TRUNK_RULES, f"a branch {JUST_OVER_A_DAY} hours old must fail, got {code}"
    assert "hours old" in message, f"unexpected message {message!r}"
