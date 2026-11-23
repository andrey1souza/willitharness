import argparse
import json
import os
import sys
from dataclasses import replace

import pytest

from agent_site import CELL, ONE_RUN, OVERLAY_NAME, add_overlay_file, guard_site, install_fake_agent_environment, prepare_project_with_fake_agent, run_one
from cli_runner import run_cli
from fake_claude import DENIED_COMMAND, FAKE_VERSION, report_of
from files import write_tree
from lifecycle_site import ready_site, run_setup, stored_final_runs, validate_site

from willitharness import cli
from willitharness.claude_agent import probe_argv, run_command
from willitharness.lifecycle import record_reachability, start_running
from willitharness.plan import PlanError
from willitharness.real_runner import claude_runner
from willitharness.store import RunState
from willitharness.stream import parse_stream
from willitharness.vocabulary import Reach

pytestmark = pytest.mark.skipif(sys.platform != "darwin", reason="the real runner uses macOS sandbox-exec")
PLANTED_KEY = "fakefakefakefakefake"
PLANTED_TOKEN = "dummydummydummydummy"
KEY_VARIABLE = "ANTHROPIC_API_KEY"
TOKEN_VARIABLE = "CLAUDE_CODE_OAUTH_TOKEN"
RUN_FOLDER = (".willitharness", "demo", "runs", "A", "stop-server", "1")
STUB_COMMANDS = "pkill -f vitest\npkill second\n"
EXPECTED_CALLS = "pkill -f vitest\npkill second\n"
ISOLATION_FLAGS = ("--strict-mcp-config", "--disable-slash-commands", "--no-session-persistence")


def run_with_commands(tmp_path, monkeypatch, behavior, commands):
    site = prepare_project_with_fake_agent(tmp_path, monkeypatch, ONE_RUN, behavior)
    add_overlay_file(site, "fake-commands.txt", commands)
    return site, run_one(site)


def artifact(tmp_path, name):
    return tmp_path.joinpath("project", *RUN_FOLDER, name)


def flag_value(arguments, flag):
    assert flag in arguments, f"{flag} is missing from {arguments}"
    return arguments[arguments.index(flag) + 1]


def test_an_effect_run_has_the_bash_tool_only_and_the_allowlist_from_the_world(tmp_path, monkeypatch):
    site = prepare_project_with_fake_agent(tmp_path, monkeypatch, ONE_RUN, "ok")
    arguments = report_of(run_one(site).transcript)["arguments"]
    assert flag_value(arguments, "--tools") == "Bash", f"an effect run must have Bash only, got {arguments}"
    assert flag_value(arguments, "--allowedTools") == "Bash(ls:*),Bash(pkill:*)", f"the allowlist must hold the task and real commands, got {arguments}"
    assert flag_value(arguments, "--permission-mode") == "default", f"the permission mode must be default. Fix: pass --permission-mode default, got {arguments}"


def test_an_effect_run_keeps_every_isolation_flag(tmp_path, monkeypatch):
    site = prepare_project_with_fake_agent(tmp_path, monkeypatch, ONE_RUN, "ok")
    arguments = report_of(run_one(site).transcript)["arguments"]
    assert all(flag in arguments for flag in ISOLATION_FLAGS), f"an isolation flag is missing from {arguments}"
    assert flag_value(arguments, "--setting-sources") == "project,local", f"setting sources wrong in {arguments}"


def test_a_guard_only_arm_gives_its_own_run_bash_write_and_edit(tmp_path, monkeypatch):
    site = prepare_project_with_fake_agent(tmp_path, monkeypatch, ONE_RUN, "ok")
    guard = replace(site.plan.arms[0], role="guard_only")
    arguments = report_of(run_one(replace(site, plan=replace(site.plan, arms=(guard,)))).transcript)["arguments"]
    assert flag_value(arguments, "--tools") == "Bash,Write,Edit", f"a guard run must have Bash, Write and Edit, got {arguments}"
    assert flag_value(arguments, "--allowedTools") == "Bash(ls:*),Bash(pkill:*)", f"Write and Edit must stay off the allowlist so a bypass is denied and counted, got {arguments}"


def test_a_plan_with_a_guard_arm_gives_every_arm_the_guard_tools(tmp_path, monkeypatch):
    site = prepare_project_with_fake_agent(tmp_path, monkeypatch, ONE_RUN, "ok")
    guard = replace(site.plan.arms[0], label="B", role="guard_only")
    plan = replace(site.plan, arms=(site.plan.arms[0], guard))
    two_arms = replace(site, plan=plan)
    record_reachability(two_arms, "B", Reach.LOADED)
    arguments = report_of(run_one(two_arms).transcript)["arguments"]
    assert flag_value(arguments, "--tools") == "Bash,Write,Edit", f"arm A runs in a plan that has a guard arm, so it needs the guard tools, got {arguments}"


def test_a_stub_logs_its_arguments_prints_the_canned_output_and_exits_zero(tmp_path, monkeypatch):
    site, result = run_with_commands(tmp_path, monkeypatch, "tools", STUB_COMMANDS + "pkill; echo status=$?\n")
    outputs = report_of(result.transcript)["tool_outputs"]
    assert outputs == ["stub-killed\n", "stub-killed\n", "stub-killed\nstatus=0\n"], f"the stub must print its canned output and exit 0, got {outputs}"
    assert artifact(tmp_path, "calls-1.log").read_text() == EXPECTED_CALLS + "pkill\n", f"the calls log must hold one line per call, got {artifact(tmp_path, 'calls-1.log').read_text()!r}"


def test_the_stub_folder_is_first_on_path_and_the_rest_of_path_is_kept(tmp_path, monkeypatch):
    site = prepare_project_with_fake_agent(tmp_path, monkeypatch, ONE_RUN, "ok")
    entries = report_of(run_one(site).transcript)["path"].split(os.pathsep)
    assert entries[0].endswith("/bin") and "willitharness-run-" in entries[0] and not entries[0].endswith("/work/bin"), f"the stub folder must come first on PATH, outside the working directory, got {entries}"
    assert entries[1:] == os.environ["PATH"].split(os.pathsep), f"the rest of PATH must be kept, got {entries}"


def test_a_stub_wrapper_is_generated_from_data_and_a_world_file_never_replaces_it(tmp_path, monkeypatch):
    site = prepare_project_with_fake_agent(tmp_path, monkeypatch, ONE_RUN, "tools")
    write_tree(site.world_dir, {"bin/pkill": "#!/bin/sh\necho planted-wrapper\n", "bin/evil": "#!/bin/sh\necho planted-evil\n", "calls.log": "planted-log\n"})
    for name in ("pkill", "evil"):
        (site.world_dir / "bin" / name).chmod(0o755)
    add_overlay_file(site, "fake-commands.txt", "pkill\nevil\n")
    validate_site(site)
    outputs = report_of(run_one(site).transcript)["tool_outputs"]
    assert outputs[0] == "stub-killed\n", f"the wrapper must come from the stub data, got {outputs}"
    assert "planted-evil" not in outputs[1] and "not found" in outputs[1], f"a world bin folder must not reach PATH, got {outputs}"
    assert artifact(tmp_path, "calls-1.log").read_text() == "pkill\n", "a world calls.log must not survive into the run"


def test_the_run_stores_its_transcript_and_calls_under_the_plan_runs_folder(tmp_path, monkeypatch):
    site, result = run_with_commands(tmp_path, monkeypatch, "tools", STUB_COMMANDS)
    stored = artifact(tmp_path, "transcript-1.jsonl").read_text()
    assert stored.splitlines() == list(result.transcript), f"the stored transcript must equal the run transcript, got {stored!r}"
    assert artifact(tmp_path, "calls-1.log").read_text() == EXPECTED_CALLS, "the calls log must be stored next to the transcript"


def test_a_second_attempt_keeps_the_first_attempt_artifacts(tmp_path, monkeypatch):
    site = prepare_project_with_fake_agent(tmp_path, monkeypatch, ONE_RUN, "ok")
    setup = run_setup(site)
    runner = claude_runner(setup, "haiku")
    runner(CELL, 1, 1)
    runner(CELL, 1, 2)
    names = sorted(path.name for path in artifact(tmp_path, "").iterdir())
    assert names == ["calls-1.log", "calls-2.log", "transcript-1.jsonl", "transcript-2.jsonl"], f"each attempt keeps its own files, got {names}"


def test_a_planted_secret_reaches_the_agent_but_is_absent_from_the_stored_artifacts(tmp_path, monkeypatch):
    site = prepare_project_with_fake_agent(tmp_path, monkeypatch, ONE_RUN, "tools")
    monkeypatch.setenv(KEY_VARIABLE, PLANTED_KEY)
    monkeypatch.setenv(TOKEN_VARIABLE, PLANTED_TOKEN)
    add_overlay_file(site, "fake-commands.txt", f"pkill ${KEY_VARIABLE} ${TOKEN_VARIABLE}\n")
    result = run_one(site)
    transcript = artifact(tmp_path, "transcript-1.jsonl").read_text()
    calls = artifact(tmp_path, "calls-1.log").read_text()
    assert PLANTED_KEY in "\n".join(result.transcript) and PLANTED_TOKEN in "\n".join(result.transcript), f"the agent never saw the planted secrets, so the check proves nothing: {result.transcript!r}"
    assert PLANTED_KEY not in transcript and PLANTED_TOKEN not in transcript, f"a secret survived in the stored transcript: {transcript!r}"
    assert calls == "pkill [redacted] [redacted]\n", f"the calls log must hold the redaction marker in place of both secrets, got {calls!r}"
    assert "stub-killed" in transcript and "[redacted]" in transcript, f"redaction must replace the secrets only, got {transcript!r}"


@pytest.mark.parametrize("marker", ["CLAUDE.md", "AGENTS.md", ".claude"])
@pytest.mark.parametrize("holder", ["grandparent", "outer", "base"])
def test_the_runner_refuses_a_workspace_base_with_an_instruction_file_above_it(tmp_path, monkeypatch, marker, holder):
    site = prepare_project_with_fake_agent(tmp_path, monkeypatch, ONE_RUN, "ok")
    base = tmp_path / "outer" / "base"
    base.mkdir(parents=True)
    planted = {"grandparent": tmp_path, "outer": tmp_path / "outer", "base": base}[holder]
    if marker == ".claude":
        (planted / marker).mkdir()
    else:
        (planted / marker).write_text("planted rule")
    with pytest.raises(PlanError) as raised:
        claude_runner(run_setup(site), "haiku", base)
    message = str(raised.value)
    assert str(planted / marker) in message and "Rule:" in message and "Fix:" in message, f"the refusal must name the file, the rule and the fix, got {message!r}"
    assert not stored_final_runs(site), f"a refused runner must start no run, found {stored_final_runs(site)}"


def test_a_clean_workspace_base_is_used_for_the_workspace(tmp_path, monkeypatch):
    site = prepare_project_with_fake_agent(tmp_path, monkeypatch, ONE_RUN, "ok")
    base = tmp_path / "clean" / "base"
    base.mkdir(parents=True)
    result = run_one(site, base)
    assert report_of(result.transcript)["cwd"].startswith(str(base.resolve())), f"the workspace must sit under {base}, got {report_of(result.transcript)['cwd']}"


def test_the_runner_records_the_claude_version_in_the_plan_folder(tmp_path, monkeypatch):
    site = prepare_project_with_fake_agent(tmp_path, monkeypatch, ONE_RUN, "ok")
    claude_runner(run_setup(site), "haiku")
    record = json.loads((site.root / ".willitharness" / "demo" / "agent.json").read_text())
    assert record == {"claude_version": FAKE_VERSION, "model": "haiku"}, f"the agent record is {record}. Rule: T73, agent.json holds the model next to the version. Fix: pass the model to record_agent_version."


def test_run_exits_three_with_a_fix_and_no_run_record_when_claude_is_not_on_path(tmp_path, monkeypatch, capsys):
    site = ready_site(tmp_path / "project", ONE_RUN)
    write_tree(site.root, {f"{OVERLAY_NAME}/rule.txt": "the rule text"})
    (tmp_path / "empty").mkdir()
    monkeypatch.setenv("PATH", str(tmp_path / "empty"))
    monkeypatch.chdir(site.root)
    code, out, err = run_cli(capsys, ["run", "plan.json", "--agent", "claude"])
    assert code == 3 and out == "", f"expected exit 3 and no output, got {code}, {out!r}"
    assert "claude --version failed" in err and "Rule:" in err and "Fix:" in err, f"the refusal must name the rule and the fix, got {err!r}"
    assert not stored_final_runs(site) and not (site.root / ".willitharness" / "demo" / "agent.json").exists(), f"a refused run must leave no run record and no version record, found {stored_final_runs(site)}"


def test_run_exits_three_when_claude_version_exits_nonzero(tmp_path, monkeypatch, capsys):
    site = ready_site(tmp_path / "project", ONE_RUN)
    write_tree(site.root, {f"{OVERLAY_NAME}/rule.txt": "the rule text"})
    broken = tmp_path / "broken"
    broken.mkdir()
    (broken / "claude").write_text("#!/bin/sh\necho 1.0.0-broken\nexit 1\n")
    (broken / "claude").chmod(0o755)
    monkeypatch.setenv("PATH", f"{broken}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.chdir(site.root)
    code, out, err = run_cli(capsys, ["run", "plan.json", "--agent", "claude"])
    assert code == 3 and "it exited 1" in err, f"a failing claude --version must exit 3 even when it prints a version, got {code}, {err!r}"
    assert not stored_final_runs(site), f"a refused run must leave no run record, found {stored_final_runs(site)}"


def test_run_exits_three_when_claude_version_prints_nothing(tmp_path, monkeypatch, capsys):
    site = ready_site(tmp_path / "project", ONE_RUN)
    write_tree(site.root, {f"{OVERLAY_NAME}/rule.txt": "the rule text"})
    silent = tmp_path / "silent"
    silent.mkdir()
    (silent / "claude").write_text("#!/bin/sh\nexit 0\n")
    (silent / "claude").chmod(0o755)
    monkeypatch.setenv("PATH", f"{silent}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.chdir(site.root)
    code, out, err = run_cli(capsys, ["run", "plan.json", "--agent", "claude"])
    assert code == 3 and "printed ''" in err, f"an empty claude --version must exit 3, got {code}, {err!r}"
    assert not stored_final_runs(site), f"a refused run must leave no run record, found {stored_final_runs(site)}"


def test_each_rep_and_cell_has_its_own_artifact_folder(tmp_path, monkeypatch):
    site = prepare_project_with_fake_agent(tmp_path, monkeypatch, ONE_RUN, "ok")
    start_running(site)
    runner = claude_runner(run_setup(site), "haiku")
    runner(CELL, 1, 1)
    runner(CELL, 2, 1)
    folders = sorted(path.name for path in tmp_path.joinpath("project", *RUN_FOLDER[:-1]).iterdir())
    assert folders == ["1", "2"], f"each rep keeps its own folder, got {folders}"


def test_permission_denials_in_the_stream_stay_countable(tmp_path, monkeypatch):
    _, result = run_with_commands(tmp_path, monkeypatch, "tools deny", STUB_COMMANDS)
    record = parse_stream(list(result.transcript), (), 0.02)
    assert record.state is RunState.RECORDED_USABLE and record.denials == 1, f"the denial must be counted, got {record}"
    assert record.commands == ("pkill -f vitest", "pkill second"), f"the attempts must stay listed, got {record.commands}"
    assert DENIED_COMMAND in result.transcript[-1], "the denied command must stay in the result event"


SCAFFOLDING_NAMES = {"bin", "calls.log", "stubs", "tasks.txt", "real.txt", "prompts"}
PROBE_COMMANDS = "ls -a\ncat bin/cp\ncat calls.log\nfind .\ncat tasks.txt\n"
WRAPPER_FOLDER = "${PATH%%:*}"


def test_the_agent_sees_no_scaffolding_in_its_working_directory(tmp_path, monkeypatch):
    site = prepare_project_with_fake_agent(tmp_path, monkeypatch, ONE_RUN, "tools")
    write_tree(site.world_dir, {"package.json": "{}"})
    add_overlay_file(site, "fake-commands.txt", "pkill x\n" + PROBE_COMMANDS)
    validate_site(site)
    listing, missing_wrapper, missing_log, found, missing_tasks = report_of(run_one(site).transcript)["tool_outputs"][1:]
    assert sorted(listing.split()) == [".", "..", "fake-behavior.txt", "fake-commands.txt", "fake-escape-target.txt", "inside.txt", "package.json", "rule.txt"], f"ls -a shows more than the project files and the overlay: {listing!r}"
    assert {line.removeprefix("./") for line in found.splitlines()} == {"."} | set(listing.split()) - {".", ".."}, f"find shows more than ls: {found!r}"
    assert "No such file" in missing_wrapper and "No such file" in missing_log and "No such file" in missing_tasks, f"a scaffolding file was readable: {missing_wrapper!r} {missing_log!r} {missing_tasks!r}"
    assert artifact(tmp_path, "calls-1.log").read_text() == "pkill x\n", "the call must still be logged and stored"


def test_a_guard_run_cannot_write_into_the_wrapper_folder_or_beside_the_calls_log(tmp_path, monkeypatch):
    attacks = f'echo x >> "{WRAPPER_FOLDER}/pkill"; echo status=$?\necho x > "{WRAPPER_FOLDER}/planted"; echo status=$?\necho x > "{WRAPPER_FOLDER}/../planted"; echo status=$?\npkill\n'
    site = guard_site(prepare_project_with_fake_agent(tmp_path, monkeypatch, ONE_RUN, "tools"))
    add_overlay_file(site, "fake-commands.txt", attacks)
    result = run_one(site)
    outputs = report_of(result.transcript)["tool_outputs"]
    assert all(output.startswith("status=1\n") and "Operation not permitted" in output for output in outputs[:3]), f"a write outside the workspace must fail under the sandbox, got {outputs}"
    assert outputs[3] == "stub-killed\n", f"the wrapper must be untouched, got {outputs[3]!r}"


def test_a_probe_run_for_a_system_prompt_arm_passes_the_same_flag_and_keeps_no_tools(tmp_path, monkeypatch):
    install_fake_agent_environment(tmp_path, monkeypatch)
    rule = tmp_path / "system-prompt.txt"
    rule.write_bytes(b"probe rule")
    work = tmp_path / "work"
    work.mkdir()
    report = report_of(run_command(work, probe_argv("What value?", "haiku", 0.03, str(rule))))
    assert flag_value(report["arguments"], "--append-system-prompt-file") == str(rule), f"the probe must use the run channel, got {report['arguments']}"
    assert bytes.fromhex(report["system_prompt_hex"]) == b"probe rule" and flag_value(report["arguments"], "--tools") == "", f"unexpected report {report}"


def test_the_cli_probe_runner_hands_the_system_prompt_file_to_the_agent(tmp_path, monkeypatch):
    install_fake_agent_environment(tmp_path, monkeypatch)
    rule = tmp_path / "system-prompt.txt"
    rule.write_bytes(b"cli rule")
    work = tmp_path / "work"
    work.mkdir()
    arguments = argparse.Namespace(directory=work, label="Verification code", model="haiku", run_budget_usd=0.03, system_prompt_file=str(rule))
    report = report_of(cli.claude_runner_for_cli(arguments, 0))
    assert flag_value(report["arguments"], "--append-system-prompt-file") == str(rule), f"got {report['arguments']}"
