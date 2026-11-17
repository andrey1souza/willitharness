import pytest

from git_repo import init_repo, run_git
from guards import identity

ALLOWED = "16019275+andrey1souza@users.noreply.github.com"
WORK = "122283945+SomeoneElse@users.noreply.github.com"
ACCOUNT = "andrey1souza"
WORK_ACCOUNT = "AndreySouzaThoughtworks"
GLOBAL_CONFIG_VARIABLE = "GIT_CONFIG_GLOBAL"


@pytest.fixture
def repo(tmp_path):
    prepared = init_repo(tmp_path, email=ALLOWED)
    run_git(prepared, ["config", identity.ACCOUNT_KEY, ACCOUNT])
    return prepared


def set_email(repo, email):
    run_git(repo, ["config", "user.email", email])


def test_personal_noreply_address_and_account_are_accepted(repo):
    code = identity.main({}, str(repo))
    assert code == identity.EXIT_CLEAN, "the personal address and account must pass, got code %r" % (code,)


def test_other_account_address_is_rejected_with_a_fix(repo, capsys):
    set_email(repo, WORK)
    code = identity.main({}, str(repo))
    message = capsys.readouterr().err
    assert code == identity.EXIT_WRONG_IDENTITY, "another account address must fail, got code %r" % (code,)
    assert WORK in message, "the message must show the rejected address, got %r" % (message,)
    assert "Fix:" in message, "the message must end with a fix, got %r" % (message,)


def test_private_address_is_rejected(repo):
    set_email(repo, "someone@example.com")
    code = identity.main({}, str(repo))
    assert code == identity.EXIT_WRONG_IDENTITY, "a private address must fail, got code %r" % (code,)


def test_pattern_can_be_overridden_by_the_environment(repo):
    set_email(repo, "someone@example.com")
    environment = {identity.PATTERN_VARIABLE: r"^someone@example\.com$"}
    code = identity.main(environment, str(repo))
    assert code == identity.EXIT_CLEAN, "an address matching the override must pass, got code %r" % (code,)


def test_work_account_in_the_repo_is_rejected_with_a_fix(repo, capsys):
    run_git(repo, ["config", identity.ACCOUNT_KEY, WORK_ACCOUNT])
    code = identity.main({}, str(repo))
    message = capsys.readouterr().err
    assert code == identity.EXIT_WRONG_IDENTITY, "the work account must fail, got code %r" % (code,)
    assert WORK_ACCOUNT in message, "the message must show the wrong account, got %r" % (message,)
    assert "Fix:" in message, "the message must end with a fix, got %r" % (message,)


def test_unset_account_is_rejected_with_a_fix(repo, capsys):
    run_git(repo, ["config", "--unset", identity.ACCOUNT_KEY])
    code = identity.main({}, str(repo))
    message = capsys.readouterr().err
    assert code == identity.EXIT_WRONG_IDENTITY, "an unset account must fail, got code %r" % (code,)
    assert "unset in this repo" in message, "the message must say the account is unset, got %r" % (message,)


def test_global_account_setting_does_not_count(tmp_path, monkeypatch, capsys):
    global_config = tmp_path / "global.gitconfig"
    global_config.write_text('[credential "https://github.com"]\n\tusername = %s\n' % ACCOUNT)
    monkeypatch.setenv(GLOBAL_CONFIG_VARIABLE, str(global_config))
    repo_directory = tmp_path / "work"
    repo_directory.mkdir()
    init_repo(repo_directory, email=ALLOWED)
    code = identity.main({}, str(repo_directory))
    message = capsys.readouterr().err
    assert code == identity.EXIT_WRONG_IDENTITY, (
        "a global account setting must not satisfy the check, got code %r" % (code,)
    )
    assert "unset in this repo" in message, "the message must say the repo-local value is unset, got %r" % (message,)


def test_account_can_be_overridden_by_the_environment(repo):
    run_git(repo, ["config", identity.ACCOUNT_KEY, "someone-else"])
    environment = {identity.ACCOUNT_VARIABLE: "someone-else"}
    code = identity.main(environment, str(repo))
    assert code == identity.EXIT_CLEAN, "an account matching the override must pass, got code %r" % (code,)
