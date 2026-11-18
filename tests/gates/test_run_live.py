import os
import sys

import pytest

import run_live
from fake_claude import install_fake_claude
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


def test_a_plan_whose_runs_all_finish_within_the_cap_prints_the_pass_line(tmp_path, monkeypatch, capsys):
    install_fake_agent(tmp_path, monkeypatch)
    code = run_live.main([], claude_runner)
    out = capsys.readouterr().out
    assert code == 0, f"the gate must pass, got {code} with {out!r}"
    assert "plan: Complete; usable runs: 2 of 2" in out and "cost: $0.0200" in out and out.endswith("GATE G3.10 PASS\n"), f"unexpected output {out!r}"


def overspending_factory(setup, model):
    assert setup.tasks and model, f"overspending_factory got {setup!r} and {model!r}. Fix: pass the run setup and a model."

    def runner(cell, rep, attempt):
        assert cell.arm and rep >= 1 and attempt >= 1, f"runner got {cell}, {rep}, {attempt}. Rule: runs count from 1."
        return success_transcript(setup.site.plan.run_cap_usd * 2)

    return runner


def test_a_plan_whose_runs_all_overspend_is_not_proven_and_exits_one(tmp_path, monkeypatch, capsys):
    install_fake_agent(tmp_path, monkeypatch)
    code = run_live.main([], overspending_factory)
    out = capsys.readouterr().out
    assert code == 1 and "run not proven" in out and "GATE" not in out, f"an over-cap run must not pass, got {code} with {out!r}"


