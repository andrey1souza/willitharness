import pytest

from files import plant
from git_repo import TEST_EMAIL, commit_files, git_output, init_repo, run_git
from guards import integrate

PASSING = {integrate.CHECK_VARIABLE: "true"}
FAILING = {integrate.CHECK_VARIABLE: "false"}
LAND = [integrate.LAND_LOCAL_FLAG]
SYNC = [integrate.SYNC_FLAG]
BRANCH = "feat/change"


@pytest.fixture
def repo(tmp_path):
    prepared = init_repo(tmp_path, TEST_EMAIL)
    commit_files(prepared, "chore: start", ["README.md"])
    run_git(prepared, ["update-ref", "refs/remotes/origin/main", "main"])
    run_git(prepared, ["switch", "-c", BRANCH])
    commit_files(prepared, "feat: change", ["change.txt"])
    return prepared


@pytest.fixture
def remote(repo, tmp_path_factory):
    bare = tmp_path_factory.mktemp("remote")
    run_git(bare, ["init", "-q", "--bare", "-b", "main"])
    run_git(repo, ["update-ref", "-d", "refs/remotes/origin/main"])
    run_git(repo, ["remote", "add", "origin", str(bare)])
    run_git(repo, ["push", "-q", "origin", "main"])
    run_git(repo, ["fetch", "-q", "origin"])
    return bare


def main_subjects(repo):
    return git_output(repo, ["log", "--format=%s", "main"]).splitlines()


def branch_subjects(repo):
    return git_output(repo, ["log", "--format=%s", BRANCH]).splitlines()


def test_verify_keeps_the_branch_and_never_moves_main(repo, capsys):
    before = git_output(repo, ["rev-parse", "main"])
    code = integrate.main([], str(repo), PASSING)
    output = capsys.readouterr().out
    assert code == integrate.EXIT_INTEGRATED, f"expected exit 0, got {code}; output {output!r}"
    assert git_output(repo, ["rev-parse", "main"]) == before, f"verify must not move main, got {main_subjects(repo)}"
    assert git_output(repo, ["branch", "--list", BRANCH]) != "", f"verify must keep the branch; output {output!r}"
    assert git_output(repo, ["branch", "--show-current"]) == BRANCH, "verify stays on the branch"


def test_verify_ends_with_the_notice_naming_the_real_branch(repo, capsys):
    integrate.main([], str(repo), PASSING)
    last_line = capsys.readouterr().out.splitlines()[-1]
    expected = f"integrate: verified. Local main is unchanged. To publish: git push origin {BRANCH}, then open a pull request from it (see scripts/guards/pr_text.py)"
    assert last_line == expected, f"the last line must be the notice, got {last_line!r}"
    assert "<branch" not in last_line, f"the notice names the branch itself, got {last_line!r}"


def test_verify_rebases_on_origin_main_and_leaves_local_main_alone(repo):
    old = git_output(repo, ["rev-parse", "main"])
    run_git(repo, ["switch", "-c", "chore/remote", "main"])
    commit_files(repo, "chore: remote moved", ["moved.txt"])
    run_git(repo, ["update-ref", "refs/remotes/origin/main", "HEAD"])
    run_git(repo, ["switch", BRANCH])
    code = integrate.main([], str(repo), PASSING)
    assert code == integrate.EXIT_INTEGRATED, f"expected exit 0, got {code}"
    assert branch_subjects(repo) == ["feat: change", "chore: remote moved", "chore: start"], f"got {branch_subjects(repo)}"
    assert git_output(repo, ["rev-parse", "main"]) == old, "local main must not move"


def test_verify_without_origin_main_is_refused(repo, capsys):
    run_git(repo, ["update-ref", "-d", "refs/remotes/origin/main"])
    code = integrate.main([], str(repo), PASSING)
    message = capsys.readouterr().err
    assert code == integrate.EXIT_REFUSED, f"expected exit 1, got {code}"
    assert "origin/main does not exist" in message and "Fix:" in message, f"unexpected message {message!r}"


def test_a_branch_that_lacks_origin_main_is_refused(repo):
    run_git(repo, ["switch", "-c", "chore/remote", "main"])
    commit_files(repo, "chore: remote moved", ["moved.txt"])
    run_git(repo, ["update-ref", "refs/remotes/origin/main", "HEAD"])
    run_git(repo, ["switch", BRANCH])
    with pytest.raises(integrate.Refused, match="not an ancestor") as refusal:
        integrate.require_based_on_origin(str(repo), BRANCH)
    assert "Fix:" in str(refusal.value), f"the refusal says how to fix, got {refusal.value}"


def test_verify_with_failing_checks_keeps_everything(repo, capsys):
    before = git_output(repo, ["rev-parse", "main"])
    code = integrate.main([], str(repo), FAILING)
    message = capsys.readouterr().err
    assert code == integrate.EXIT_REFUSED, f"expected exit 1, got {code}"
    assert "the checks failed" in message and "Fix:" in message, f"unexpected message {message!r}"
    assert git_output(repo, ["rev-parse", "main"]) == before, "main must not move"


def test_verify_refuses_a_dirty_tree(repo, capsys):
    plant(repo, "loose.txt", "not committed")
    code = integrate.main([], str(repo), PASSING)
    message = capsys.readouterr().err
    assert code == integrate.EXIT_REFUSED, f"a dirty tree is refused, got {code}"
    assert "uncommitted" in message, f"the message names the cause, got {message!r}"


def test_verify_refuses_the_trunk(repo, capsys):
    run_git(repo, ["switch", "main"])
    code = integrate.main([], str(repo), PASSING)
    message = capsys.readouterr().err
    assert code == integrate.EXIT_REFUSED, f"the trunk is refused, got {code}"
    assert "you are on main" in message, f"the message names the cause, got {message!r}"


def test_a_verify_rebase_conflict_is_refused_and_the_branch_is_left_intact(repo, capsys):
    run_git(repo, ["switch", "-c", "chore/remote", "main"])
    commit_files(repo, "chore: remote edits the same file", ["change.txt"])
    run_git(repo, ["update-ref", "refs/remotes/origin/main", "HEAD"])
    run_git(repo, ["switch", BRANCH])
    before = git_output(repo, ["rev-parse", BRANCH])
    code = integrate.main([], str(repo), PASSING)
    message = capsys.readouterr().err
    assert code == integrate.EXIT_REFUSED, f"expected exit 1, got {code}"
    assert "rebasing feat/change on origin/main failed" in message, f"unexpected message {message!r}"
    assert git_output(repo, ["rev-parse", BRANCH]) == before, "the branch must be unchanged after the aborted rebase"


def test_land_local_fast_forwards_main_and_deletes_the_branch(repo, capsys):
    code = integrate.main(LAND, str(repo), PASSING)
    output = capsys.readouterr().out
    assert code == integrate.EXIT_INTEGRATED, f"expected exit 0, got {code}"
    assert main_subjects(repo)[0] == "feat: change", f"main must hold the branch commit, got {main_subjects(repo)}"
    assert git_output(repo, ["branch", "--list", BRANCH]) == "", f"the branch must be deleted; output {output!r}"


def test_land_local_ends_with_the_local_only_notice(repo, capsys):
    integrate.main(LAND, str(repo), PASSING)
    last_line = capsys.readouterr().out.splitlines()[-1]
    expected = "integrate: main is local only. Publishing needs a branch: recreate it with git branch <name> <sha>"
    assert last_line == expected, f"the last line must be the notice, got {last_line!r}"


def test_land_local_failing_checks_leave_main_and_the_branch_untouched(repo, capsys):
    code = integrate.main(LAND, str(repo), FAILING)
    message = capsys.readouterr().err
    assert code == integrate.EXIT_REFUSED, f"expected exit 1, got {code}"
    assert main_subjects(repo) == ["chore: start"], f"main must not move, got {main_subjects(repo)}"
    assert git_output(repo, ["branch", "--list", BRANCH]) != "", f"the branch must stay after a failed check in {repo}; message {message!r}"


def test_land_local_from_main_is_refused(repo, capsys):
    run_git(repo, ["switch", "main"])
    code = integrate.main(LAND, str(repo), PASSING)
    message = capsys.readouterr().err
    assert code == integrate.EXIT_REFUSED, f"expected exit 1, got {code}"
    assert "you are on main" in message, f"unexpected message {message!r}"


def test_land_local_rebases_on_main_and_keeps_the_history_linear(repo):
    run_git(repo, ["switch", "main"])
    commit_files(repo, "chore: main moved", ["moved.txt"])
    run_git(repo, ["update-ref", "refs/remotes/origin/main", "main"])
    run_git(repo, ["switch", BRANCH])
    code = integrate.main(LAND, str(repo), PASSING)
    assert code == integrate.EXIT_INTEGRATED, f"expected exit 0, got {code}"
    assert main_subjects(repo) == ["feat: change", "chore: main moved", "chore: start"], f"got {main_subjects(repo)}"
    assert git_output(repo, ["rev-list", "--merges", "main"]) == "", "the trunk must hold no merge commit"


def test_land_local_with_a_dirty_tree_is_refused(repo, capsys):
    plant(repo, "loose.txt", "not committed")
    code = integrate.main(LAND, str(repo), PASSING)
    message = capsys.readouterr().err
    assert code == integrate.EXIT_REFUSED, f"expected exit 1, got {code}"
    assert "uncommitted" in message, f"the message names the cause, got {message!r}"


def test_land_local_rebase_conflict_is_refused_and_the_branch_is_left_intact(repo, capsys):
    run_git(repo, ["switch", "main"])
    commit_files(repo, "chore: main edits the same file", ["change.txt"])
    run_git(repo, ["update-ref", "refs/remotes/origin/main", "main"])
    run_git(repo, ["switch", BRANCH])
    before = git_output(repo, ["rev-parse", BRANCH])
    code = integrate.main(LAND, str(repo), PASSING)
    message = capsys.readouterr().err
    assert code == integrate.EXIT_REFUSED, f"expected exit 1, got {code}"
    assert "rebasing feat/change on main failed" in message, f"unexpected message {message!r}"
    assert git_output(repo, ["rev-parse", BRANCH]) == before, "the branch must be unchanged after the aborted rebase"


def test_land_local_with_main_behind_origin_is_refused_with_a_fix(repo, capsys):
    run_git(repo, ["update-ref", "refs/remotes/origin/main", "HEAD"])
    code = integrate.main(LAND, str(repo), PASSING)
    message = capsys.readouterr().err
    assert code == integrate.EXIT_REFUSED, f"expected exit 1, got {code}"
    assert "lacks 1 commit(s) of origin/main" in message and "Rule:" in message, f"unexpected message {message!r}"
    assert "git merge --ff-only origin/main" in message and "git log origin/main..main --oneline" in message, f"the fix names the safe steps, got {message!r}"
    assert "reset --hard" not in message, f"the fix never suggests a blind reset, got {message!r}"
    assert main_subjects(repo) == ["chore: start"], f"main must not move, got {main_subjects(repo)}"


def test_land_local_with_main_level_with_origin_lands(repo):
    code = integrate.main(LAND, str(repo), PASSING)
    assert code == integrate.EXIT_INTEGRATED, f"expected exit 0, got {code}"
    assert main_subjects(repo)[0] == "feat: change", f"main must hold the branch commit, got {main_subjects(repo)}"


def test_sync_fast_forwards_main_and_deletes_merged_branches_only(repo, remote, capsys):
    run_git(repo, ["branch", "feat/unmerged", "main"])
    run_git(repo, ["switch", "feat/unmerged"])
    commit_files(repo, "feat: other work", ["other.txt"])
    run_git(repo, ["push", "-q", "origin", f"{BRANCH}:main"])
    run_git(repo, ["update-ref", "refs/remotes/origin/main", "main"])
    code = integrate.main(SYNC, str(repo), PASSING)
    output = capsys.readouterr().out
    assert code == integrate.EXIT_INTEGRATED, f"expected exit 0, got {code}; output {output!r}"
    assert main_subjects(repo)[0] == "feat: change", f"main must reach origin/main, got {main_subjects(repo)}"
    assert git_output(repo, ["branch", "--list", BRANCH]) == "", f"the merged branch is deleted; output {output!r}"
    assert git_output(repo, ["branch", "--list", "feat/unmerged"]) != "", f"an unmerged branch is never deleted in {repo}"


def test_sync_refuses_a_diverged_main_without_resetting_it(repo, remote, capsys):
    run_git(repo, ["push", "-q", "origin", f"{BRANCH}:main"])
    run_git(repo, ["switch", "main"])
    run_git(repo, ["update-ref", "refs/remotes/origin/main", "main"])
    commit_files(repo, "chore: unpublished", ["local.txt"])
    before = git_output(repo, ["rev-parse", "main"])
    code = integrate.main(SYNC, str(repo), PASSING)
    message = capsys.readouterr().err
    assert code == integrate.EXIT_REFUSED, f"expected exit 1, got {code}"
    assert "git log origin/main..main --oneline" in message and "Rule:" in message, f"unexpected message {message!r}"
    assert "reset --hard" not in message, f"the fix never suggests a blind reset, got {message!r}"
    assert git_output(repo, ["rev-parse", "main"]) == before, "main must keep its unpublished commit"


def test_sync_without_a_remote_is_refused(repo, capsys):
    code = integrate.main(SYNC, str(repo), PASSING)
    message = capsys.readouterr().err
    assert code == integrate.EXIT_REFUSED, f"expected exit 1, got {code}"
    assert "fetching origin failed" in message and "Fix:" in message, f"unexpected message {message!r}"
