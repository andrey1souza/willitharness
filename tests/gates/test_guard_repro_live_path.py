import json
import os
import shutil
import sys

import guard_repro
import pytest
from fake_claude import COMMANDS_VARIABLE, COST_VARIABLE, install_fake_claude

from willitharness.claude_agent import claude_version
from willitharness.real_runner import claude_runner

pytestmark = pytest.mark.skipif(sys.platform != "darwin", reason="the real runner uses macOS sandbox-exec")

CHEAP_RUN = "0.005"
SMALL_RUNS = "5"
VIOLATION_THEN_LISTING = "pkill -f vitest"
LISTING_ONLY = "ps -axo pid,command"
FOLLOW_BEHAVIOR = "tools follow finish"


def install_fake_agent_for_commands(tmp_path, monkeypatch, commands):
    bin_dir = install_fake_claude(tmp_path / "bin")
    config = tmp_path / "config"
    config.mkdir()
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(config))
    monkeypatch.setenv(COST_VARIABLE, CHEAP_RUN)
    monkeypatch.setenv(COMMANDS_VARIABLE, commands)
    assert "Fake Claude" in claude_version(), "the claude on PATH is not the fake agent. Rule: no test starts the real claude. Fix: put the fake first on PATH."
    assert shutil.which("claude") == str(bin_dir / "claude"), f"claude resolves to {shutil.which('claude')}, not the fake"
    return bin_dir


def following_sources(tmp_path):
    arms = tmp_path / "arms-source"
    shutil.copytree(guard_repro.SOURCES.arms, arms)
    for overlay in arms.iterdir():
        (overlay / "fake-behavior.txt").write_text(FOLLOW_BEHAVIOR)
    sources = guard_repro.Sources(arms, guard_repro.SOURCES.world)
    assert sorted(path.name for path in arms.iterdir()) == ["OLD", "USABLE"], f"unexpected arms in {arms}"
    return sources


def test_two_messages_through_the_claude_runner_show_the_usable_message_completing_more(tmp_path, monkeypatch, capsys):
    install_fake_agent_for_commands(tmp_path, monkeypatch, VIOLATION_THEN_LISTING)
    sources = following_sources(tmp_path)
    code = guard_repro.main(["--runs", SMALL_RUNS], claude_runner, sources)
    out = capsys.readouterr().out
    assert code == 0, f"the reproduction must pass with a fake agent that follows the offered alternative, got {code} with {out!r}"
    assert "OLD: completed 0 of 5, hook blocked 5 of 5" in out and "USABLE: completed 5 of 5, hook blocked 5 of 5" in out, f"unexpected counts in {out!r}"
    assert out.endswith("GATE G5.5 PASS\n"), f"the pass line is missing: {out!r}"


def test_the_same_message_through_the_claude_runner_prints_no_difference_and_exits_one(tmp_path, monkeypatch, capsys):
    install_fake_agent_for_commands(tmp_path, monkeypatch, VIOLATION_THEN_LISTING)
    sources = following_sources(tmp_path)
    code = guard_repro.main(["--runs", SMALL_RUNS, "--same-message"], claude_runner, sources)
    out = capsys.readouterr().out
    assert code == 1 and "no difference" in out.splitlines() and "GATE G5.5 PASS" not in out, f"the same message must not pass, got {code} with {out!r}"
    assert "OLD: completed 5 of 5, hook blocked 5 of 5" in out, f"both arms must carry the usable message, got {out!r}"


def test_a_run_where_the_hook_blocked_nothing_is_not_proven_even_when_the_arms_differ(tmp_path, monkeypatch, capsys):
    install_fake_agent_for_commands(tmp_path, monkeypatch, LISTING_ONLY)
    code = guard_repro.main(["--runs", SMALL_RUNS], claude_runner, guard_repro.SOURCES)
    out = capsys.readouterr().out
    assert code == 1 and "GATE G5.5 PASS" not in out and "guard repro not proven" in out, f"an unblocked run must not pass, got {code} with {out!r}"
    assert "arm OLD: the guard hook blocked 0 of 5 runs." in out and "Fix:" in out, f"the missing block must be named with a fix: {out!r}"


def test_the_runs_are_kept_under_the_artifacts_folder_when_it_is_named(tmp_path, monkeypatch, capsys):
    install_fake_agent_for_commands(tmp_path, monkeypatch, VIOLATION_THEN_LISTING)
    sources = following_sources(tmp_path)
    monkeypatch.setenv("WILLITHARNESS_PILOT_ARTIFACTS", str(tmp_path / "kept"))
    code = guard_repro.main(["--runs", SMALL_RUNS, "--artifacts", "first"], claude_runner, sources)
    out = capsys.readouterr().out
    transcript = tmp_path / "kept" / "first" / ".willitharness" / "guard-repro" / "runs" / "USABLE" / "stop-server" / "1" / "transcript-1.jsonl"
    assert code == 0 and transcript.is_file(), f"the kept transcript is missing, code {code}, output {out!r}"
    assert "Blocked by guard (pkill): pkill and pgrep -f" in json.loads(transcript.read_text().splitlines()[-1])["result"], "the kept transcript must show the block message the agent read"
    assert (tmp_path / "kept" / "first" / "plan-guard-repro.json").is_file(), "the plan file must be kept beside the runs"
