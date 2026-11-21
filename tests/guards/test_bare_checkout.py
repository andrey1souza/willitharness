from pathlib import Path

from git_repo import TEST_EMAIL, commit_files, init_repo, run_git
from guards import bare_checkout


def checkout(tmp_path, name="co"):
    directory = tmp_path / name
    directory.mkdir()
    init_repo(directory, TEST_EMAIL)
    commit_files(directory, "feat: one", ["one.txt"])
    return directory


def test_a_checkout_marked_bare_is_reported_with_the_value_the_rule_and_the_fix(tmp_path, capsys):
    repo = checkout(tmp_path)
    run_git(repo, ["config", "core.bare", "true"])
    code = bare_checkout.main(str(repo))
    message = capsys.readouterr().err
    assert code == bare_checkout.EXIT_BARE_CHECKOUT, "a .git directory with core.bare true must fail, got code %r" % (code,)
    assert "core.bare is true" in message and "Rule:" in message, "the message needs the value and the rule, got %r" % (message,)
    assert "Fix: run git config core.bare false in %s." % repo.resolve() in message, "the message needs the exact fix naming the checkout, got %r" % (message,)


def test_a_checkout_that_is_not_marked_bare_passes(tmp_path):
    repo = checkout(tmp_path)
    code = bare_checkout.main(str(repo))
    assert code == bare_checkout.EXIT_CLEAN, "core.bare false must pass, got code %r" % (code,)


def test_a_real_bare_repository_passes(tmp_path):
    bare = tmp_path / "remote.git"
    bare.mkdir()
    run_git(bare, ["init", "-q", "--bare"])
    code = bare_checkout.main(str(bare))
    assert code == bare_checkout.EXIT_CLEAN, "a bare repository has no .git directory and must pass, got code %r" % (code,)


def test_a_linked_worktree_passes_while_the_flag_is_false_and_fails_when_the_shared_flag_is_true(tmp_path, capsys):
    repo = checkout(tmp_path)
    linked = tmp_path / "linked"
    run_git(repo, ["worktree", "add", "-q", "-b", "feat/linked", str(linked)])
    assert bare_checkout.main(str(linked)) == bare_checkout.EXIT_CLEAN, "a linked worktree with core.bare false must pass"
    run_git(repo, ["config", "core.bare", "true"])
    code = bare_checkout.main(str(linked))
    message = capsys.readouterr().err
    assert code == bare_checkout.EXIT_BARE_CHECKOUT, "the shared flag applies to every worktree, got code %r" % (code,)
    assert str(repo.resolve()) in message, "the message must name the main checkout that holds the flag, got %r" % (message,)


def test_the_flag_alone_is_not_enough_without_a_git_directory_of_that_name(tmp_path):
    other = tmp_path / "remote.git"
    other.mkdir()
    assert bare_checkout.bare_checkout_problem(other, "true") == "", "a directory not named .git is a bare repository"


def test_a_git_directory_name_alone_is_not_enough_without_the_flag(tmp_path):
    git_directory = tmp_path / ".git"
    git_directory.mkdir()
    assert bare_checkout.bare_checkout_problem(git_directory, "false") == "", "core.bare false is a normal checkout"
    assert bare_checkout.bare_checkout_problem(git_directory, "") == "", "an unset flag is a normal checkout"


def test_a_missing_git_directory_is_not_reported(tmp_path):
    missing = Path(tmp_path / "gone" / ".git")
    assert bare_checkout.bare_checkout_problem(missing, "true") == "", "only an existing .git directory marks a checkout"


def test_a_flag_spelled_yes_is_read_as_true(tmp_path):
    repo = checkout(tmp_path)
    run_git(repo, ["config", "core.bare", "yes"])
    code = bare_checkout.main(str(repo))
    assert code == bare_checkout.EXIT_BARE_CHECKOUT, "git reads yes as true, so the check must too, got code %r" % (code,)


def test_an_unset_flag_passes(tmp_path):
    repo = checkout(tmp_path)
    run_git(repo, ["config", "--unset", "core.bare"])
    code = bare_checkout.main(str(repo))
    assert code == bare_checkout.EXIT_CLEAN, "an unset core.bare is a normal checkout, got code %r" % (code,)
