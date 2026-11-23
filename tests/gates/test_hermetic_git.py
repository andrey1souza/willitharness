import subprocess


def git_value(directory, name):
    return subprocess.run(["git", "config", "--get", name], cwd=directory, capture_output=True, text=True)


def test_no_git_identity_is_visible_to_a_test(tmp_path):
    for name in ("user.name", "user.email"):
        found = git_value(tmp_path, name)
        assert found.returncode != 0 and not found.stdout.strip(), f"git shows {name} {found.stdout!r} to a test. Rule: a test runs without the identity of the person who runs it, as CI does. Fix: hide the global git config in tests/conftest.py."


def commit_needing_a_config_identity(directory):
    subprocess.run(["git", "init", "-q"], cwd=directory, check=True)
    return subprocess.run(["git", "-c", "user.useConfigOnly=true", "commit", "-q", "--allow-empty", "-m", "x"], cwd=directory, capture_output=True, text=True)


def test_a_commit_that_needs_an_identity_from_config_fails(tmp_path):
    committed = commit_needing_a_config_identity(tmp_path)
    assert committed.returncode != 0, f"a commit worked with no identity in config, got {committed.stdout!r} {committed.stderr!r}. Rule: a test that commits sets its own identity. Fix: hide the global git config in tests/conftest.py."
