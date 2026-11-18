import pytest

from files import plant
from willitharness.isolation import agent_environment, sandbox_profile, sandboxed_command

SECRETS = {"GH_TOKEN": "x", "AWS_SECRET_ACCESS_KEY": "x", "GITHUB_TOKEN": "x", "NPM_TOKEN": "x", "OPENAI_API_KEY": "x"}
NEEDED = {"PATH": "/bin", "HOME": "/home/u", "ANTHROPIC_API_KEY": "k", "LC_ALL": "C", "CLAUDE_CODE_ENTRYPOINT": "cli"}


def test_unrelated_secrets_never_reach_the_agent():
    scrubbed = agent_environment({**NEEDED, **SECRETS})
    assert not set(SECRETS) & scrubbed.keys(), f"secrets leaked into {sorted(scrubbed)}"


def test_the_variables_the_agent_needs_are_kept():
    scrubbed = agent_environment({**NEEDED, **SECRETS})
    assert scrubbed == NEEDED, f"expected exactly {NEEDED}, got {scrubbed}"


def test_an_environment_without_a_path_is_rejected_with_the_fix():
    with pytest.raises(AssertionError) as raised:
        agent_environment({"HOME": "/home/u"})
    assert "no PATH" in str(raised.value) and "Fix:" in str(raised.value), f"unexpected message {str(raised.value)!r}"


def test_the_profile_allows_writes_only_inside_the_world_and_the_extra_folders(tmp_path):
    world = plant(tmp_path / "world", "marker", "x")
    extra = plant(tmp_path / "cache", "marker", "x")
    home = plant(tmp_path / "home", "marker", "x")
    profile = sandbox_profile(world, home, (extra,))
    lines = profile.splitlines()
    assert lines[:3] == ["(version 1)", "(allow default)", "(deny file-write*)"], f"unexpected start {lines[:3]}"
    assert str(world.resolve()) in lines[3] and str(extra.resolve()) in lines[3], f"writable folders missing in {lines[3]!r}"


def test_the_profile_hides_every_secret_folder_under_home(tmp_path):
    world = tmp_path / "world"
    home = tmp_path / "home"
    world.mkdir()
    home.mkdir()
    deny_line = sandbox_profile(world, home, ()).splitlines()[-1]
    for name in (".ssh", ".aws", ".gnupg", ".config/gh", ".netrc", ".docker"):
        assert str((home / name).resolve()) in deny_line, f"{name} is not hidden in {deny_line!r}"


def test_a_path_with_a_quote_is_rejected(tmp_path):
    world = tmp_path / 'we"ird'
    world.mkdir()
    home = tmp_path / "home"
    home.mkdir()
    with pytest.raises(AssertionError) as raised:
        sandbox_profile(world, home, ())
    assert "quote or backslash" in str(raised.value), f"unexpected message {str(raised.value)!r}"


def test_the_wrapped_command_puts_the_profile_before_the_command():
    wrapped = sandboxed_command(["echo", "hi"], "(version 1)\n(allow default)")
    assert wrapped == ["sandbox-exec", "-p", "(version 1)\n(allow default)", "echo", "hi"], f"unexpected command {wrapped}"
