import contextlib
import io
import json
import os
import shutil
import stat
import subprocess
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

import pytest
from cli_runner import run_cli
from three_arm_site import transcript_lines

import pilot_live
from willitharness import cli
from willitharness.artifacts import RUNS_DIR, TRANSCRIPT_NAME
from willitharness.component_arms import ARM_COMPONENT, ARM_NOISE, ARM_NOTHING, ARM_PROMPT
from willitharness.lifecycle import PlanState, lifecycle_dir, read_state
from willitharness.load_report import split_skill
from willitharness.plan import DEFAULT_REPS, read_plan

REPOSITORY = Path(__file__).resolve().parents[2]
CASE = REPOSITORY / "fixtures" / "three-arm-pkill"
PLAN_DIRECTORY = CASE / "plan"
PILOT_WORLD = REPOSITORY / "fixtures" / "pilot" / "worlds" / "stop-server"
PILOT_RULES = REPOSITORY / "fixtures" / "pilot" / "AGENTS.md"
SCRIPT = REPOSITORY / "scripts" / "gates" / "three_arm_live.sh"
SCRIPT_NAME = "scripts/gates/three_arm_live.sh"
PLAN_FILE = "plan.json"
WORLD_DIRECTORY = "world"
SKILL_NAME = "stop-processes"
TASK = "stop-server"
PLAN_NAME = "three-arm-pkill"
EVERY_ARM = (ARM_NOTHING, ARM_NOISE, ARM_PROMPT, ARM_COMPONENT)
PROBE_RUNS = 3
PROBE_RUN_CAP = Decimal("0.01")
PROBE_SEED = 3
TARGET = "ZQ-8841-lumen"
CONTROL = "purple-giraffe-91"
MAX_WORST_CASE_USD = Decimal("1.00")
FIRED_RUNS = 4
PLAIN_RUNS = 4
FIRED_TURNS = 4
PLAIN_TURNS = 3
EXIT_OK = 0
EXIT_REFUSED = 2
MODEL = "haiku"
RULE_MARKER = "Rule:"
FIX_MARKER = "Fix:"
FAKE_CLAUDE = "#!/bin/sh\ntouch \"$CLAUDE_STARTED_MARKER\"\nexit 1\n"


@dataclass(frozen=True)
class Flow:
    root: Path
    codes: dict
    outputs: dict


def plan_numbers():
    plan = json.loads((PLAN_DIRECTORY / PLAN_FILE).read_text())
    tasks = [line for line in (PLAN_DIRECTORY / WORLD_DIRECTORY / "tasks.txt").read_text().splitlines() if line.strip()]
    arms, reps, cap = len(plan["arms"]), plan.get("reps", DEFAULT_REPS), Decimal(str(plan["run_cap_usd"]))
    runs = arms * reps * len(tasks) * cap
    probes = arms * PROBE_RUNS * PROBE_RUN_CAP
    return arms, reps, len(tasks), cap, runs, probes


def files_of(folder):
    assert folder.is_dir(), f"{folder} is not a folder. Fix: restore the fixture."
    return {path.relative_to(folder).as_posix(): path.read_bytes() for path in sorted(folder.rglob("*")) if path.is_file()}


def copy_case(destination):
    shutil.copytree(PLAN_DIRECTORY, destination / "plan")
    shutil.copytree(CASE / "probe", destination / "probe")
    for arm in json.loads((destination / "plan" / PLAN_FILE).read_text())["arms"]:
        (destination / "plan" / arm["overlay"]).mkdir(parents=True, exist_ok=True)
    return destination


def cli_step(arguments):
    stdout, stderr = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        code = cli.main(arguments)
    return code, stdout.getvalue(), stderr.getvalue()


def fake_probe_arguments(probe, arm):
    return [
        "probe", "--agent", "fake", "--directory", str(probe), "--boundary", str(probe), "--runs", str(PROBE_RUNS),
        "--seed", str(PROBE_SEED), "--target-token", TARGET, "--control-token", CONTROL, "--plan", PLAN_FILE, "--arm", arm,
    ]


def run_pipeline(tmp_path_factory, fired_runs, plain_runs):
    root = copy_case(tmp_path_factory.mktemp("three-arm"))
    plan_root = root / "plan"
    codes, outputs = {}, {}
    with pytest.MonkeyPatch.context() as patch:
        patch.chdir(plan_root)
        steps = [("plan_check", ["plan", "check", PLAN_FILE]), ("world_check", ["world", "check", WORLD_DIRECTORY])]
        steps += [(f"probe_{arm}", fake_probe_arguments(root / "probe", arm)) for arm in EVERY_ARM]
        steps += [("run", ["run", PLAN_FILE, "--agent", "fake"])]
        for name, arguments in steps:
            codes[name], outputs[name], _ = cli_step(arguments)
        folder = lifecycle_dir(plan_root, read_plan(plan_root, PLAN_FILE))
        for rep in range(1, fired_runs + plain_runs + 1):
            path = folder / RUNS_DIR / ARM_COMPONENT / TASK / str(rep) / TRANSCRIPT_NAME.format(attempt=rep)
            path.parent.mkdir(parents=True, exist_ok=True)
            did_fire = rep <= fired_runs
            path.write_text(transcript_lines(did_fire, FIRED_TURNS if did_fire else PLAIN_TURNS))
        for name in ("analyze", "decide", "report"):
            codes[name], outputs[name], errors = cli_step([name, PLAN_FILE])
            outputs[f"{name}_errors"] = errors
        outputs["state"] = read_state(folder)
    return Flow(plan_root, codes, outputs)


@pytest.fixture(scope="module")
def plain(tmp_path_factory):
    return run_pipeline(tmp_path_factory, 0, 0)


@pytest.fixture(scope="module")
def fired(tmp_path_factory):
    return run_pipeline(tmp_path_factory, FIRED_RUNS, PLAIN_RUNS)


def script_result(arguments, tmp_path, extra_environment=None):
    started = tmp_path / "claude-started"
    stub_directory = tmp_path / "stub-bin"
    stub_directory.mkdir(exist_ok=True)
    stub = stub_directory / "claude"
    stub.write_text(FAKE_CLAUDE)
    stub.chmod(stub.stat().st_mode | stat.S_IEXEC)
    environment = {
        **os.environ,
        "PATH": f"{stub_directory}{os.pathsep}{os.environ['PATH']}",
        "CLAUDE_STARTED_MARKER": str(started),
        "WILLITHARNESS_PILOT_ARTIFACTS": str(tmp_path / "artifacts"),
        **(extra_environment or {}),
    }
    done = subprocess.run([str(SCRIPT), *arguments], capture_output=True, text=True, env=environment, cwd=tmp_path)
    return done, started


def assert_rule_and_fix(done):
    assert done.returncode == EXIT_REFUSED, f"expected exit {EXIT_REFUSED}, got {done.returncode}: {done.stderr!r}"
    assert RULE_MARKER in done.stderr and done.stderr.strip().split(FIX_MARKER)[-1].strip(), f"the refusal has no Rule and Fix: {done.stderr!r}"


def pilot_rule_text():
    bullet = next(line for line in PILOT_RULES.read_text().splitlines() if line.startswith("- Never use `pkill`"))
    return bullet.removeprefix("- ")


def skill_body():
    return split_skill((CASE / ".claude" / "skills" / SKILL_NAME / "SKILL.md").read_text())[1]


def arm_prompt_text():
    return (PLAN_DIRECTORY / "arms" / ARM_PROMPT / "system-prompt.txt").read_text()


def checked_in_detector():
    return json.loads((CASE / "detector.json").read_text())


def checked_in_plan():
    return json.loads((PLAN_DIRECTORY / PLAN_FILE).read_text())


def test_the_skill_body_is_the_pilot_rule_text_and_arm_p_holds_the_same_text():
    rule_text = pilot_rule_text()
    assert skill_body() == rule_text, f"the skill body is {skill_body()!r}, not the pilot rule {rule_text!r}. Fix: copy the pilot bullet."
    assert arm_prompt_text() == rule_text, f"arm P holds {arm_prompt_text()!r}, not the pilot rule {rule_text!r}. Fix: build the plan again."


def test_the_detector_and_the_world_are_the_pilot_ones():
    assert checked_in_detector() == list(pilot_live.STOP_SERVER_ACTIONS), f"detector {checked_in_detector()!r} differs from the pilot detector {pilot_live.STOP_SERVER_ACTIONS!r}. Fix: copy the pilot detector."
    checked_in, pilot = files_of(PLAN_DIRECTORY / WORLD_DIRECTORY), files_of(PILOT_WORLD)
    assert checked_in == pilot, f"the world files {sorted(checked_in)!r} differ from the pilot world {sorted(pilot)!r}. Fix: copy the pilot world again."


def test_the_checked_in_plan_and_overlays_equal_the_build_plan_output(tmp_path, capsys):
    plan = checked_in_plan()
    arguments = [
        "build-plan", "--skill", SKILL_NAME, "--project", str(CASE), "--detector", str(CASE / "detector.json"), "--out", str(tmp_path / "out"),
        "--name", PLAN_NAME, "--budget-usd", str(plan["budget_usd"]), "--run-cap-usd", str(plan["run_cap_usd"]), "--task-file", str(CASE / "tasks.json"),
    ]
    code, _, error = run_cli(capsys, arguments)
    assert code == EXIT_OK, error
    built = json.loads((tmp_path / "out" / PLAN_FILE).read_text())
    assert [task["id"] for task in built["tasks"]] == [TASK], f"the built plan has tasks {built['tasks']!r}, not one task {TASK!r}. Fix: keep the one task in tasks.json."
    assert plan == built, f"the checked-in plan differs from the build-plan output: {plan!r} against {built!r}. Fix: build the plan again."
    built_overlays, checked_in_overlays = files_of(tmp_path / "out" / "arms"), files_of(PLAN_DIRECTORY / "arms")
    assert built_overlays and checked_in_overlays == built_overlays, f"checked-in overlays {sorted(checked_in_overlays)!r} differ from built {sorted(built_overlays)!r}. Fix: build the plan again."


def test_the_plan_has_arms_n_n2_p_and_c_and_the_checks_pass(tmp_path, monkeypatch, capsys):
    root = copy_case(tmp_path) / "plan"
    monkeypatch.chdir(root)
    labels = tuple(arm.label for arm in read_plan(root, PLAN_FILE).arms)
    assert labels == EVERY_ARM, f"plan arms are {labels!r}, not {EVERY_ARM!r}. Fix: build arms N, N2, P and C."
    codes = (run_cli(capsys, ["plan", "check", PLAN_FILE])[0], run_cli(capsys, ["world", "check", WORLD_DIRECTORY])[0])
    assert codes == (EXIT_OK, EXIT_OK), f"plan check and world check exited {codes!r}, not {(EXIT_OK, EXIT_OK)!r}. Fix: read their messages."


def test_the_worst_case_cost_of_runs_and_probes_stays_within_one_dollar():
    arms, reps, tasks, cap, runs, probes = plan_numbers()
    assert (arms, reps, tasks) == (4, DEFAULT_REPS, 1), f"the plan has {arms} arms, {reps} reps and {tasks} tasks"
    assert runs + probes <= MAX_WORST_CASE_USD, f"worst case {arms} x {reps} x {tasks} x {cap} = {runs} plus probes {probes} is above {MAX_WORST_CASE_USD}. Fix: lower reps or the cap."


def test_the_fake_agent_pipeline_reaches_the_verdict_through_the_real_cli(plain):
    assert plain.outputs["state"] is PlanState.ANALYZED, f"the plan ended {plain.outputs['state']}"
    steps = ("plan_check", "world_check", "run", "analyze", "decide", "report")
    codes = [plain.codes[name] for name in steps]
    assert codes == [EXIT_OK] * len(steps), f"exit codes {codes!r} for {steps!r}, not all {EXIT_OK}. Fix: read {plain.outputs}"
    for arm in EVERY_ARM:
        assert f"recorded: arm {arm} is Loaded in plan {PLAN_NAME}" in plain.outputs[f"probe_{arm}"], f"probe of arm {arm} gave {plain.outputs[f'probe_{arm}']!r}"
    assert "plan Complete: 80 runs" in plain.outputs["run"], f"unexpected run output {plain.outputs['run']!r}"


def test_decide_and_report_print_the_three_arm_verdict(plain):
    counts = "(arm C 0 of 20 runs, arm P 0 of 20 runs, arm N 0 of 20 runs)"
    assert f"decision {TASK} C: insurance, keep" in plain.outputs["decide"] and counts in plain.outputs["decide"], f"decide printed {plain.outputs['decide']!r}"
    report = plain.outputs["report"]
    assert "## Three-arm verdict" in report and f"- {TASK}: arm C 0 of 20 runs, arm P 0 of 20 runs, arm N 0 of 20 runs. Verdict: insurance, keep" in report, f"report printed {report!r}"
    assert f"decision {TASK} C: insurance, keep" in report, "the report holds the decision line"


def test_fake_transcripts_without_a_skill_call_leave_the_trigger_not_measured(plain):
    assert "Trigger not measured. No usable run of arm C has a stored transcript." in plain.outputs["report"], f"report printed {plain.outputs['report']!r}"


def test_planted_transcripts_with_a_skill_call_give_a_measured_trigger_rate(fired):
    report = fired.outputs["report"]
    measured = FIRED_RUNS + PLAIN_RUNS
    rate = FIRED_RUNS * 100 // measured
    assert f"Trigger rate of arm C: {FIRED_RUNS} of {measured} runs ({rate}%)." in report, f"report printed {report!r}"
    assert f"arm C violated in 0 of {FIRED_RUNS} runs that fired" in report, f"report printed {report!r}"
    assert "Trigger not measured" not in report, "a measured trigger must not also print not measured"


def test_the_script_prints_the_live_command_and_the_worst_case_and_starts_nothing(tmp_path):
    arms, reps, tasks, cap, runs, probes = plan_numbers()
    done, started = script_result([], tmp_path)
    assert done.returncode == EXIT_OK, done.stderr
    expected = [
        f"worst-case run cost: {arms} arms x {reps} reps x {tasks} tasks x ${cap} cap = ${runs:.2f}",
        f"worst-case total: ${runs + probes:.2f}",
        f"live command: {SCRIPT_NAME} --live --reps {reps} --cap-usd {runs + probes:.2f} --model {MODEL} --artifacts NAME",
    ]
    assert all(line in done.stdout.splitlines() for line in expected), f"the script printed {done.stdout!r}, not {expected!r}"
    assert not started.exists(), "the print mode started claude"


def test_the_script_refuses_a_run_count_above_the_plan(tmp_path):
    reps = plan_numbers()[1]
    done, started = script_result(["--dry", "--reps", str(reps + 1)], tmp_path)
    assert_rule_and_fix(done)
    assert f"is above the {reps} runs per arm of the plan" in done.stderr, f"unexpected refusal {done.stderr!r}"
    assert not started.exists() and "plan check" not in done.stdout, f"a refused run count started a run: {done.stdout!r}. Fix: refuse before any step."


def test_a_live_run_without_a_cap_or_with_a_low_cap_is_refused_before_any_spend(tmp_path):
    for arguments, reason in ((["--live", "--artifacts", "x"], "no cost cap given"), (["--live", "--cap-usd", "0.5", "--artifacts", "x"], "is below the worst-case total")):
        done, started = script_result(arguments, tmp_path)
        assert_rule_and_fix(done)
        assert reason in done.stderr, f"expected {reason!r} in {done.stderr!r}. Fix: name that reason in the refusal."
        assert not started.exists(), f"claude started for {arguments!r}"


def test_the_plan_completion_check_is_a_kill_with_both_stub_pids():
    check = checked_in_plan()["tasks"][0]["completed_check"]
    assert check == {"kind": "transcript_contains", "texts": ["kill", "999991", "999992"]}, f"the completed check is {check!r}. Rule: completion means kill with both stub PIDs, as in the pilot. Fix: restore the check in tasks.json."


def script_text():
    assert SCRIPT.is_file(), f"{SCRIPT} is not a file. Fix: restore the script."
    return SCRIPT.read_text()


def test_the_live_script_copies_the_artifacts_before_it_deletes_the_work_folder_on_every_exit():
    text = script_text()
    handler = text[text.index("finish()"):text.index("work=")]
    assert handler.index("keep_artifacts") < handler.index('rm -rf "$work"'), f"the exit handler must copy the artifacts before it deletes the work folder, got {handler!r}. Rule: a paid run keeps its transcripts even when a later step fails. Fix: call keep_artifacts first in finish."
    assert "trap finish EXIT" in text, "the script must run finish on every exit. Rule: a failing step must not lose the transcripts of a paid run. Fix: trap finish EXIT."
    assert "willitharness report \"$PLAN_FILE\"\n\nif" not in text, "the artifact copy must not sit after the last step, where a failing step skips it"


def test_the_script_dry_mode_runs_the_whole_pipeline_with_the_fake_agent(tmp_path):
    done, started = script_result(["--dry"], tmp_path)
    assert done.returncode == EXIT_OK, done.stderr
    assert f"decision {TASK} C: insurance, keep" in done.stdout and "Trigger not measured" in done.stdout and "plan Complete: 80 runs" in done.stdout, f"the dry run printed {done.stdout!r}"
    assert not started.exists() and not (PLAN_DIRECTORY / ".willitharness").exists(), "the dry run started claude or wrote into the fixture"
