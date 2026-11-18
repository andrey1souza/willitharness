import os
import sys

import pytest

import run_live
from fake_claude import COMMANDS_VARIABLE, install_fake_claude
from lifecycle_site import success_transcript

from willitharness.real_runner import claude_runner

pytestmark = pytest.mark.skipif(sys.platform != "darwin", reason="the real runner uses macOS sandbox-exec")


def install_fake_agent(tmp_path, monkeypatch):
    bin_dir = install_fake_claude(tmp_path / "bin")
    config = tmp_path / "config"
    config.mkdir()
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(config))
    assert (bin_dir / "claude").is_file(), f"the fake agent is missing in {bin_dir}"
    return bin_dir


def test_a_plan_whose_runs_all_finish_within_the_cap_and_call_the_stub_prints_the_pass_line(tmp_path, monkeypatch, capsys):
    install_fake_agent(tmp_path, monkeypatch)
    monkeypatch.setenv(COMMANDS_VARIABLE, "greet now")
    code = run_live.main([], claude_runner)
    out = capsys.readouterr().out
    assert code == 0, f"the gate must pass, got {code} with {out!r}"
    assert "plan: Complete; usable runs: 2 of 2\nstub calls: 2 of 2\ncost: $0.0200" in out and out.endswith("GATE G3.10 PASS\n"), f"unexpected output {out!r}"


def test_a_plan_whose_agent_never_calls_the_stub_is_not_proven_and_exits_one(tmp_path, monkeypatch, capsys):
    install_fake_agent(tmp_path, monkeypatch)
    code = run_live.main([], claude_runner)
    out = capsys.readouterr().out
    assert code == 1 and "stub calls: 0 of 2" in out and "run not proven" in out and "GATE" not in out, f"a run that skips the stub must not pass, got {code} with {out!r}"


def test_the_live_project_has_one_task_with_a_prompt_file_and_one_stub(tmp_path):
    root = run_live.write_project(tmp_path)
    assert (root / "world" / "tasks.txt").read_text() == "say-hello: greet\n", "the live world has one task that runs one stub"
    assert (root / "world" / "prompts" / "say-hello.txt").read_text() == run_live.TASK_PROMPT and (root / "world" / "stubs" / "greet" / "output.txt").read_text() == "hello from the stub\n", f"the live world has the prompt file and the stub output, got {sorted(path.name for path in (root / 'world').rglob('*'))}"


def overspending_factory(setup, model):
    assert setup.tasks and model, f"overspending_factory got {setup!r} and {model!r}. Fix: pass the run setup and a model."
    agent = claude_runner(setup, model)

    def runner(cell, rep, attempt):
        assert cell.arm and rep >= 1 and attempt >= 1, f"runner got {cell}, {rep}, {attempt}. Rule: runs count from 1."
        agent(cell, rep, attempt)
        return success_transcript(setup.site.plan.run_cap_usd * 2)

    return runner


def test_a_plan_whose_runs_all_overspend_is_not_proven_and_exits_one(tmp_path, monkeypatch, capsys):
    install_fake_agent(tmp_path, monkeypatch)
    monkeypatch.setenv(COMMANDS_VARIABLE, "greet now")
    code = run_live.main([], overspending_factory)
    out = capsys.readouterr().out
    assert code == 1 and "run not proven" in out and "GATE" not in out, f"an over-cap run must not pass, got {code} with {out!r}"


