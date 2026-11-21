import pytest

from git_repo import init_repo, run_git
from guards import identity

ALLOWED = "16019275+andrey1souza@users.noreply.github.com"
WORK = "122283945+SomeoneElse@users.noreply.github.com"
ACCOUNT = "andrey1souza"
WORK_ACCOUNT = "AndreySouzaThoughtworks"
GLOBAL_CONFIG_VARIABLE = "GIT_CONFIG_GLOBAL"
PERSONAL_KEY = "AAAAC3NzaC1lZDI1NTE5AAAAIPersonalPersonalPersonalPersonalPersonal"
WORK_KEY = "AAAAC3NzaC1lZDI1NTE5AAAAIWorkWorkWorkWorkWorkWorkWorkWorkWorkWorkWork"
SIGNERS_TEXT = f"{ALLOWED} ssh-ed25519 {PERSONAL_KEY}\nwork@example.com ssh-ed25519 {WORK_KEY}\n"


@pytest.fixture
def repo(tmp_path):
    prepared = init_repo(tmp_path, email=ALLOWED)
    run_git(prepared, ["config", identity.ACCOUNT_KEY, ACCOUNT])
    (tmp_path / "personal.pub").write_text(f"ssh-ed25519 {PERSONAL_KEY} personal\n")
    (tmp_path / "work.pub").write_text(f"ssh-ed25519 {WORK_KEY} work\n")
    (tmp_path / "signers").write_text(SIGNERS_TEXT)
    run_git(prepared, ["config", identity.SIGNING_KEY, str(tmp_path / "personal.pub")])
    run_git(prepared, ["config", identity.SIGNERS_KEY, str(tmp_path / "signers")])
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


def test_pattern_can_be_overridden_by_the_environment(repo, tmp_path):
    set_email(repo, "someone@example.com")
    (tmp_path / "signers").write_text(f"someone@example.com ssh-ed25519 {PERSONAL_KEY}\n")
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


def test_a_signing_key_that_is_not_listed_for_the_email_is_rejected_with_a_fix(repo, capsys):
    run_git(repo, ["config", identity.SIGNING_KEY, str(repo / "work.pub")])
    code = identity.main({}, str(repo))
    message = capsys.readouterr().err
    assert code == identity.EXIT_WRONG_IDENTITY, "a key listed only for another address must fail, got code %r" % (code,)
    assert "not listed for" in message and "Fix:" in message, "the message needs the rule and the fix, got %r" % (message,)


def test_an_unset_signing_key_is_rejected(repo, capsys):
    run_git(repo, ["config", identity.SIGNING_KEY, ""])
    code = identity.main({}, str(repo))
    message = capsys.readouterr().err
    assert code == identity.EXIT_WRONG_IDENTITY and "is unset" in message, "an empty signing key must fail, got %r %r" % (code, message)


def test_a_signing_key_file_without_a_public_key_is_rejected(repo, tmp_path, capsys):
    (tmp_path / "personal.pub").write_text("")
    code = identity.main({}, str(repo))
    message = capsys.readouterr().err
    assert code == identity.EXIT_WRONG_IDENTITY and "holds no public key" in message, "got %r %r" % (code, message)


def test_the_key_must_belong_to_the_same_line_as_the_email():
    signers = f"other@example.com ssh-ed25519 {PERSONAL_KEY}\n{ALLOWED} ssh-ed25519 {WORK_KEY}\n"
    assert not identity.principal_trusts_key(signers, ALLOWED, PERSONAL_KEY), f"a key on another address line must not count in {signers!r}"
    assert identity.principal_trusts_key(signers, ALLOWED, WORK_KEY), f"a key on the address line must count in {signers!r}"


def test_a_comma_separated_principal_list_is_read():
    signers = f"first@example.com,{ALLOWED} ssh-ed25519 {PERSONAL_KEY}\n"
    assert identity.principal_trusts_key(signers, ALLOWED, PERSONAL_KEY), f"the address may be one of several principals in {signers!r} for {ALLOWED!r}"


def test_key_blob_is_the_second_field():
    assert identity.key_blob(f"ssh-ed25519 {PERSONAL_KEY} comment") == PERSONAL_KEY, "the blob follows the key type"
    assert identity.key_blob("ssh-ed25519") == "", "a line without a blob gives an empty blob"
