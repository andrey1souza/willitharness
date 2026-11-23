import sys

import guard_repro
import pilot_live
import pytest
from test_guard_repro_live_path import VIOLATION_THEN_LISTING, following_sources, install_fake_agent_for_commands

from willitharness.artifacts import RUNS_DIR
from willitharness.detectors import transcript_contains
from willitharness.real_runner import claude_runner

pytestmark = pytest.mark.skipif(sys.platform != "darwin", reason="the real runner uses macOS sandbox-exec")

SMALL_RUNS = "3"
KEPT_NAME = "kept"
TRANSCRIPT_PATTERN = "transcript-*.jsonl"
STORED_ARMS = ("OLD", "USABLE")


def kept_transcripts(tmp_path, monkeypatch, capsys, same_message):
    install_fake_agent_for_commands(tmp_path, monkeypatch, VIOLATION_THEN_LISTING)
    monkeypatch.setenv(pilot_live.ARTIFACTS_ROOT_VARIABLE, str(tmp_path / "artifacts"))
    arguments = ["--runs", SMALL_RUNS, "--artifacts", KEPT_NAME, *(["--same-message"] if same_message else [])]
    guard_repro.main(arguments, claude_runner, following_sources(tmp_path))
    capsys.readouterr()
    runs = tmp_path / "artifacts" / KEPT_NAME / pilot_live.STORE_DIRECTORY / guard_repro.PLAN_NAME / RUNS_DIR
    found = {arm: sorted((runs / arm).rglob(TRANSCRIPT_PATTERN)) for arm in STORED_ARMS}
    assert all(len(paths) == int(SMALL_RUNS) for paths in found.values()), f"each arm stores {SMALL_RUNS} transcripts, got {found}. Rule: a run stores its transcript. Fix: check the runner."
    return {arm: [path.read_text().splitlines() for path in paths] for arm, paths in found.items()}


def completed_in(transcripts):
    return [transcript_contains(guard_repro.COMPLETED_TEXTS, lines) for lines in transcripts]


def test_G5_8_a_stored_transcript_completes_only_when_a_kill_with_both_pids_ran_and_was_not_blocked(tmp_path, monkeypatch, capsys):
    stored = kept_transcripts(tmp_path, monkeypatch, capsys, same_message=False)
    assert completed_in(stored["USABLE"]) == [True] * int(SMALL_RUNS), "the usable message leads to a kill with both PIDs"
    assert completed_in(stored["OLD"]) == [False] * int(SMALL_RUNS), "the old message leads to no kill"


def test_G5_8_a_blocked_kill_in_a_stored_transcript_does_not_complete_the_run(tmp_path, monkeypatch, capsys):
    stored = kept_transcripts(tmp_path, monkeypatch, capsys, same_message=False)
    blocked_kill = [line.replace(guard_repro.VIOLATING_COMMAND, guard_repro.COMPLETING_COMMAND) for line in stored["OLD"][0]]
    assert guard_repro.COMPLETING_COMMAND in "".join(blocked_kill), f"the bad input must hold {guard_repro.COMPLETING_COMMAND!r}: {blocked_kill}"
    assert completed_in([blocked_kill]) == [False], f"a kill that the guard blocked is not completion: {blocked_kill}"
