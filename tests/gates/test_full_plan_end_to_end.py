import contextlib
import io
import shutil
from dataclasses import dataclass
from pathlib import Path

import pytest

from files import plant
from willitharness import cli
from willitharness.lifecycle import PlanState, lifecycle_dir, read_reach, read_state
from willitharness.plan import read_plan
from willitharness.store import Cell, RunState, cell_counters, latest_by_run, load_records, spent
from willitharness.vocabulary import Reach

FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "pilot-guard" / "no-force-push"
PLAN_FILE = "plan.json"
WORLD_DIRECTORY = "world"
LEDGER_FILE = "runs.jsonl"
ARMS = ("N", "N2", "P")
TARGET = "ZQ-8841-lumen"
CONTROL = "purple-giraffe-91"
PROBE_SEED = 3
PROBE_RUNS = 3
TASK = "publish-fix"
EXPECTED_RUNS = 60
WORLD_NOT_VALIDATED = "world not validated; run: willitharness world check"
RUN_BEFORE_PROBE = "willitharness probe --plan <plan.json> --arm"
NO_VERDICTS = "no verdicts yet; run: willitharness analyze"
RUN_AFTER_ANALYSIS = "plan is Analyzed; a run can start only from ReachabilityChecked or Running"
ABORT_AFTER_ANALYSIS = "plan already analyzed; abort is not possible"
DECISION_LINE = f"decision {TASK} P: DeleteCandidate (reach Loaded, effect NoMeasurableEffect, guard GuardUntested)"
RUN_ARGUMENTS = ["run", PLAN_FILE, "--agent", "fake"]
AFTER_COMPLETE = ("analyze", "decide", "report", "run_after_analysis", "abort_after_analysis")


@dataclass(frozen=True)
class Step:
    code: int
    out: str
    err: str
    state: PlanState
    ledger: str


@dataclass(frozen=True)
class Flow:
    root: Path
    steps: dict


def plan_probe_arguments(directory, arm):
    return [
        "probe", "--agent", "fake", "--directory", str(directory), "--boundary", str(directory),
        "--runs", str(PROBE_RUNS), "--seed", str(PROBE_SEED), "--target-token", TARGET, "--control-token", CONTROL,
        "--plan", PLAN_FILE, "--arm", arm,
    ]


def plan_folder(root):
    return lifecycle_dir(root, read_plan(root, PLAN_FILE))


def ledger_records(root):
    return load_records(plan_folder(root))


def ledger_text(root):
    path = plan_folder(root) / LEDGER_FILE
    return path.read_text() if path.is_file() else ""


def step_of(root, arguments):
    stdout, stderr = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        code = cli.main(arguments)
    return Step(code, stdout.getvalue(), stderr.getvalue(), read_state(plan_folder(root)), ledger_text(root))


def run_until_complete(tmp_path_factory, patch):
    root = tmp_path_factory.mktemp("project")
    shutil.copytree(FIXTURE, root, dirs_exist_ok=True)
    directory = plant(tmp_path_factory.mktemp("agent-directory"), "AGENTS.md", f"Verification code: {TARGET}\n")
    patch.chdir(root)
    steps = {"start": Step(cli.EXIT_OK, "", "", read_state(plan_folder(root)), ledger_text(root))}
    steps["plan_check"] = step_of(root, ["plan", "check", PLAN_FILE])
    steps["run_before_world"] = step_of(root, RUN_ARGUMENTS)
    steps["world_check"] = step_of(root, ["world", "check", WORLD_DIRECTORY])
    steps["run_before_probe"] = step_of(root, RUN_ARGUMENTS)
    for arm in ARMS:
        steps[f"probe_{arm}"] = step_of(root, plan_probe_arguments(directory, arm))
    steps["run"] = step_of(root, RUN_ARGUMENTS)
    return root, steps


@pytest.fixture(scope="module")
def flow(tmp_path_factory):
    with pytest.MonkeyPatch.context() as patch:
        root, steps = run_until_complete(tmp_path_factory, patch)
        steps["analyze"] = step_of(root, ["analyze", PLAN_FILE])
        steps["decide"] = step_of(root, ["decide", PLAN_FILE])
        steps["report"] = step_of(root, ["report", PLAN_FILE])
        steps["run_after_analysis"] = step_of(root, RUN_ARGUMENTS)
        steps["abort_after_analysis"] = step_of(root, ["abort", PLAN_FILE])
    return Flow(root, steps)


@pytest.fixture(scope="module")
def skipped_analysis(tmp_path_factory):
    with pytest.MonkeyPatch.context() as patch:
        root, steps = run_until_complete(tmp_path_factory, patch)
        steps["report"] = step_of(root, ["report", PLAN_FILE])
    return Flow(root, steps)


def test_G6_4_a_new_plan_is_drafted_and_the_plan_check_passes(flow):
    assert flow.steps["start"].state is PlanState.DRAFTED, f"a new plan starts {PlanState.DRAFTED}, got {flow.steps['start'].state}"
    check = flow.steps["plan_check"]
    assert check.code == cli.EXIT_OK and check.out == "plan ok: pilot-guard-no-force-push (3 arms, 20 reps)\n", f"unexpected plan check {check}"


def test_G6_4_the_world_check_passes(flow):
    check = flow.steps["world_check"]
    assert check.code == cli.EXIT_OK and check.out.startswith("world: valid (hash "), f"unexpected world check {check}"


def test_G6_4_L1_a_run_before_the_world_check_is_refused_and_starts_nothing(flow):
    refused = flow.steps["run_before_world"]
    assert refused.code == cli.EXIT_DOMAIN_FAILURE and WORLD_NOT_VALIDATED in refused.err, f"run before the world check got {refused}"
    assert refused.ledger == "", "L1: a refused run must not start any run"


def test_G6_4_L1_a_run_before_every_arm_is_probed_is_refused_and_starts_nothing(flow):
    refused = flow.steps["run_before_probe"]
    assert refused.code == cli.EXIT_DOMAIN_FAILURE and RUN_BEFORE_PROBE in refused.err, f"run before probing got {refused}"
    assert refused.ledger == "", "L1: a refused run must not start any run"


def test_G6_4_the_states_follow_the_lifecycle_order_up_to_complete(flow):
    order = [flow.steps[name].state for name in ("start", "run_before_probe", "probe_N", "probe_N2", "probe_P", "run")]
    assert order == [
        PlanState.DRAFTED, PlanState.WORLD_VALIDATED, PlanState.WORLD_VALIDATED, PlanState.WORLD_VALIDATED,
        PlanState.REACHABILITY_CHECKED, PlanState.COMPLETE,
    ], f"unexpected state order {order}"


def test_G6_4_a_probe_of_every_arm_records_loaded(flow):
    for arm in ARMS:
        step = flow.steps[f"probe_{arm}"]
        assert step.code == cli.EXIT_OK and f"recorded: arm {arm} is Loaded in plan" in step.out, f"probe of arm {arm} gave {step}"
    assert read_reach(plan_folder(flow.root)) == {arm: Reach.LOADED for arm in ARMS}, "every arm must hold its probe result"


def test_G6_4_the_run_finishes_every_run_and_the_plan_is_complete(flow):
    run = flow.steps["run"]
    assert run.code == cli.EXIT_OK and run.out == "plan Complete: 60 runs, spent $0.60\n", f"unexpected run {run}"


def test_G6_4_L2_the_spend_stays_inside_the_budget(flow):
    plan = read_plan(flow.root, PLAN_FILE)
    total = spent(ledger_records(flow.root))
    assert 0 < total <= plan.budget_usd, f"L2: spent {total} against the budget {plan.budget_usd}"


def test_G6_4_L4_every_cell_has_exactly_reps_usable_runs(flow):
    plan = read_plan(flow.root, PLAN_FILE)
    records = ledger_records(flow.root)
    runs = latest_by_run(records)
    counters = cell_counters(records)
    assert len(runs) == EXPECTED_RUNS and all(run.state is RunState.RECORDED_USABLE for run in runs.values()), f"expected {EXPECTED_RUNS} usable runs, got {len(runs)}"
    assert set(counters) == {Cell(arm, TASK) for arm in ARMS}, f"unexpected cells {set(counters)}"
    assert all(item.usable == plan.reps for item in counters.values()), f"L4: usable runs per cell must equal reps {plan.reps}, got {counters}"


def test_G6_4_L9_attempts_per_cell_stay_within_reps_plus_max_retries(flow):
    plan = read_plan(flow.root, PLAN_FILE)
    counters = cell_counters(ledger_records(flow.root))
    assert all(item.attempts <= plan.reps + plan.max_retries for item in counters.values()), f"L9: attempts per cell must stay within reps plus max_retries, got {counters}"


def test_G6_4_L8_analyze_gives_an_effect_result_with_a_noise_pair_at_noise_ok(flow):
    analyze = flow.steps["analyze"]
    assert analyze.code == cli.EXIT_OK, f"analyze exited {analyze.code}: {analyze.err!r}"
    assert "verdict Inconclusive; noise NoiseOk; effect NoMeasurableEffect" in analyze.out, f"L8: the effect result needs the noise pair at NoiseOk, got {analyze.out!r}"


def test_G6_4_analyze_ends_the_plan_analyzed(flow):
    assert flow.steps["analyze"].state is PlanState.ANALYZED, f"analyze ends {PlanState.ANALYZED}, got {flow.steps['analyze'].state}"


def test_G6_4_decide_gives_a_decision_for_the_rule(flow):
    decide = flow.steps["decide"]
    assert decide.code == cli.EXIT_OK and decide.out.strip() == DECISION_LINE, f"unexpected decision {decide}"


def test_G6_4_report_holds_the_decision_the_effect_and_the_cost(flow):
    report = flow.steps["report"]
    assert report.code == cli.EXIT_OK, f"report exited {report.code}: {report.err!r}"
    assert DECISION_LINE in report.out and "## Q2 Effect" in report.out and "Total cost: $0.60." in report.out, f"the report lacks the decision, Q2 or the cost: {report.out!r}"


def test_G6_4_a_run_after_analyze_is_refused(flow):
    rerun = flow.steps["run_after_analysis"]
    assert rerun.code == cli.EXIT_DOMAIN_FAILURE and RUN_AFTER_ANALYSIS in rerun.err, f"a run after analyze got {rerun}"
    assert rerun.state is PlanState.ANALYZED, f"a refused run must keep {PlanState.ANALYZED}, got {rerun.state}"


def test_G6_4_an_abort_after_analyze_is_refused(flow):
    abort = flow.steps["abort_after_analysis"]
    assert abort.code == cli.EXIT_DOMAIN_FAILURE and ABORT_AFTER_ANALYSIS in abort.err, f"an abort after analyze got {abort}"
    assert abort.state is PlanState.ANALYZED, f"a refused abort must keep {PlanState.ANALYZED}, got {abort.state}"


def test_G6_4_L3_recorded_runs_do_not_change_after_the_run_ends(flow):
    final = flow.steps["run"].ledger
    changed = [name for name in AFTER_COMPLETE if flow.steps[name].ledger != final]
    assert changed == [], f"L3: the ledger changed after the plan completed, at {changed}"


def test_G6_4_L5_a_plan_that_skips_analysis_is_refused_by_the_report_command(skipped_analysis):
    report = skipped_analysis.steps["report"]
    assert report.code == cli.EXIT_DOMAIN_FAILURE and report.out == "" and report.err.strip() == NO_VERDICTS, f"L5: no verdict before analyze, got {report}"
    assert report.state is PlanState.COMPLETE, f"a refused report must keep {PlanState.COMPLETE}, got {report.state}"
