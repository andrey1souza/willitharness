import pytest

from git_repo import TEST_EMAIL, init_repo, run_git
from guards import private_names

TERM = "zzprivateterm"
FIRST_TERM = "zzfirstterm"
SECOND_TERM = "zzsecondterm"


@pytest.fixture
def repo(tmp_path):
    return init_repo(tmp_path, TEST_EMAIL)


def environment_with(tmp_path_factory, terms):
    denylist = tmp_path_factory.mktemp("config") / "denylist"
    denylist.write_text("\n".join(terms) + "\n")
    return {private_names.DENYLIST_VARIABLE: str(denylist)}


@pytest.fixture
def environment(tmp_path_factory):
    return environment_with(tmp_path_factory, [TERM])


def stage_note(repo, text):
    (repo / "notes.md").write_text(text)
    run_git(repo, ["add", "notes.md"])


def test_staged_term_is_reported_without_echoing_the_term(repo, environment, capsys):
    stage_note(repo, "hello %s world\n" % TERM)
    code = private_names.main(["--staged"], environment, str(repo))
    message = capsys.readouterr().err
    assert code == private_names.EXIT_LEAK, "a staged denylisted term must fail, got code %r" % (code,)
    assert "notes.md" in message, "the report must name the file, got %r" % (message,)
    assert TERM not in message, "the report must not repeat the private term, got %r" % (message,)
    assert "Fix:" in message, "the report must end with a fix, got %r" % (message,)


def test_clean_staged_files_pass(repo, environment):
    stage_note(repo, "nothing private here\n")
    code = private_names.main(["--staged"], environment, str(repo))
    assert code == private_names.EXIT_CLEAN, "clean staged files must pass, got code %r" % (code,)


def test_committed_term_is_found_by_revision(repo, environment):
    stage_note(repo, "hello %s world\n" % TERM)
    run_git(repo, ["commit", "-q", "-m", "feat: add notes"])
    code = private_names.main(["--rev", "HEAD"], environment, str(repo))
    assert code == private_names.EXIT_LEAK, "a committed denylisted term must fail by revision, got code %r" % (code,)


def test_clean_revision_passes(repo, environment):
    stage_note(repo, "clean\n")
    run_git(repo, ["commit", "-q", "-m", "feat: add notes"])
    code = private_names.main(["--rev", "HEAD"], environment, str(repo))
    assert code == private_names.EXIT_CLEAN, "a clean revision must pass, got code %r" % (code,)


def test_second_pattern_alone_is_enough_to_fail(repo, tmp_path_factory):
    environment = environment_with(tmp_path_factory, [FIRST_TERM, SECOND_TERM])
    stage_note(repo, "only the %s appears here\n" % SECOND_TERM)
    code = private_names.main(["--staged"], environment, str(repo))
    assert code == private_names.EXIT_LEAK, (
        "the second of two patterns must match, so the pattern file is read in full, got code %r" % (code,)
    )


def test_missing_denylist_blocks_with_a_fix(repo, tmp_path, capsys):
    environment = {private_names.DENYLIST_VARIABLE: str(tmp_path / "absent")}
    code = private_names.main(["--staged"], environment, str(repo))
    message = capsys.readouterr().err
    assert code == private_names.EXIT_BLOCKED, "a missing denylist must block, got code %r" % (code,)
    assert "Fix:" in message, "the block message must end with a fix, got %r" % (message,)
