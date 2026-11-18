import math
import os
import sys
import threading
import time
from dataclasses import replace

import pytest

from agent_site import ONE_RUN, TWO_RUNS, prepare_project_with_fake_agent, run_one
from cli_runner import run_cli
from fake_claude import ESCAPE_TARGET_FILE, PID_FILE, SECRET_VARIABLE, report_of
from files import write_tree
from lifecycle_site import TASK_NAME, TASK_PROMPT, run_setup, stored_final_runs, validate_site

from willitharness.lifecycle import TIMED_OUT, PlanState, RunSetup, abort_plan, execute_plan, lifecycle_dir, read_state, start_running
from willitharness.plan import PlanError
from willitharness.real_runner import claude_runner
from willitharness.store import Cell, RunState

pytestmark = pytest.mark.skipif(sys.platform != "darwin", reason="the real runner uses macOS sandbox-exec")
CELL = Cell("A", TASK_NAME)
HUNG_TIMEOUT_SECONDS = 1.0
ABORT_TIMEOUT_SECONDS = 30.0
WAIT_SECONDS = 10.0
POLL_SECONDS = 0.02


def wait_for(path):
    deadline = time.monotonic() + WAIT_SECONDS
    while not path.exists() and time.monotonic() < deadline:
        time.sleep(POLL_SECONDS)
    assert path.exists(), f"{path} did not appear within {WAIT_SECONDS} seconds"
    return path


def assert_process_gone(pid):
    deadline = time.monotonic() + WAIT_SECONDS
    alive = True
    while alive and time.monotonic() < deadline:
        try:
            os.kill(pid, 0)
            time.sleep(POLL_SECONDS)
        except ProcessLookupError:
            alive = False
    assert not alive, f"process {pid} is still alive after the run ended. Rule: a killed run leaves no agent behind."


def test_the_agent_gets_the_plan_flags_and_the_run_cap_as_its_budget(tmp_path, monkeypatch):
    site = prepare_project_with_fake_agent(tmp_path, monkeypatch, ONE_RUN, "ok")
    arguments = report_of(run_one(site).transcript)["arguments"]
    assert arguments[:2] == ["-p", TASK_PROMPT.strip()], f"unexpected start {arguments[:2]}"
    assert arguments[arguments.index("--max-budget-usd") + 1] == "0.02", f"budget flag wrong in {arguments}"
    assert arguments[arguments.index("--setting-sources") + 1] == "project,local", f"setting sources wrong in {arguments}"


def test_the_workspace_holds_the_project_files_and_the_arm_overlay_only(tmp_path, monkeypatch):
    site = prepare_project_with_fake_agent(tmp_path, monkeypatch, ONE_RUN, "ok")
    write_tree(site.world_dir, {"package.json": "{}"})
    validate_site(site)
    report = report_of(run_one(site).transcript)
    assert report["files"] == ["fake-behavior.txt", "fake-escape-target.txt", "package.json", "rule.txt"], f"unexpected workspace files {report['files']}"
    assert not report["cwd"].startswith(str(site.root)), f"the workspace {report['cwd']} sits under the project {site.root}. Rule: a project instruction file must not reach the agent."


def test_the_agent_environment_drops_unlisted_variables_and_gets_a_private_temp_folder(tmp_path, monkeypatch):
    site = prepare_project_with_fake_agent(tmp_path, monkeypatch, ONE_RUN, "ok")
    report = report_of(run_one(site).transcript)
    assert SECRET_VARIABLE not in report["environment"], f"{SECRET_VARIABLE} leaked into {report['environment']}"
    assert report["tmpdir"].endswith("/tmp") and "willitharness-run-" in report["tmpdir"], f"unexpected TMPDIR {report['tmpdir']}"
    assert report["claude_tmpdir"] == report["tmpdir"], f"claude must write its command output inside the private scratch folder, got CLAUDE_CODE_TMPDIR {report['claude_tmpdir']} and TMPDIR {report['tmpdir']}"


def test_the_agent_can_write_in_its_workspace_and_nowhere_else(tmp_path, monkeypatch):
    site = prepare_project_with_fake_agent(tmp_path, monkeypatch, ONE_RUN, "ok")
    report = report_of(run_one(site).transcript)
    assert report["wrote_inside"] is True, f"the agent could not write in its workspace, report {report}"
    assert report["wrote_outside"] is False and not (tmp_path / "outside" / "escaped.txt").exists(), f"the agent wrote outside its workspace, report {report}"


def test_the_workspace_is_removed_after_the_run(tmp_path, monkeypatch):
    site = prepare_project_with_fake_agent(tmp_path, monkeypatch, ONE_RUN, "ok")
    cwd = report_of(run_one(site).transcript)["cwd"]
    assert not os.path.exists(cwd), f"the workspace {cwd} survived the run"
    assert not (site.world_dir / "inside.txt").exists(), "a run wrote into the plan's own world"


def test_G3_10_a_hung_agent_is_killed_at_the_timeout_and_charged_run_cap(tmp_path, monkeypatch):
    site = prepare_project_with_fake_agent(tmp_path, monkeypatch, ONE_RUN, "hang")
    setup = RunSetup(site, (TASK_NAME,), HUNG_TIMEOUT_SECONDS)
    outcome = execute_plan(setup, claude_runner(setup, "haiku"))
    (run,) = stored_final_runs(site)
    assert outcome is PlanState.COMPLETE, f"the plan must end Complete, got {outcome}"
    assert run.state is RunState.RECORDED_UNUSABLE and math.isclose(run.cost_usd, 0.02), f"a timeout is unusable at RUN_CAP, got {run}"
    assert_process_gone(int((tmp_path / "config" / PID_FILE).read_text()))


def test_G3_10_a_run_that_outlives_the_timeout_ends_as_timed_out_even_while_the_plan_keeps_running(tmp_path, monkeypatch):
    site = prepare_project_with_fake_agent(tmp_path, monkeypatch, ONE_RUN, "hang")
    setup = RunSetup(site, (TASK_NAME,), HUNG_TIMEOUT_SECONDS)
    start_running(site)
    result = claude_runner(setup, "haiku")(CELL, 1, 1)
    assert result == TIMED_OUT, f"a run past the timeout must end as TIMED_OUT, got {result}"
    assert_process_gone(int((tmp_path / "config" / PID_FILE).read_text()))


def test_G3_10_an_agent_that_reports_a_cost_above_run_cap_is_recorded_unusable_at_run_cap(tmp_path, monkeypatch):
    site = prepare_project_with_fake_agent(tmp_path, monkeypatch, ONE_RUN, "overspend")
    setup = run_setup(site)
    execute_plan(setup, claude_runner(setup, "haiku"))
    (run,) = stored_final_runs(site)
    assert run.state is RunState.RECORDED_UNUSABLE and math.isclose(run.cost_usd, 0.02), f"an over-cap run is unusable at RUN_CAP, got {run}"
    assert run.usable == {"attempted_violation": False, "completed": False}, f"an over-cap run counts for nothing, got {run.usable}"


def test_a_plan_of_normal_runs_ends_complete_with_usable_records_at_their_cost(tmp_path, monkeypatch):
    site = prepare_project_with_fake_agent(tmp_path, monkeypatch, TWO_RUNS, "ok")
    setup = run_setup(site)
    outcome = execute_plan(setup, claude_runner(setup, "haiku"))
    runs = stored_final_runs(site)
    assert outcome is PlanState.COMPLETE and len(runs) == 2, f"two runs and Complete expected, got {outcome} and {runs}"
    assert all(run.state is RunState.RECORDED_USABLE and math.isclose(run.cost_usd, 0.01) for run in runs), f"every run costs 0.01 and is usable, got {runs}"


def test_G3_11_abort_kills_the_agent_that_is_in_flight(tmp_path, monkeypatch):
    site = prepare_project_with_fake_agent(tmp_path, monkeypatch, ONE_RUN, "hang")
    setup = RunSetup(site, (TASK_NAME,), ABORT_TIMEOUT_SECONDS)
    outcomes = []
    worker = threading.Thread(target=lambda: outcomes.append(execute_plan(setup, claude_runner(setup, "haiku"))))
    worker.start()
    pid = int(wait_for(tmp_path / "config" / PID_FILE).read_text())
    abort_plan(site.root, site.plan)
    worker.join(WAIT_SECONDS)
    (run,) = stored_final_runs(site)
    assert not worker.is_alive() and outcomes == [PlanState.ABORTED], f"the plan must end Aborted quickly, got {outcomes}"
    assert run.state is RunState.RECORDED_UNUSABLE and math.isclose(run.cost_usd, 0.02), f"an aborted run is unusable at RUN_CAP, got {run}"
    stored_state = read_state(lifecycle_dir(site.root, site.plan))
    assert stored_state is PlanState.ABORTED, f"the stored state is {stored_state}, expected Aborted. Rule: abort ends the plan in Aborted."
    assert_process_gone(pid)


def test_an_arm_overlay_that_is_not_a_directory_is_refused_before_any_run(tmp_path, monkeypatch):
    site = prepare_project_with_fake_agent(tmp_path, monkeypatch, ONE_RUN, "ok")
    for name in ("rule.txt", "fake-behavior.txt", ESCAPE_TARGET_FILE):
        (site.root / "A.md" / name).unlink()
    (site.root / "A.md").rmdir()
    with pytest.raises(PlanError) as raised:
        claude_runner(run_setup(site), "haiku")
    assert "is not a directory" in str(raised.value) and "Fix:" in str(raised.value), f"unexpected message {str(raised.value)!r}"
    assert not stored_final_runs(site), f"a refused plan must not start a run, found {stored_final_runs(site)}"


def test_an_arm_on_the_system_prompt_channel_is_refused(tmp_path, monkeypatch):
    site = prepare_project_with_fake_agent(tmp_path, monkeypatch, ONE_RUN, "ok")
    arm = replace(site.plan.arms[0], channel="system_prompt")
    refused = replace(site, plan=replace(site.plan, arms=(arm,)))
    with pytest.raises(PlanError) as raised:
        claude_runner(run_setup(refused), "haiku")
    assert "channel system_prompt" in str(raised.value) and "T64" in str(raised.value) and "Fix:" in str(raised.value), f"unexpected message {str(raised.value)!r}"


def test_the_run_command_runs_the_claude_agent_and_prints_the_spend(tmp_path, monkeypatch, capsys):
    prepare_project_with_fake_agent(tmp_path, monkeypatch, TWO_RUNS, "ok")
    monkeypatch.chdir(tmp_path / "project")
    code, out, err = run_cli(capsys, ["run", "plan.json", "--agent", "claude"])
    assert code == 0 and "plan Complete: 4 runs, spent $0.02\n" == out, f"unexpected result {code}, {out!r}, {err!r}"


def test_the_run_command_exits_one_when_an_overlay_is_missing(tmp_path, monkeypatch, capsys):
    site = prepare_project_with_fake_agent(tmp_path, monkeypatch, ONE_RUN, "ok")
    for name in ("rule.txt", "fake-behavior.txt", ESCAPE_TARGET_FILE):
        (site.root / "A.md" / name).unlink()
    (site.root / "A.md").rmdir()
    monkeypatch.chdir(site.root)
    code, out, err = run_cli(capsys, ["run", "plan.json", "--agent", "claude"])
    assert code == 1 and "is not a directory" in err, f"unexpected result {code}, {out!r}, {err!r}"
