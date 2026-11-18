import pytest

from files import plant
from git_repo import TEST_EMAIL, commit_files, git_output, init_repo, run_git
from guards import integrate

PASSING = {integrate.CHECK_VARIABLE: "true"}
FAILING = {integrate.CHECK_VARIABLE: "false"}


@pytest.fixture
def repo(tmp_path):
    prepared = init_repo(tmp_path, TEST_EMAIL)
    commit_files(prepared, "chore: start", ["README.md"])
    run_git(prepared, ["switch", "-c", "feat/change"])
    commit_files(prepared, "feat: change", ["change.txt"])
    return prepared


def main_subjects(repo):
    return git_output(repo, ["log", "--format=%s", "main"]).splitlines()


def test_a_green_branch_is_fast_forwarded_onto_main_and_deleted(repo, capsys):
    code = integrate.main([], str(repo), PASSING)
    output = capsys.readouterr().out
    assert code == integrate.EXIT_INTEGRATED, f"expected exit 0, got {code}"
    assert main_subjects(repo)[0] == "feat: change", f"main must hold the branch commit, got {main_subjects(repo)}"
    assert git_output(repo, ["branch", "--list", "feat/change"]) == "", f"the branch must be deleted; output {output!r}"


def test_failing_checks_leave_main_and_the_branch_untouched(repo, capsys):
    code = integrate.main([], str(repo), FAILING)
    message = capsys.readouterr().err
    assert code == integrate.EXIT_REFUSED, f"expected exit 1, got {code}"
    assert main_subjects(repo) == ["chore: start"], f"main must not move, got {main_subjects(repo)}"
    assert "the checks failed" in message and "Fix:" in message, f"unexpected message {message!r}"
    assert git_output(repo, ["branch", "--list", "feat/change"]) != "", f"the branch must stay after a failed check in {repo}"


def test_a_dirty_working_tree_is_refused(repo, capsys):
    plant(repo, "loose.txt", "not committed")
    code = integrate.main([], str(repo), PASSING)
    message = capsys.readouterr().err
    assert code == integrate.EXIT_REFUSED, f"expected exit 1, got {code}"
    assert "uncommitted" in message, f"unexpected message {message!r}"


def test_integrating_from_main_is_refused(repo, capsys):
    run_git(repo, ["switch", "main"])
    code = integrate.main([], str(repo), PASSING)
    message = capsys.readouterr().err
    assert code == integrate.EXIT_REFUSED, f"expected exit 1, got {code}"
    assert "you are on main" in message, f"unexpected message {message!r}"


def test_a_branch_behind_main_is_rebased_and_the_history_stays_linear(repo):
    run_git(repo, ["switch", "main"])
    commit_files(repo, "chore: main moved", ["moved.txt"])
    run_git(repo, ["switch", "feat/change"])
    code = integrate.main([], str(repo), PASSING)
    assert code == integrate.EXIT_INTEGRATED, f"expected exit 0, got {code}"
    assert main_subjects(repo) == ["feat: change", "chore: main moved", "chore: start"], f"got {main_subjects(repo)}"
    assert git_output(repo, ["rev-list", "--merges", "main"]) == "", "the trunk must hold no merge commit"


def test_a_rebase_conflict_is_refused_and_the_branch_is_left_intact(repo, capsys):
    run_git(repo, ["switch", "main"])
    commit_files(repo, "chore: main edits the same file", ["change.txt"])
    run_git(repo, ["switch", "feat/change"])
    before = git_output(repo, ["rev-parse", "feat/change"])
    code = integrate.main([], str(repo), PASSING)
    message = capsys.readouterr().err
    assert code == integrate.EXIT_REFUSED, f"expected exit 1, got {code}"
    assert "rebasing feat/change on main failed" in message, f"unexpected message {message!r}"
    assert git_output(repo, ["rev-parse", "feat/change"]) == before, "the branch must be unchanged after the aborted rebase"
