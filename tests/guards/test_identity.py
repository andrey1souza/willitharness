import pytest

from git_repo import init_repo, run_git
from guards import identity

ALLOWED = "16019275+andrey1souza@users.noreply.github.com"
WORK = "122283945+SomeoneElse@users.noreply.github.com"


@pytest.fixture
def repo(tmp_path):
    return init_repo(tmp_path, email=ALLOWED)


def set_email(repo, email):
    run_git(repo, ["config", "user.email", email])


def test_personal_noreply_address_is_accepted(repo):
    code = identity.main({}, str(repo))
    assert code == identity.EXIT_CLEAN, "the personal noreply address must pass, got code %r" % (code,)


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
