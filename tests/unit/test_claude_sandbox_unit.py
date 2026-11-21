import json

import pytest

from willitharness.claude_sandbox import NO_DOMAINS, sandbox_settings
from willitharness.isolation import SECRET_DIRECTORIES


def folders(tmp_path):
    run_root = tmp_path / "run"
    home = tmp_path / "home"
    return run_root / "work", run_root, home


def expected(tmp_path, domains):
    work, run_root, home = folders(tmp_path)
    return {
        "sandbox": {
            "enabled": True,
            "failIfUnavailable": True,
            "allowUnsandboxedCommands": False,
            "filesystem": {
                "allowWrite": [str(work), f"{run_root}/tmp", f"{run_root}/calls.log"],
                "denyRead": [f"{home}/.ssh", f"{home}/.aws", f"{home}/.gnupg", f"{home}/.config/gh", f"{home}/.netrc", f"{home}/.docker"],
            },
            "network": {"allowedDomains": domains},
        }
    }


def test_the_settings_hold_every_key_with_its_literal_value(tmp_path):
    work, run_root, home = folders(tmp_path)
    assert json.loads(sandbox_settings(work, run_root, home, NO_DOMAINS)) == expected(tmp_path, []), "the default settings differ from the literal expectation"


def test_failing_closed_and_refusing_unsandboxed_commands_are_set(tmp_path):
    sandbox = json.loads(sandbox_settings(*folders(tmp_path), NO_DOMAINS))["sandbox"]
    assert sandbox["failIfUnavailable"] is True, f"failIfUnavailable must be true, got {sandbox['failIfUnavailable']!r}. Rule: no run falls back to no sandbox."
    assert sandbox["allowUnsandboxedCommands"] is False and sandbox["enabled"] is True, f"unsandboxed commands must be refused and the sandbox on, got {sandbox}"


def test_the_network_is_closed_by_default_and_opens_only_the_named_domains(tmp_path):
    work, run_root, home = folders(tmp_path)
    assert json.loads(sandbox_settings(work, run_root, home, NO_DOMAINS))["sandbox"]["network"] == {"allowedDomains": []}, "the default network must allow no domain"
    opened = json.loads(sandbox_settings(work, run_root, home, ("example.com",)))
    assert opened == expected(tmp_path, ["example.com"]), f"a named domain must appear and nothing else change, got {opened}"


@pytest.mark.parametrize("secret", SECRET_DIRECTORIES)
def test_every_secret_folder_is_denied_for_reading(tmp_path, secret):
    work, run_root, home = folders(tmp_path)
    denied = json.loads(sandbox_settings(work, run_root, home, NO_DOMAINS))["sandbox"]["filesystem"]["denyRead"]
    assert str(home / secret) in denied, f"{secret} is missing from denyRead {denied}. Rule: every secret folder under home is hidden."


def test_the_workspace_scratch_folder_and_calls_log_are_the_only_writable_paths(tmp_path):
    work, run_root, home = folders(tmp_path)
    writable = json.loads(sandbox_settings(work, run_root, home, NO_DOMAINS))["sandbox"]["filesystem"]["allowWrite"]
    assert writable == [str(work), str(run_root / "tmp"), str(run_root / "calls.log")], f"unexpected writable paths {writable}"
    assert str(run_root) not in writable and str(run_root / "bin") not in writable, f"the run folder and the wrapper folder must stay read-only, got {writable}"


def test_a_relative_path_and_a_single_string_of_domains_are_refused(tmp_path):
    work, run_root, home = folders(tmp_path)
    with pytest.raises(AssertionError) as relative:
        sandbox_settings(work, run_root.relative_to(tmp_path), home, NO_DOMAINS)
    with pytest.raises(AssertionError) as single:
        sandbox_settings(work, run_root, home, "example.com")
    assert "Fix:" in str(relative.value) and "Fix:" in str(single.value), f"each refusal must name the fix, got {relative.value!r} and {single.value!r}"
