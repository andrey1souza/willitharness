import json
import re

import pytest

import sandbox_live

GOOD_REPLY = "BLOCKED_WRITE\nWROTE_INSIDE\nBLOCKED_SSH\nNET_BLOCKED\nhello from the stub"
GOOD_CALLS = "greet\n"
CHEAP = 0.001
EXPENSIVE = 0.06
BROKEN_REPLIES = {
    "outside": (GOOD_REPLY.replace("BLOCKED_WRITE", "WROTE_OUTSIDE"), "a write outside the workspace was not blocked"),
    "outside-both": (GOOD_REPLY + "\nWROTE_OUTSIDE", "a write outside the workspace was not blocked"),
    "outside-word-missing": (GOOD_REPLY.replace("BLOCKED_WRITE\n", ""), "a write outside the workspace was not blocked"),
    "inside": (GOOD_REPLY.replace("WROTE_INSIDE", "BLOCKED_INSIDE"), "a write inside the workspace did not work"),
    "inside-both": (GOOD_REPLY + "\nBLOCKED_INSIDE", "a write inside the workspace did not work"),
    "ssh": (GOOD_REPLY.replace("BLOCKED_SSH", "READ_SSH"), "the .ssh folder was readable"),
    "ssh-both": (GOOD_REPLY + "\nREAD_SSH", "the .ssh folder was readable"),
    "network": (GOOD_REPLY.replace("NET_BLOCKED", "NET_OK"), "the network was reachable"),
    "network-both": (GOOD_REPLY + "\nNET_OK", "the network was reachable"),
    "stub": (GOOD_REPLY.replace("hello from the stub", ""), "the stub output did not reach the reply"),
}


def result_transcript(reply, cost):
    return [json.dumps({"type": "result", "subtype": "success", "is_error": False, "result": reply, "total_cost_usd": cost})]


def runner_replying(reply, cost, calls, base):
    def run(run_root, command):
        assert "--settings" in command, f"the gate must pass the settings, got {command}"
        (base / run_root.name / "calls.log").write_text(calls)
        return result_transcript(reply, cost)

    return run


def outside_name_of(command):
    match = re.search(r"\$HOME/(\.willitharness-sandbox-probe-\w+)", command[2])
    assert match, f"the prompt names no outside file: {command[2]!r}"
    return match.group(1)


def home_with_secret_folder(tmp_path):
    home = tmp_path / "home"
    (home / ".ssh").mkdir(parents=True)
    (tmp_path / "runs").mkdir()
    return home


def test_a_full_confinement_reply_with_the_stub_call_and_a_low_cost_fails_no_check():
    assert sandbox_live.failed_checks(GOOD_REPLY, False, GOOD_CALLS, CHEAP) == [], "the good reply must pass every check"


@pytest.mark.parametrize("name", sorted(BROKEN_REPLIES))
def test_each_broken_reply_fails_exactly_its_check(name):
    reply, message = BROKEN_REPLIES[name]
    assert sandbox_live.failed_checks(reply, False, GOOD_CALLS, CHEAP) == [message], f"{name} must fail only {message!r}"


def test_an_empty_reply_fails_every_reply_check(tmp_path):
    assert len(sandbox_live.failed_checks("", False, GOOD_CALLS, CHEAP)) == 5, "an empty reply proves none of the five probes"


def test_a_file_that_exists_outside_fails_even_when_the_reply_says_blocked():
    assert sandbox_live.failed_checks(GOOD_REPLY, True, GOOD_CALLS, CHEAP) == ["a write outside the workspace was not blocked"], "the file on disk is the truth, not the reply"


def test_a_lost_stub_call_and_an_overspend_each_fail_their_check():
    assert sandbox_live.failed_checks(GOOD_REPLY, False, "", CHEAP) == ["the calls log lost the stub call"], "an empty calls log means the stub could not log under the sandbox"
    assert sandbox_live.failed_checks(GOOD_REPLY, False, GOOD_CALLS, EXPENSIVE) == ["the run cost more than the cap"], "a cost above the cap fails"


def test_the_probe_command_has_one_distinct_word_per_probe_and_the_literal_steps():
    command = sandbox_live.sandbox_probe_script(".willitharness-sandbox-probe-abc")
    assert command == (
        "bash -c 'touch \"$HOME/.willitharness-sandbox-probe-abc\" 2>/dev/null && echo WROTE_OUTSIDE || echo BLOCKED_WRITE; "
        "touch inside-probe.txt 2>/dev/null && echo WROTE_INSIDE || echo BLOCKED_INSIDE; "
        'ls "$HOME/.ssh" >/dev/null 2>&1 && echo READ_SSH || echo BLOCKED_SSH; '
        "curl -sfI -m 6 https://example.com >/dev/null 2>&1 && echo NET_OK || echo NET_BLOCKED; "
        "greet'"
    ), f"unexpected probe command {command!r}"
    assert sandbox_live.probe_prompt(".willitharness-sandbox-probe-abc").endswith(command), f"the prompt must end with the command {command!r}"


def test_a_name_without_the_gate_prefix_is_refused():
    with pytest.raises(AssertionError) as raised:
        sandbox_live.sandbox_probe_script("id_rsa")
    assert "Rule:" in str(raised.value) and "Fix:" in str(raised.value), f"unexpected message {str(raised.value)!r}"


def test_the_gate_command_has_the_bash_tool_only_the_bash_allowlist_and_the_run_settings(tmp_path):
    run_root = tmp_path.resolve() / "run"
    run_root.mkdir()
    home = home_with_secret_folder(tmp_path).resolve()
    command = sandbox_live.sandbox_command(run_root, home, ".willitharness-sandbox-probe-abc")
    assert command[command.index("--tools") + 1] == "Bash" and command[command.index("--allowedTools") + 1] == "Bash(bash:*)", f"tools wrong in {command}"
    settings = json.loads(command[command.index("--settings") + 1])["sandbox"]
    assert settings["filesystem"]["allowWrite"] == [f"{run_root}/work", f"{run_root}/tmp", f"{run_root}/calls.log"], f"allowWrite wrong in {settings}"
    assert settings["failIfUnavailable"] is True and settings["network"] == {"allowedDomains": []}, f"settings wrong in {settings}"


def test_the_gate_passes_on_a_confined_run_and_prints_the_pass_line(tmp_path, capsys):
    home = home_with_secret_folder(tmp_path)
    runs = tmp_path / "runs"
    code = sandbox_live.main(runner_replying(GOOD_REPLY, CHEAP, GOOD_CALLS, runs), home, runs)
    out = capsys.readouterr().out
    assert code == 0 and out.endswith("GATE SANDBOX PASS\n"), f"the gate must pass and end with the pass line, got {code} with {out!r}"
    assert "failed:" not in out and "cost: $0.0010" in out, f"a passing gate prints no failure and the cost, got {out!r}"


@pytest.mark.parametrize("name", sorted(BROKEN_REPLIES))
def test_the_gate_fails_for_each_broken_reply(tmp_path, capsys, name):
    reply, message = BROKEN_REPLIES[name]
    home = home_with_secret_folder(tmp_path)
    runs = tmp_path / "runs"
    code = sandbox_live.main(runner_replying(reply, CHEAP, GOOD_CALLS, runs), home, runs)
    out = capsys.readouterr().out
    assert code == 1 and f"failed: {message}\nsandbox not proven\n" in out and "GATE" not in out, f"{name} must fail the gate with {message!r} and no pass line, got {code} with {out!r}"


def test_the_gate_fails_on_an_overspend_a_lost_stub_call_and_a_silent_agent(tmp_path, capsys):
    home = home_with_secret_folder(tmp_path)
    runs = tmp_path / "runs"
    assert sandbox_live.main(runner_replying(GOOD_REPLY, EXPENSIVE, GOOD_CALLS, runs), home, runs) == 1, "a run above the cost cap must fail the gate"
    assert sandbox_live.main(runner_replying(GOOD_REPLY, CHEAP, "", runs), home, runs) == 1, "a run whose calls log lost the stub call must fail the gate"
    assert sandbox_live.main(no_reply_runner, home, runs) == 1, "a run with no reply must fail the gate"
    assert capsys.readouterr().out.count("sandbox not proven") == 3, "each failure must print the message"


def no_reply_runner(run_root, command):
    assert run_root.is_dir() and command, f"the gate must hand the runner a folder and a command, got {run_root} and {command}"
    return []


def test_a_file_the_agent_wrote_outside_fails_the_gate_and_is_cleaned_up(tmp_path, capsys):
    home = home_with_secret_folder(tmp_path)
    runs = tmp_path / "runs"
    replying = runner_replying(GOOD_REPLY, CHEAP, GOOD_CALLS, runs)

    def leaking_runner(run_root, command):
        (home / outside_name_of(command)).write_text("leak")
        return replying(run_root, command)

    code = sandbox_live.main(leaking_runner, home, runs)
    out = capsys.readouterr().out
    assert code == 1 and "failed: a write outside the workspace was not blocked" in out, f"a leaked file must fail the gate with the outside-write message, got {code} with {out!r}"
    assert sorted(path.name for path in home.iterdir()) == [".ssh"], f"the gate must remove its own file, found {sorted(path.name for path in home.iterdir())}"


def test_a_home_without_the_secret_folder_proves_nothing_and_fails_before_any_run(tmp_path, capsys):
    home = tmp_path / "home"
    home.mkdir()

    def never(run_root, command):
        raise AssertionError(f"the agent must not run without a secret folder to protect, got {run_root} and {command}")

    assert sandbox_live.main(never, home) == 1, "no secret folder must fail the gate"
    out = capsys.readouterr().out
    assert "the .ssh folder is missing" in out, f"the message must say why the gate stopped, got {out!r}"


def test_a_runner_that_raises_still_removes_the_outside_file(tmp_path):
    home = home_with_secret_folder(tmp_path)

    def failing_runner(run_root, command):
        (home / outside_name_of(command)).write_text("leak")
        raise RuntimeError(f"agent crashed in {run_root}")

    with pytest.raises(RuntimeError):
        sandbox_live.main(failing_runner, home, tmp_path / "runs")
    assert sorted(path.name for path in home.iterdir()) == [".ssh"], f"the gate must remove its file even after a crash, found {sorted(path.name for path in home.iterdir())}"
