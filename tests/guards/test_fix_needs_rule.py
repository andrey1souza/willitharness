import pytest

from git_repo import TEST_EMAIL, commit_files, init_repo
from guards import fix_needs_rule


@pytest.fixture
def repo(tmp_path):
    return init_repo(tmp_path, TEST_EMAIL)


@pytest.mark.parametrize(
    "subject, expected",
    [
        ("fix: stop the crash", True),
        ("fix(guards): stop the crash", True),
        ("fix!: break things", True),
        ("feat: add a thing", False),
        ("chore: tidy", False),
        ("prefix: not a fix", False),
    ],
)
def test_fix_subject_detection(subject, expected):
    assert fix_needs_rule.is_fix(subject) is expected, (
        "subject %r should be fix=%r under the conventional commit form" % (subject, expected)
    )


def test_fix_without_a_check_is_rejected(repo, capsys):
    commit_files(repo, "fix: stop the crash", ["src/willitharness/a.py"])
    code = fix_needs_rule.main(["HEAD"], str(repo))
    message = capsys.readouterr().err
    assert code == fix_needs_rule.EXIT_MISSING_CHECK, "a fix with no check must fail, got code %r" % (code,)
    assert "stop the crash" in message, "the report must name the commit subject, got %r" % (message,)
    assert "Fix:" in message, "the report must end with a fix, got %r" % (message,)


def test_fix_with_a_test_is_accepted(repo):
    commit_files(repo, "fix: stop the crash", ["src/willitharness/a.py", "tests/unit/test_a.py"])
    code = fix_needs_rule.main(["HEAD"], str(repo))
    assert code == fix_needs_rule.EXIT_CLEAN, "a fix that adds a test must pass, got code %r" % (code,)


def test_feature_without_a_check_is_accepted(repo):
    commit_files(repo, "feat: add a thing", ["src/willitharness/a.py"])
    code = fix_needs_rule.main(["HEAD"], str(repo))
    assert code == fix_needs_rule.EXIT_CLEAN, "only fix commits need a check, but feat got code %r" % (code,)


def test_only_the_given_range_is_checked(repo):
    commit_files(repo, "fix: old crash", ["src/willitharness/a.py"])
    commit_files(repo, "feat: new thing", ["src/willitharness/b.py"])
    narrow = fix_needs_rule.main(["HEAD~1..HEAD"], str(repo))
    wide = fix_needs_rule.main(["HEAD"], str(repo))
    assert narrow == fix_needs_rule.EXIT_CLEAN, "the old fix is outside HEAD~1..HEAD, but got code %r" % (narrow,)
    assert wide == fix_needs_rule.EXIT_MISSING_CHECK, "the old fix is inside HEAD, but got code %r" % (wide,)
