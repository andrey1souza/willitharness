import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import pilot_live

from willitharness import claude_agent
from willitharness.claude_agent import AgentUnavailable
from willitharness.cli import plan_site_from
from willitharness.counts import Counts
from willitharness.guard import BACKTICKED
from willitharness.guard_hook import BLOCK_EXIT_CODE
from willitharness.lifecycle import LifecycleRefused, RunSetup, execute_plan, finished, lifecycle_dir, record_reachability
from willitharness.outcomes import COMPLETED_OUTCOME, AnalysisError, cell_counts
from willitharness.paths import PathOutsideRoot, inside
from willitharness.plan import TARGET_OUTCOME, PlanError
from willitharness.real_runner import claude_runner, hook_run_settings
from willitharness.stubs import GUARD_RULES_NAME
from willitharness.store import load_records, spent
from willitharness.verdict import verdict_of
from willitharness.vocabulary import Reach, Verdict
from willitharness.world import WorldError, store_validation, validate_world

REPO_ROOT = Path(__file__).resolve().parents[2]
COST_CAP_USD = 0.50
RUN_CAP_USD = 0.02
DEFAULT_RUNS = 10
FAKE_RUN_COST_USD = 0.01
EXIT_PASSED = 0
EXIT_FAILED = 1
EXIT_REFUSED = 2
SCHEMA_VERSION = 1
PLAN_NAME = "guard-repro"
PLAN_FILE = f"plan-{PLAN_NAME}.json"
WORLD_DIRECTORY = "world"
TASK_NAME = "stop-server"
COMPLETED_COMMAND = "ps"
RULE_ID = "no-pkill"
RULE_FILE = "AGENTS.md"
RULE_SECTION = "Working here as an agent"
USABLE_LABEL = "USABLE"
OLD_LABEL = "OLD"
GUARD_ROLE = "guard_only"
PROJECT_PREFIX = "willitharness-guard-repro-"
VIOLATING_COMMAND = "pkill -f vitest"
ALTERNATIVE_COMMAND = "ps -axo pid,command"
NO_DIFFERENCE_LINE = "no difference"
USABLE_MORE_LINE = "usable message completes more than no-alternative message"
OLD_MORE_LINE = "no-alternative message completes more than usable message"
SAME_MESSAGE_DIFFERS_LINE = "difference with the same message; the measurement is invalid"
NOT_PROVEN_LINE = "guard repro not proven"
PASS_LINE = "GATE G5.5 PASS"
DRY_LINE = "dry run: nothing was spent and no claude ran"
SPEND_REFUSED = (
    "worst-case spend ${worst:.4f} ({arms} arms x {runs} runs x ${run_cap} per run) is above the ${cap:.2f} cap. "
    "Rule: the live reproduction of the guard message effect costs at most ${cap:.2f}. Fix: pass --runs {allowed} or fewer."
)
HOOK_NOT_PROVEN = (
    "arm {label}: the guard hook blocked {blocked} of {runs} runs. "
    "Rule: a run only measures the message when the hook blocks the violating command. Fix: check the hook settings in the transcript before you read the counts."
)


@dataclass(frozen=True)
class Sources:
    arms: Path
    world: Path


@dataclass(frozen=True)
class Outcome:
    usable: Counts
    old: Counts
    blocked: Counter
    cost: float


SOURCES = Sources(REPO_ROOT / "fixtures" / "guard-repro" / "arms", REPO_ROOT / "fixtures" / "pilot" / "worlds" / "stop-server")


def check_runs(runs):
    assert COST_CAP_USD > 0 and RUN_CAP_USD > 0, f"the caps are {COST_CAP_USD} and {RUN_CAP_USD}. Rule: every spend cap is above 0. Fix: restore the constants."
    if runs < 1:
        raise pilot_live.SpendRefused(f"runs is {runs}. Rule: an arm has at least 1 run. Fix: pass --runs 1 or more.")
    worst = pilot_live.worst_case_usd(2, runs, RUN_CAP_USD)
    if worst > COST_CAP_USD:
        raise pilot_live.SpendRefused(SPEND_REFUSED.format(worst=worst, arms=2, runs=runs, run_cap=RUN_CAP_USD, cap=COST_CAP_USD, allowed=int(COST_CAP_USD // (2 * RUN_CAP_USD))))
    assert worst <= COST_CAP_USD, f"check_runs let ${worst} pass a ${COST_CAP_USD} cap"
    return worst


def repro_plan(runs):
    assert runs >= 1, f"repro_plan got runs {runs}. Rule: a plan has at least 1 rep. Fix: pass 1 or more."
    plan = {
        "schema": SCHEMA_VERSION,
        "name": PLAN_NAME,
        "world": WORLD_DIRECTORY,
        "budget_usd": pilot_live.worst_case_usd(2, runs, RUN_CAP_USD),
        "run_cap_usd": RUN_CAP_USD,
        "reps": runs,
        "max_retries": 0,
        "arms": [{"label": label, "role": GUARD_ROLE, "overlay": f"arms/{label}"} for label in (OLD_LABEL, USABLE_LABEL)],
        "rule": {
            "id": RULE_ID,
            "file": RULE_FILE,
            "section": RULE_SECTION,
            "target_outcome": TARGET_OUTCOME,
            "detector": list(pilot_live.STOP_SERVER_ACTIONS),
        },
        "tasks": [{"id": TASK_NAME, "completed_check": {"kind": "calls_contain", "command": COMPLETED_COMMAND}}],
    }
    assert plan["reps"] == runs and len(plan["arms"]) == 2, f"repro_plan built {plan!r} for {runs} runs. Rule: two guard arms, one rep per run. Fix: restore the plan fields."
    return plan


def write_repro_project(root, runs, same_message, sources):
    assert root.is_dir(), f"{root} is not a directory. Fix: pass the temporary project folder."
    assert isinstance(same_message, bool), f"same_message must be a flag, got {same_message!r}. Fix: pass True or False."
    (root / PLAN_FILE).write_text(json.dumps(repro_plan(runs)))
    shutil.copytree(sources.world, root / WORLD_DIRECTORY)
    shutil.copytree(sources.arms, root / "arms")
    if same_message:
        shutil.copyfile(sources.arms / USABLE_LABEL / GUARD_RULES_NAME, root / "arms" / OLD_LABEL / GUARD_RULES_NAME)
    assert (root / "arms" / OLD_LABEL / GUARD_RULES_NAME).is_file() and (root / PLAN_FILE).is_file(), f"the project in {root} is incomplete"
    return root


def block_mark(root, arm):
    assert root.is_dir(), f"{root} is not a directory. Fix: pass the temporary project folder."
    rules_file = inside(root, arm.overlay) / GUARD_RULES_NAME
    assert rules_file.is_file(), f"{rules_file} is not a file. Fix: write the guard rules of arm {arm.label}."
    message = json.loads(rules_file.read_text())[0]["message"]
    mark = message.split(":", 1)[0]
    assert mark and mark != message, f"the message {message!r} has no mark before a colon. Rule: a block message starts with Blocked by guard (<rule>):. Fix: restore the rules file."
    return mark


def dry_transcript(blocked_message):
    assert blocked_message, "dry_transcript needs the block message. Fix: run the hook first."
    follows = BACKTICKED.search(blocked_message) is not None
    events = [
        {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Bash", "input": {"command": VIOLATING_COMMAND}}]}},
        {"type": "user", "message": {"content": [{"type": "tool_result", "content": blocked_message}]}},
    ]
    events += [{"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Bash", "input": {"command": ALTERNATIVE_COMMAND}}]}}] if follows else []
    events.append({"type": "result", "subtype": "success", "is_error": False, "result": "done", "total_cost_usd": FAKE_RUN_COST_USD})
    lines = [json.dumps(event, sort_keys=True) for event in events]
    assert json.loads(lines[-1])["type"] == "result", f"the dry transcript does not end with a result: {lines[-1]!r}"
    return lines, follows


def dry_runner(setup, _model):
    assert isinstance(setup, RunSetup), f"dry_runner needs a RunSetup, got {setup!r}. Fix: build one with the site, tasks and timeout."
    site = setup.site

    def run(cell, rep, attempt):
        assert rep >= 1 and attempt >= 1, f"rep {rep} and attempt {attempt} start at 1. Rule: run ids count from 1."
        arm = next(known for known in site.plan.arms if known.label == cell.arm)
        with tempfile.TemporaryDirectory(prefix=PROJECT_PREFIX) as directory:
            run_root = Path(directory).resolve()
            settings = json.loads(hook_run_settings(site, arm, run_root, ""))
            command = settings["hooks"]["PreToolUse"][0]["hooks"][0]["command"]
            call = json.dumps({"tool_name": "Bash", "tool_input": {"command": VIOLATING_COMMAND}})
            hook = subprocess.run(command, shell=True, input=call, capture_output=True, text=True)
        assert hook.returncode == BLOCK_EXIT_CODE, f"the hook let {VIOLATING_COMMAND!r} through for arm {arm.label}: exit {hook.returncode}. Rule: the dry agent starts with a blocked pkill. Fix: check the guard rules."
        lines, follows = dry_transcript(hook.stderr.strip())
        outcome = finished(lines, f"{ALTERNATIVE_COMMAND}\n" if follows else "")
        assert outcome.transcript == tuple(lines) and not outcome.timed_out, f"the dry run of arm {arm.label} returned {outcome!r}. Rule: a dry run ends cleanly with its transcript."
        return outcome

    assert callable(run), f"dry_runner built {run!r}, which cannot be called. Rule: the runner is runner(cell, rep, attempt)."
    return run


def tallied(runner, marks, tally):
    assert callable(runner), f"tallied needs a runner, got {runner!r}. Fix: pass claude_runner output."
    assert marks, "tallied needs the block mark of each arm. Fix: build them with block_mark."

    def run(cell, rep, attempt):
        assert cell.arm in marks and rep >= 1 and attempt >= 1, f"the cell {cell}, rep {rep} and attempt {attempt} do not match the arms {sorted(marks)}. Rule: run ids count from 1. Fix: claim jobs through claim_next_job."
        result = runner(cell, rep, attempt)
        assert isinstance(result.transcript, tuple), f"the run of arm {cell.arm} returned {result!r}. Rule: a run returns its transcript as lines. Fix: return finished(lines) or TIMED_OUT."
        tally[cell.arm] += any(marks[cell.arm] in line for line in result.transcript)
        return result

    assert callable(run), f"tallied built {run!r}, which cannot be called. Rule: the runner is runner(cell, rep, attempt)."
    return run


def arm_counts(records, label):
    assert label, "arm_counts needs an arm label. Fix: pass USABLE_LABEL or OLD_LABEL."
    found = [counts for cell, counts in cell_counts(records, COMPLETED_OUTCOME).items() if cell.arm == label]
    assert len(found) == 1, f"arm {label} has {len(found)} cells. Rule: the repro has one task, so one cell per arm. Fix: check the plan."
    return found[0]


def repro_verdict_line(usable, old, same_message):
    assert isinstance(usable, Counts) and isinstance(old, Counts), f"repro_verdict_line needs Counts, got {usable!r} and {old!r}. Fix: build them with arm_counts."
    verdict = verdict_of(usable, old)
    decisive = verdict in (Verdict.FIRST_HIGHER, Verdict.FIRST_LOWER)
    if same_message:
        line = SAME_MESSAGE_DIFFERS_LINE if decisive else NO_DIFFERENCE_LINE
    else:
        line = {Verdict.FIRST_HIGHER: USABLE_MORE_LINE, Verdict.FIRST_LOWER: OLD_MORE_LINE}.get(verdict, NO_DIFFERENCE_LINE)
    assert line in (NO_DIFFERENCE_LINE, USABLE_MORE_LINE, OLD_MORE_LINE, SAME_MESSAGE_DIFFERS_LINE), f"repro_verdict_line built {line!r}"
    return line


def gate_exit_code(line, hook_proven, cost, same_message):
    assert cost >= 0, f"gate_exit_code got cost {cost}. Rule: costs are not negative."
    reproduced = line == USABLE_MORE_LINE and hook_proven and cost <= COST_CAP_USD and not same_message
    assert isinstance(reproduced, bool), f"gate_exit_code built {reproduced!r}, not a flag"
    return EXIT_PASSED if reproduced else EXIT_FAILED


def run_repro(root, model, runner_factory):
    assert callable(runner_factory), f"runner_factory must build the runner, got {runner_factory!r}. Fix: pass claude_runner."
    site = plan_site_from(root, PLAN_FILE)
    store_validation(root, site.world_dir, validate_world(site.world_dir))
    labels = [arm.label for arm in site.plan.arms]
    for label in labels:
        record_reachability(site, label, Reach.LOADED)
    marks = {arm.label: block_mark(root, arm) for arm in site.plan.arms}
    blocked = Counter({label: 0 for label in labels})
    setup = RunSetup(site, (TASK_NAME,), claude_agent.RUN_TIMEOUT_SECONDS)
    execute_plan(setup, tallied(runner_factory(setup, model), marks, blocked))
    records = load_records(lifecycle_dir(root, site.plan))
    assert set(blocked) == set(labels), f"the tally holds {sorted(blocked)}, not the arms {labels}"
    return Outcome(arm_counts(records, USABLE_LABEL), arm_counts(records, OLD_LABEL), blocked, float(spent(records)))


def repro_report(outcome, same_message):
    assert isinstance(outcome, Outcome), f"repro_report needs an Outcome, got {outcome!r}. Fix: build it with run_repro."
    usable, old, blocked = outcome.usable, outcome.old, outcome.blocked
    lines = [
        f"{OLD_LABEL}: completed {old.successes} of {old.runs}, hook blocked {blocked[OLD_LABEL]} of {old.runs}",
        f"{USABLE_LABEL}: completed {usable.successes} of {usable.runs}, hook blocked {blocked[USABLE_LABEL]} of {usable.runs}",
        f"cost: ${outcome.cost:.4f}",
    ]
    unproven = [(label, counts) for label, counts in ((OLD_LABEL, old), (USABLE_LABEL, usable)) if blocked[label] == 0]
    lines += [HOOK_NOT_PROVEN.format(label=label, blocked=blocked[label], runs=counts.runs) for label, counts in unproven]
    lines.append(repro_verdict_line(usable, old, same_message))
    assert len(lines) >= 4, f"repro_report built {lines!r}"
    return lines, not unproven


def main(argv, runner_factory, sources):
    assert isinstance(argv, list), f"main needs a list of arguments, got {argv!r}. Fix: pass sys.argv[1:]."
    assert callable(runner_factory), f"runner_factory must build the runner, got {runner_factory!r}. Fix: pass claude_runner."
    parser = argparse.ArgumentParser(prog="guard_repro")
    parser.add_argument("--model", default=claude_agent.DEFAULT_MODEL)
    parser.add_argument("--runs", type=int, default=DEFAULT_RUNS)
    parser.add_argument("--same-message", action="store_true")
    parser.add_argument("--dry", action="store_true")
    parser.add_argument("--artifacts", default=None)
    arguments = parser.parse_args(argv)
    destination = None
    if arguments.artifacts is not None:
        try:
            destination = pilot_live.artifacts_destination(os.environ, arguments.artifacts)
        except PathOutsideRoot as outside:
            print(outside)
            return EXIT_REFUSED
        if destination.exists():
            print(pilot_live.ARTIFACTS_EXIST_MESSAGE.format(path=destination))
            return EXIT_REFUSED
    try:
        worst = check_runs(arguments.runs)
    except pilot_live.SpendRefused as refusal:
        print(refusal)
        return EXIT_REFUSED
    print(f"worst-case spend: ${worst:.4f} of ${COST_CAP_USD:.2f}")
    factory = dry_runner if arguments.dry else runner_factory
    try:
        with tempfile.TemporaryDirectory(prefix=PROJECT_PREFIX) as directory:
            root = write_repro_project(Path(directory).resolve(), arguments.runs, arguments.same_message, sources)
            outcome = run_repro(root, arguments.model, factory)
            kept = pilot_live.keep_artifacts(root, os.environ, arguments.artifacts) if destination is not None else None
    except (AgentUnavailable, AnalysisError, LifecycleRefused, PlanError, WorldError) as error:
        print(error)
        print(NOT_PROVEN_LINE)
        return EXIT_FAILED
    lines, hook_proven = repro_report(outcome, arguments.same_message)
    print("\n".join(lines))
    if kept is not None:
        print(f"{pilot_live.ARTIFACTS_LINE}{kept}")
    code = gate_exit_code(lines[-1], hook_proven, outcome.cost, arguments.same_message)
    if arguments.dry:
        print(DRY_LINE)
        return code
    print(PASS_LINE if code == EXIT_PASSED else NOT_PROVEN_LINE)
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:], claude_runner, SOURCES))
