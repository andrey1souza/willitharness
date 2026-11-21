import pytest

from files import plant
from willitharness.isolation import agent_environment, sandbox_profile, sandboxed_command, unlisted_secret_names

SECRETS = {"GH_TOKEN": "x", "AWS_SECRET_ACCESS_KEY": "x", "GITHUB_TOKEN": "x", "NPM_TOKEN": "x", "OPENAI_API_KEY": "x"}
NEEDED = {"PATH": "/bin", "HOME": "/home/u", "ANTHROPIC_API_KEY": "k", "LC_ALL": "C", "CLAUDE_CODE_TMPDIR": "/tmp/t"}
SESSION_VARIABLES = (
    "CLAUDE_CODE_MESSAGING_TOKEN", "CLAUDE_CODE_MESSAGING_SOCKET", "CLAUDE_CODE_CHILD_SESSION", "CLAUDE_CODE_CHILD_NOTES_DIR",
    "CLAUDE_CODE_SESSION_ID", "CLAUDE_CODE_SESSION_ATTENDED", "CLAUDE_CODE_EXECPATH", "CLAUDE_CODE_ENTRYPOINT",
)
EXPLICIT_VARIABLES = (
    "CLAUDE_CONFIG_DIR", "CLAUDE_CODE_TMPDIR", "CLAUDE_CODE_FAKE_COMMANDS", "CLAUDE_CODE_FAKE_COST",
    "ANTHROPIC_API_KEY", "CLAUDE_CODE_OAUTH_TOKEN", "LC_ALL",
)
UNKNOWN_VARIABLES = ("CLAUDE_CODE_X", "CLAUDE_CODE_FUTURE_FLAG", "LC_TIME", "CLAUDE_CONFIG_DIR_EXTRA")
MINIMAL = {"PATH": "/bin"}


@pytest.mark.parametrize("name", SESSION_VARIABLES)
def test_a_parent_session_variable_is_dropped(name):
    scrubbed = agent_environment({**MINIMAL, name: "v"})
    assert name not in scrubbed, f"{name} reached the agent: {sorted(scrubbed)}"
    assert scrubbed == {"PATH": "/bin", "SHELL": "/bin/bash"}, f"only PATH and the agent shell may remain, got {scrubbed}"


@pytest.mark.parametrize("name", EXPLICIT_VARIABLES)
def test_an_explicitly_listed_variable_passes(name):
    scrubbed = agent_environment({**MINIMAL, name: "v"})
    assert scrubbed.get(name) == "v", f"{name} is on the explicit list but was dropped: {scrubbed}"
    assert scrubbed == {"PATH": "/bin", name: "v", "SHELL": "/bin/bash"}, f"unexpected variables {scrubbed}"


@pytest.mark.parametrize("name", UNKNOWN_VARIABLES)
def test_an_unknown_claude_code_or_locale_variable_is_dropped_because_there_is_no_prefix_rule(name):
    scrubbed = agent_environment({**MINIMAL, name: "v"})
    assert name not in scrubbed, f"{name} passed without being named: {sorted(scrubbed)}"
    assert scrubbed == {"PATH": "/bin", "SHELL": "/bin/bash"}, f"only PATH and the agent shell may remain, got {scrubbed}"


def test_only_the_authentication_variables_on_the_allowed_list_look_like_secrets_and_anthropic_api_key_stays_allowed_for_users_who_authenticate_with_it():
    assert unlisted_secret_names(EXPLICIT_VARIABLES) == [], f"an explicit variable looks like a secret: {unlisted_secret_names(EXPLICIT_VARIABLES)}"
    assert unlisted_secret_names([*EXPLICIT_VARIABLES, "CLAUDE_CODE_MESSAGING_TOKEN", "DB_PASSWORD"]) == ["CLAUDE_CODE_MESSAGING_TOKEN", "DB_PASSWORD"], "a secret-named variable outside the authentication set must be reported"
    assert agent_environment({**MINIMAL, "ANTHROPIC_API_KEY": "k"})["ANTHROPIC_API_KEY"] == "k", "ANTHROPIC_API_KEY must reach the agent"


def test_unrelated_secrets_never_reach_the_agent():
    scrubbed = agent_environment({**NEEDED, **SECRETS})
    assert not set(SECRETS) & scrubbed.keys(), f"secrets leaked into {sorted(scrubbed)}"


def test_the_variables_the_agent_needs_are_kept():
    scrubbed = agent_environment({**NEEDED, **SECRETS})
    assert scrubbed == {**NEEDED, "SHELL": "/bin/bash"}, f"expected the needed variables plus the agent shell, got {scrubbed}"


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


def test_the_agent_shell_is_bash_whatever_the_user_shell_is():
    scrubbed = agent_environment({**NEEDED, "SHELL": "/bin/zsh"})
    assert scrubbed["SHELL"] == "/bin/bash", f"the agent must not get the user's shell, got {scrubbed['SHELL']!r}"
    assert agent_environment(NEEDED)["SHELL"] == "/bin/bash", "the agent shell is set even when the user has none"
