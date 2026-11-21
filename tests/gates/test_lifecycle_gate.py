import json
import math
import threading

import pytest

from cli_runner import run_cli
from lifecycle_site import SiteSpec, TASK_NAME, edit_world, make_site, ready_site, reach_every_arm, run_setup, success_transcript, validate_site

from willitharness.lifecycle import Job, PlanState, begin_run, execute_plan, lifecycle_dir, record_reachability, start_running, write_state
from willitharness.store import UNKNOWN_WORLD, Cell, latest_by_run, load_records, spent
from willitharness.vocabulary import Reach

TIGHT = SiteSpec(arm_count=1, budget_usd=0.05, run_cap_usd=0.02, reps=100, max_retries=0)
ROOMY = SiteSpec(arm_count=2, budget_usd=1.0, run_cap_usd=0.02, reps=2, max_retries=0)
FOUR_ARMS = SiteSpec(arm_count=4, budget_usd=1.0, run_cap_usd=0.02, reps=1, max_retries=0)
PARALLEL = SiteSpec(arm_count=1, budget_usd=0.10, run_cap_usd=0.02, reps=20, max_retries=0)
RUN_ARGUMENTS = ["run", "plan.json", "--agent", "fake"]


def state_file(site):
    return json.loads((lifecycle_dir(site.root, site.plan) / "state.json").read_text())["state"]


def gate_final_runs(site):
    return tuple(latest_by_run(load_records(lifecycle_dir(site.root, site.plan))).values())


def test_G3_6_the_run_command_stops_at_the_budget_with_exit_code_four(tmp_path, monkeypatch, capsys):
    site = ready_site(tmp_path, TIGHT)
    monkeypatch.chdir(tmp_path)
    code, out, err = run_cli(capsys, RUN_ARGUMENTS)
    assert code == 4, f"the budget stop exits 4, got {code}; out {out!r}; err {err!r}"
    assert len(gate_final_runs(site)) == 4 and math.isclose(spent(gate_final_runs(site)), 0.04), f"4 runs and 0.04 spent, got {gate_final_runs(site)}"
    assert state_file(site) == "BudgetStopped", f"got {state_file(site)}"
    assert "spent $0.04" in out, f"the run prints the spend, got {out!r}"


def test_G3_7_the_run_command_ends_complete_with_exit_zero_when_the_budget_allows_every_run(tmp_path, monkeypatch, capsys):
    site = ready_site(tmp_path, ROOMY)
    monkeypatch.chdir(tmp_path)
    code, out, err = run_cli(capsys, RUN_ARGUMENTS)
    assert code == 0, f"got {code}; out {out!r}; err {err!r}"
    assert len(gate_final_runs(site)) == 4 and state_file(site) == "Complete", f"4 runs and Complete, got {len(gate_final_runs(site))} and {state_file(site)}"


def test_G3_7_the_run_command_refuses_a_plan_with_a_missing_arm_and_names_it(tmp_path, monkeypatch, capsys):
    site = make_site(tmp_path, FOUR_ARMS)
    validate_site(site)
    for label in "ABC":
        record_reachability(site, label, Reach.LOADED)
    monkeypatch.chdir(tmp_path)
    code, out, err = run_cli(capsys, RUN_ARGUMENTS)
    assert code == 1 and "arm D" in err, f"exit 1 naming arm D, got {code} and {err!r}"
    assert gate_final_runs(site) == (), "no run may start"


def test_G3_7_the_run_command_refuses_a_world_never_validated(tmp_path, monkeypatch, capsys):
    site = make_site(tmp_path, TIGHT)
    monkeypatch.chdir(tmp_path)
    code, out, err = run_cli(capsys, RUN_ARGUMENTS)
    assert code == 1, f"got {code}"
    assert "world not validated; run: willitharness world check" in err, f"got {err!r}"
    assert gate_final_runs(site) == (), "no run may start"


def test_G3_9_the_run_command_refuses_a_changed_world_and_starts_nothing(tmp_path, monkeypatch, capsys):
    site = ready_site(tmp_path, TIGHT)
    edit_world(site)
    monkeypatch.chdir(tmp_path)
    code, out, err = run_cli(capsys, RUN_ARGUMENTS)
    assert code == 1, f"got {code}"
    assert "world changed since validation; run: willitharness world check" in err, f"got {err!r}"
    assert gate_final_runs(site) == (), "no new run may start"


def test_G3_9_a_plan_returns_to_drafted_after_a_world_change_and_the_state_file_shows_it(tmp_path):
    site = ready_site(tmp_path, TIGHT)
    assert state_file(site) == "ReachabilityChecked", f"got {state_file(site)}"
    edit_world(site)
    reach_every_arm(site, Reach.LOADED)
    assert state_file(site) == "Drafted", f"got {state_file(site)}"


def test_G3_11_abort_then_analyze_exits_one_with_no_verdict(tmp_path, monkeypatch, capsys):
    site = ready_site(tmp_path, TIGHT)
    monkeypatch.chdir(tmp_path)
    run_cli(capsys, RUN_ARGUMENTS)
    abort_code, abort_out, abort_err = run_cli(capsys, ["abort", "plan.json"])
    analyze_code, analyze_out, analyze_err = run_cli(capsys, ["analyze", "plan.json"])
    assert abort_code == 0 and state_file(site) == "Aborted", f"abort gave {abort_code} {abort_err!r}; state {state_file(site)}"
    assert analyze_code == 1 and "plan aborted; no verdict" in analyze_err, f"analyze gave {analyze_code} {analyze_err!r}"


def test_G3_11_the_abort_command_charges_run_cap_for_each_run_in_flight(tmp_path, monkeypatch, capsys):
    site = ready_site(tmp_path, ROOMY)
    start_running(site)
    for rep in (1, 2, 3):
        begin_run(lifecycle_dir(site.root, site.plan), Job(Cell("A", TASK_NAME), rep, rep), UNKNOWN_WORLD)
    monkeypatch.chdir(tmp_path)
    code, out, err = run_cli(capsys, ["abort", "plan.json"])
    assert code == 0, f"got {code} {err!r}"
    assert math.isclose(spent(gate_final_runs(site)), 0.06), f"3 runs at RUN_CAP 0.02 are 0.06, got {spent(gate_final_runs(site))}"


def test_G3_11_abort_after_analyze_exits_one_and_the_plan_stays_analyzed(tmp_path, monkeypatch, capsys):
    site = ready_site(tmp_path, ROOMY)
    monkeypatch.chdir(tmp_path)
    run_cli(capsys, RUN_ARGUMENTS)
    write_state(lifecycle_dir(site.root, site.plan), PlanState.ANALYZED)
    code, out, err = run_cli(capsys, ["abort", "plan.json"])
    assert code == 1 and "plan already analyzed; abort is not possible" in err, f"got {code} {err!r}"
    assert state_file(site) == "Analyzed", f"got {state_file(site)}"


def test_G3_7_analyze_on_a_running_plan_exits_one_and_on_a_complete_plan_without_a_comparison_exits_one_too(tmp_path, monkeypatch, capsys):
    site = ready_site(tmp_path, ROOMY)
    start_running(site)
    monkeypatch.chdir(tmp_path)
    running_code, running_out, running_err = run_cli(capsys, ["analyze", "plan.json"])
    run_cli(capsys, RUN_ARGUMENTS)
    complete_code, complete_out, complete_err = run_cli(capsys, ["analyze", "plan.json"])
    assert running_code == 1 and "plan still running; analyze after Complete or BudgetStopped" in running_err, f"got {running_code} {running_err!r}"
    assert complete_code == 1 and "no leave_one_out arm or no rule arm to compare" in complete_err, f"got {complete_code} {complete_err!r}"


def test_G3_6_four_parallel_runners_never_let_spent_plus_reserved_pass_the_budget(tmp_path):
    site = ready_site(tmp_path, PARALLEL)
    folder = lifecycle_dir(site.root, site.plan)
    violations = []

    def watching_runner(cell, rep, attempt):
        runs = tuple(latest_by_run(load_records(folder)).values())
        in_flight = sum(1 for run in runs if run.state.value == "Started")
        committed = spent(runs) + 0.02 * in_flight
        if committed > 0.10 + 1e-9:
            violations.append(committed)
        return success_transcript(0.01)

    outcome = execute_plan(run_setup(site), watching_runner)
    assert violations == [], f"spent plus reserved passed 0.10: {violations}"
    assert outcome.value == "BudgetStopped" and spent(gate_final_runs(site)) <= 0.10, f"got {outcome} and {spent(gate_final_runs(site))}"


def test_G3_7_a_runner_that_never_returns_is_recorded_unusable_at_run_cap_through_the_cli_path(tmp_path):
    site = ready_site(tmp_path, SiteSpec(1, 1.0, 0.02, 1, 0))
    release = threading.Event()
    setup = run_setup(site)
    outcome = execute_plan(type(setup)(setup.site, setup.tasks, 0.05), lambda cell, rep, attempt: release.wait() and success_transcript(0.01))
    release.set()
    assert outcome.value == "Complete", f"got {outcome}"
    assert [(run.state.value, run.cost_usd) for run in gate_final_runs(site)] == [("RecordedUnusable", 0.02)], f"got {gate_final_runs(site)}"


def raise_budget(site, budget):
    data = json.loads((site.root / "plan.json").read_text())
    data["budget_usd"] = budget
    (site.root / "plan.json").write_text(json.dumps(data))
    assert json.loads((site.root / "plan.json").read_text())["budget_usd"] == budget, "the plan file must keep the new budget"


def test_L10_run_on_a_budget_stopped_plan_with_a_raised_budget_resumes_it(tmp_path, monkeypatch, capsys):
    site = ready_site(tmp_path, TIGHT)
    monkeypatch.chdir(tmp_path)
    run_cli(capsys, RUN_ARGUMENTS)
    raise_budget(site, 0.10)
    code, out, err = run_cli(capsys, RUN_ARGUMENTS)
    assert code == 4 and len(gate_final_runs(site)) == 9, f"expected exit 4 and 9 runs, got {code} and {len(gate_final_runs(site))}; err {err!r}"
    assert "spent $0.09" in out and state_file(site) == "BudgetStopped", f"got {out!r} and {state_file(site)}"


def test_L11_run_on_a_budget_stopped_plan_with_the_same_budget_exits_one_and_changes_nothing(tmp_path, monkeypatch, capsys):
    site = ready_site(tmp_path, TIGHT)
    monkeypatch.chdir(tmp_path)
    run_cli(capsys, RUN_ARGUMENTS)
    before = gate_final_runs(site)
    code, out, err = run_cli(capsys, RUN_ARGUMENTS)
    assert code == 1 and "Rule: L11" in err and "Fix:" in err, f"got {code} {err!r}"
    assert gate_final_runs(site) == before and state_file(site) == "BudgetStopped", f"got {state_file(site)}"


def test_L10_run_on_a_complete_plan_exits_one_and_says_there_is_nothing_to_resume(tmp_path, monkeypatch, capsys):
    site = ready_site(tmp_path, ROOMY)
    monkeypatch.chdir(tmp_path)
    run_cli(capsys, RUN_ARGUMENTS)
    code, out, err = run_cli(capsys, RUN_ARGUMENTS)
    assert code == 1 and "nothing to resume" in err, f"got {code} {err!r}"
    assert state_file(site) == "Complete", f"got {state_file(site)}"


@pytest.mark.parametrize("spec, expected", [(TIGHT, "BudgetStopped"), (ROOMY, "Complete")])
def test_L5_an_analyze_that_cannot_produce_a_verdict_leaves_a_finished_plan_in_its_state(tmp_path, monkeypatch, capsys, spec, expected):
    site = ready_site(tmp_path, spec)
    monkeypatch.chdir(tmp_path)
    run_cli(capsys, RUN_ARGUMENTS)
    code, out, err = run_cli(capsys, ["analyze", "plan.json"])
    assert code == 1 and "no leave_one_out arm or no rule arm to compare" in err, f"got {code} {err!r}"
    assert state_file(site) == expected and "resume" not in err, f"analyze moved the plan to {state_file(site)}, expected {expected}; err {err!r}"
