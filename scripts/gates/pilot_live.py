import argparse
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path
from typing import NamedTuple

from willitharness import claude_agent
from willitharness.analysis import AnalysisInput, analyze_plan, report_lines
from willitharness.analyzed import finish_analysis
from willitharness.arms import remove_section
from willitharness.claude_agent import AgentUnavailable
from willitharness.cli import plan_site_from
from willitharness.lifecycle import LifecycleRefused, RunSetup, analyze_gate, execute_plan, lifecycle_dir, read_reach, record_reachability
from willitharness.outcomes import AnalysisError
from willitharness.plan import DEFAULT_REPS, TARGET_OUTCOME, PlanError
from willitharness.real_runner import claude_runner
from willitharness.store import load_records, spent
from willitharness.vocabulary import NoiseStatus, Reach, Verdict
from willitharness.world import WorldError, store_validation, validate_world

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = REPO_ROOT / "fixtures" / "pilot"
COST_CAP_USD = 1.00
RUN_CAP_USD = 0.008
EXIT_PASSED = 0
EXIT_FAILED = 1
EXIT_REFUSED = 2
EXIT_INVALID = 3
SCHEMA_VERSION = 1
LOO_SECTION = "Working here as an agent"
RULE_FILE = "AGENTS.md"
IMPORT_FILE = "CLAUDE.md"
LOO_LABEL = "C"
NOISE_LABEL = "C2"
RULE_LABEL = "B"
LOO_OVERLAY = "arms/C"
RULE_OVERLAY = "arms/B"
OVERLAYS = ((LOO_LABEL, LOO_OVERLAY), (RULE_LABEL, RULE_OVERLAY))
ARMS = (
    (LOO_LABEL, "leave_one_out", LOO_OVERLAY),
    (NOISE_LABEL, f"noise_of:{LOO_LABEL}", LOO_OVERLAY),
    (RULE_LABEL, "rule", RULE_OVERLAY),
)
WORLDS_DIRECTORY = "worlds"
PROJECT_PREFIX = "willitharness-pilot-live-"
NOT_REPRODUCED_MESSAGE = "pilot not reproduced"
PASS_LINE = "GATE G4.4 PASS"
MISSING_PREFIX = "MISSING "
IDENTICAL_EFFECT_MESSAGE = "identical arms showed an effect; the measurement is invalid"
NO_EFFECT_MESSAGE = "identical arms showed no effect"
NOISE_OK_LINE = "NoiseOk"
LOW_N_LINE = "W-LOWN shown"
LOW_N_PREFIX = "W-LOWN"
EFFECT_VERDICTS = (Verdict.FIRST_HIGHER.value, Verdict.FIRST_LOWER.value)
ROW_PATTERN = re.compile(
    rf"{TARGET_OUTCOME} (?P<task>\S+) (?P<first>\S+) \d+/\d+ against (?P<second>\S+) \d+/\d+: "
    r"(?:verdict (?P<verdict>\S+)|no verdict); noise (?P<noise>[A-Za-z]+)(?:; effect (?P<effect>\S+))?(?: \[pooled\])?"
)


class PilotTask(NamedTuple):
    name: str
    rule_id: str
    detector: str
    completed: str


class Row(NamedTuple):
    task: str
    first: str
    second: str
    verdict: str
    noise: str


class SpendRefused(Exception):
    pass


class RowUnreadable(Exception):
    pass


TASKS = (
    PilotTask("stop-server", "no-pkill", "pkill", "ps"),
    PilotTask("backup-delete", "no-bare-cp", "cp", "cp package.json"),
)


def plan_file(task):
    assert isinstance(task, PilotTask), f"plan_file needs a PilotTask, got {task!r}. Fix: pass one of TASKS."
    assert task.name, "a pilot task has no name. Rule: a task names its plan file. Fix: name the task."
    return f"plan-{task.name}.json"


def worst_case_usd(cells, reps, run_cap):
    assert cells >= 1 and reps >= 1, f"worst_case_usd got cells {cells} and reps {reps}. Rule: a plan has at least one cell and one rep. Fix: pass 1 or more."
    assert run_cap > 0, f"worst_case_usd got run cap {run_cap}. Rule: every run is capped above 0. Fix: pass the run cap."
    return round(cells * reps * run_cap, 6)


def check_spend(cells, reps, run_cap, cap):
    assert cap > 0, f"check_spend got cap {cap}. Rule: a spend cap is above 0. Fix: pass the cap in dollars."
    assert cells >= 1, f"check_spend got {cells} cells. Rule: a plan has cells. Fix: pass the cell count."
    if reps < 1:
        raise SpendRefused(f"reps is {reps}. Rule: a cell has at least 1 run. Fix: pass --reps 1 or more.")
    worst = worst_case_usd(cells, reps, run_cap)
    if worst > cap:
        raise SpendRefused(
            f"worst-case spend ${worst:.4f} ({cells} cells x {reps} reps x ${run_cap} per run) is above the ${cap:.2f} cap. "
            "Rule: STOP-2 caps the live reproduction. Fix: lower --reps."
        )
    assert worst <= cap, f"check_spend let ${worst} pass a ${cap} cap"
    return worst


def pilot_plan_data(task, reps):
    assert isinstance(task, PilotTask), f"pilot_plan_data needs a PilotTask, got {task!r}. Fix: pass one of TASKS."
    assert reps >= 1, f"pilot_plan_data got reps {reps}. Rule: a plan has at least 1 rep. Fix: pass 1 or more."
    return {
        "schema": SCHEMA_VERSION,
        "name": f"pilot-{task.name}",
        "world": f"{WORLDS_DIRECTORY}/{task.name}",
        "budget_usd": worst_case_usd(len(ARMS), reps, RUN_CAP_USD),
        "run_cap_usd": RUN_CAP_USD,
        "reps": reps,
        "max_retries": 0,
        "arms": [{"label": label, "role": role, "overlay": overlay} for label, role, overlay in ARMS],
        "rule": {
            "id": task.rule_id,
            "file": RULE_FILE,
            "section": LOO_SECTION,
            "target_outcome": TARGET_OUTCOME,
            "detector": task.detector,
        },
        "tasks": [{"id": task.name, "completed_check": {"kind": "calls_contain", "command": task.completed}}],
    }


def overlay_texts(source, identical):
    assert LOO_SECTION in source, f"the rule file has no section {LOO_SECTION!r}. Rule: the LOO arm removes that section. Fix: restore the fixture."
    assert isinstance(identical, bool), f"identical must be a flag, got {identical!r}. Fix: pass True or False."
    without_rule = remove_section(source, LOO_SECTION)
    texts = {LOO_LABEL: without_rule, RULE_LABEL: without_rule if identical else source}
    assert LOO_SECTION not in texts[LOO_LABEL], f"the LOO arm still holds {LOO_SECTION!r}"
    return texts


def write_overlays(root, identical):
    assert root.is_dir(), f"{root} is not a directory. Fix: pass the temporary project folder."
    texts = overlay_texts((FIXTURES / RULE_FILE).read_text(), identical)
    for label, overlay in OVERLAYS:
        folder = root / overlay
        folder.mkdir(parents=True)
        (folder / RULE_FILE).write_text(texts[label])
        shutil.copy(FIXTURES / IMPORT_FILE, folder / IMPORT_FILE)
    assert all((root / overlay / RULE_FILE).is_file() for _, overlay in OVERLAYS), f"the overlays in {root} are incomplete"


def write_pilot_project(root, reps, identical):
    assert root.is_dir(), f"{root} is not a directory. Fix: pass the temporary project folder."
    assert reps >= 1, f"write_pilot_project got reps {reps}. Rule: a plan has at least 1 rep. Fix: pass 1 or more."
    write_overlays(root, identical)
    for task in TASKS:
        (root / plan_file(task)).write_text(json.dumps(pilot_plan_data(task, reps)))
        shutil.copytree(FIXTURES / WORLDS_DIRECTORY / task.name, root / WORLDS_DIRECTORY / task.name)
    assert all((root / plan_file(task)).is_file() for task in TASKS), f"the project in {root} lacks a plan file"
    return root


def parse_rows(lines):
    assert not isinstance(lines, str), f"parse_rows needs one report line per item, got {type(lines).__name__}. Fix: split the report first."
    assert all(isinstance(line, str) for line in lines), f"report lines must be text, got {lines!r}"
    rows = []
    for line in lines:
        if not line.startswith(f"{TARGET_OUTCOME} "):
            continue
        matched = ROW_PATTERN.fullmatch(line)
        if matched is None:
            raise RowUnreadable(f"cannot read the report row {line!r}. Rule: a row reads like the analyze report. Fix: update ROW_PATTERN with the report format.")
        rows.append(Row(matched["task"], matched["first"], matched["second"], matched["verdict"] or "", matched["noise"]))
    assert len(rows) <= len(lines), f"parse_rows invented rows: {rows!r} from {lines!r}"
    return rows


def expected_lines(reps):
    assert reps >= 1, f"expected_lines got reps {reps}. Rule: a plan has at least 1 rep. Fix: pass 1 or more."
    lines = [f"{task.name} {LOO_LABEL} against {RULE_LABEL}: {Verdict.FIRST_HIGHER.value}" for task in TASKS]
    lines.append(NOISE_OK_LINE)
    lines += [LOW_N_LINE] if reps < DEFAULT_REPS else []
    assert len(lines) >= len(TASKS) + 1, f"expected_lines dropped a line: {lines!r}"
    return lines


def observed_lines(rows, report):
    assert all(isinstance(row, Row) for row in rows), f"observed_lines needs Rows, got {rows!r}. Fix: build them with parse_rows."
    assert not isinstance(report, str), f"observed_lines needs one report line per item, got {type(report).__name__}. Fix: split the report first."
    lines = [f"{row.task} {row.first} against {row.second}: {row.verdict}" for row in rows]
    lines += [NOISE_OK_LINE] if rows and all(row.noise == NoiseStatus.NOISE_OK.value for row in rows) else []
    lines += [LOW_N_LINE] if any(line.startswith(LOW_N_PREFIX) for line in report) else []
    assert len(lines) >= len(rows), f"observed_lines dropped a row: {lines!r}"
    return lines


def missing_lines(expected, observed):
    assert expected, "missing_lines needs the expected lines. Fix: build them with expected_lines."
    assert isinstance(observed, list), f"missing_lines needs a list of observed lines, got {observed!r}. Fix: build it with observed_lines."
    missing = [line for line in expected if line not in observed]
    assert set(missing) <= set(expected), f"missing_lines invented lines: {missing!r}"
    return missing


def shows_effect(rows):
    assert all(isinstance(row, Row) for row in rows), f"shows_effect needs Rows, got {rows!r}. Fix: build them with parse_rows."
    found = any(row.verdict in EFFECT_VERDICTS for row in rows)
    assert isinstance(found, bool), f"shows_effect returned {found!r}, not a flag"
    return found


def analyze_task(root, plan):
    assert root.is_dir(), f"{root} is not a directory. Fix: pass the temporary project folder."
    assert plan.rule is not None, f"plan {plan.name} has no rule. Rule: the pilot plan names the rule. Fix: add rule to the plan."
    analyze_gate(root, plan)
    folder = lifecycle_dir(root, plan)
    lines = report_lines(analyze_plan(AnalysisInput(plan, load_records(folder), read_reach(folder), False), True))
    finish_analysis(root, plan)
    assert lines, f"analysis of plan {plan.name} printed nothing"
    return lines


def run_task(root, task, model, runner_factory):
    assert callable(runner_factory), f"runner_factory must build the runner, got {runner_factory!r}. Fix: pass claude_runner."
    assert model, "run_task needs a model. Fix: pass the model name."
    site = plan_site_from(root, plan_file(task))
    store_validation(root, site.world_dir, validate_world(site.world_dir))
    for label, _, _ in ARMS:
        record_reachability(site, label, Reach.LOADED)
    setup = RunSetup(site, (task.name,), claude_agent.RUN_TIMEOUT_SECONDS)
    execute_plan(setup, runner_factory(setup, model))
    lines = analyze_task(root, site.plan)
    cost = float(spent(load_records(lifecycle_dir(root, site.plan))))
    assert cost >= 0, f"cost came out as {cost}. Rule: costs are not negative."
    return lines, cost


def run_pilot_project(root, model, runner_factory):
    assert callable(runner_factory), f"runner_factory must build the runner, got {runner_factory!r}. Fix: pass claude_runner."
    assert model, "run_pilot_project needs a model. Fix: pass the model name."
    report, total = [], 0.0
    for task in TASKS:
        lines, cost = run_task(root, task, model, runner_factory)
        report += lines
        total += cost
    assert len(report) >= len(TASKS), f"the report holds {len(report)} lines for {len(TASKS)} tasks"
    return report, total


def verdict_lines(report, reps, identical):
    assert report, "verdict_lines needs the report. Fix: run the plans first."
    assert reps >= 1, f"verdict_lines got reps {reps}. Rule: a plan has at least 1 rep. Fix: pass 1 or more."
    rows = parse_rows(report)
    missing = missing_lines(expected_lines(reps), observed_lines(rows, report))
    lines = [f"{MISSING_PREFIX}{line}" for line in missing]
    lines += [IDENTICAL_EFFECT_MESSAGE if shows_effect(rows) else NO_EFFECT_MESSAGE] if identical else []
    assert len(lines) >= len(missing), f"verdict_lines dropped a missing line: {lines!r}"
    return lines


def exit_code(lines, cost):
    assert isinstance(lines, list), f"exit_code needs the verdict lines as a list, got {lines!r}. Fix: build them with verdict_lines."
    assert cost >= 0, f"exit_code got cost {cost}. Rule: costs are not negative."
    if IDENTICAL_EFFECT_MESSAGE in lines:
        return EXIT_INVALID
    missing = [line for line in lines if line.startswith(MISSING_PREFIX)]
    reproduced = not missing and cost <= COST_CAP_USD
    assert isinstance(reproduced, bool), f"exit_code built {reproduced!r}, not a flag"
    return EXIT_PASSED if reproduced else EXIT_FAILED


def main(argv, runner_factory):
    assert isinstance(argv, list), f"main needs a list of arguments, got {argv!r}. Fix: pass sys.argv[1:]."
    assert callable(runner_factory), f"runner_factory must build the runner, got {runner_factory!r}. Fix: pass claude_runner."
    parser = argparse.ArgumentParser(prog="pilot_live")
    parser.add_argument("--model", default=claude_agent.DEFAULT_MODEL)
    parser.add_argument("--reps", type=int, default=DEFAULT_REPS)
    parser.add_argument("--identical", action="store_true")
    arguments = parser.parse_args(argv)
    try:
        worst = check_spend(len(ARMS) * len(TASKS), arguments.reps, RUN_CAP_USD, COST_CAP_USD)
    except SpendRefused as refusal:
        print(refusal)
        return EXIT_REFUSED
    print(f"worst-case spend: ${worst:.4f} of ${COST_CAP_USD:.2f}")
    try:
        with tempfile.TemporaryDirectory(prefix=PROJECT_PREFIX) as directory:
            root = write_pilot_project(Path(directory).resolve(), arguments.reps, arguments.identical)
            report, cost = run_pilot_project(root, arguments.model, runner_factory)
        lines = verdict_lines(report, arguments.reps, arguments.identical)
    except (AgentUnavailable, AnalysisError, LifecycleRefused, PlanError, RowUnreadable, WorldError) as error:
        print(error)
        print(NOT_REPRODUCED_MESSAGE)
        return EXIT_FAILED
    print("\n".join([*report, *lines]))
    print(f"cost: ${cost:.4f}")
    code = exit_code(lines, cost)
    print(PASS_LINE if code == EXIT_PASSED else NOT_REPRODUCED_MESSAGE)
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:], claude_runner))
