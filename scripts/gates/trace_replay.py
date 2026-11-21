import json
import shutil
import tempfile
from dataclasses import dataclass, replace
from decimal import Decimal
from pathlib import Path

from files import plant
from lifecycle_site import TASK_NAME, WORLD_NAME, SiteSpec, costing_runner, make_site, run_setup, success_transcript, validate_site
from willitharness.analyzed import finish_analysis
from willitharness.lifecycle import (
    TIMED_OUT,
    Job,
    LifecycleRefused,
    PlanState,
    RunContext,
    abort_plan,
    analyze_gate,
    claim_next_job,
    conclude,
    finish_job,
    finished,
    ledger_from_records,
    lifecycle_dir,
    money_spent,
    read_reach,
    read_resume,
    record_reachability,
    refresh_state,
    resume_plan,
    start_running,
    world_is_validated,
)
from willitharness.store import Cell, RunState, latest_by_run, load_records
from willitharness.vocabulary import Reach

CENTS_PER_DOLLAR = Decimal(100)
UNIT_COST_USD = 0.01
MODEL_ARMS = ("LOO", "Rule", "Repeat")
ARM_LABELS = dict(zip(MODEL_ARMS, "ABC"))
MODEL_TASK = "t1"
NO_REACH = "none"
REACH_OF = {"Loaded": Reach.LOADED, "Masked": Reach.MASKED, "Unknown": Reach.UNKNOWN}
REPORTED = "Reported"
WORLD_EDIT_FILE = "note.txt"
PROBE_DIRECTORY = "probe"
UNUSABLE_SUBTYPE = "error_during_execution"
OUTCOMES = ("usable", "unusable", "timeout")
FINAL_PLAN_STATES = (PlanState.ANALYZED.value, REPORTED)
CODE_ACTIONS = ("ValidateWorld", "WorldChanged", "CheckReach", "EnterReachChecked", "BeginRunning", "Start", "Record", "Timeout", "FinishComplete", "FinishBudgetStopped", "Resume", "Analyze", "Abort")
UNREPLAYED_ACTIONS = ("AssessNoise", "EmitEffect", "Report", "Terminated")
ABORT_IN_FLIGHT = "Abort with a run in flight"
OBSERVED_KEYS = ("state", "worldOk", "budget", "reach", "cells")
PROBES_PER_STATE = 4
STATE_VALUES = tuple(item.value for item in PlanState)


@dataclass(frozen=True)
class Divergence:
    scenario: str
    seed: int
    walk: int
    step: int
    action: str
    reason: str
    model: dict
    code: dict


@dataclass(frozen=True)
class ReplayResult:
    walks: int
    steps: int
    probes: int
    divergence: Divergence | None


@dataclass
class Rig:
    site: object
    edits: int
    arms: tuple


def describe(divergence):
    assert isinstance(divergence, Divergence), f"describe needs a Divergence, got {divergence!r}. Fix: pass the divergence the replay returned."
    assert divergence.step >= 0 and divergence.walk >= 0, f"step {divergence.step} and walk {divergence.walk} count from 0. Fix: build the divergence with indexes."
    return (
        f"divergence in {divergence.scenario}, seed {divergence.seed}, walk {divergence.walk}, step {divergence.step} ({divergence.action}): {divergence.reason}\n"
        f"  model: {json.dumps(divergence.model, sort_keys=True)}\n"
        f"  code:  {json.dumps(divergence.code, sort_keys=True)}"
    )


def dollars(units):
    assert isinstance(units, int) and units >= 0, f"money units are whole numbers of 0 or more, got {units!r}. Fix: pass the model's integer."
    amount = float(Decimal(units) / CENTS_PER_DOLLAR)
    assert amount >= 0, f"{units} units became {amount} dollars. Rule: money is never negative."
    return amount


def units(amount):
    assert amount >= 0, f"a cost cannot be negative, got {amount}. Rule: money only goes out. Fix: pass 0 or more."
    scaled = Decimal(str(amount)) * CENTS_PER_DOLLAR
    assert scaled == scaled.to_integral_value(), f"{amount} dollars is not a whole number of model units. Rule: the model counts whole units. Fix: use costs in units."
    return int(scaled)


def coverage_errors(walks):
    assert walks, "coverage_errors got no walks. Rule: a replay needs walks. Fix: generate them with TLC."
    assert all(walk for walk in walks), f"a walk is empty among {len(walks)} walks. Rule: every walk holds at least the initial state. Fix: regenerate the walks."
    taken = {state["act"][0] for walk in walks for state in walk}
    aborted_in_flight = any(after["act"][0] == "Abort" and any(cell[0] > cell[1] + cell[2] for cell in before["cells"].values()) for walk in walks for before, after in zip(walk, walk[1:]))
    missing = [name for name in CODE_ACTIONS if name not in taken] + ([] if aborted_in_flight else [ABORT_IN_FLIGHT])
    return [f"no walk took {name}. Rule: a replay that never takes an action proves nothing about it. Fix: walk more or deeper" for name in missing]


def cell_key(arm):
    assert arm in ARM_LABELS, f"{arm!r} is not a model arm {MODEL_ARMS}. Fix: use LOO, Rule or Repeat."
    key = f"{arm}/{MODEL_TASK}"
    assert key.endswith(MODEL_TASK), f"cell key {key} lost its task"
    return key


def build_rig(root, constants, arms):
    assert arms and set(arms) <= set(MODEL_ARMS), f"the plan arms {arms!r} must be a non-empty subset of {MODEL_ARMS}. Fix: read them from the walk."
    spec = SiteSpec(len(arms), dollars(constants["Budget"]), dollars(constants["RunCap"]), constants["Reps"], constants["MaxRetries"])
    site = make_site(root, spec)
    rig = Rig(site, 0, tuple(arms))
    assert [arm.label for arm in site.plan.arms] == [ARM_LABELS[arm] for arm in arms], f"the plan arms differ from {arms}. Rule: model arms map to labels in order."
    return rig


def cell_row(runs, label):
    assert label in ARM_LABELS.values(), f"{label!r} is not an arm label. Fix: use A, B or C."
    mine = [run for run in runs if run.arm == label]
    spent = sum(units(run.cost_usd) for run in mine if run.state is not RunState.STARTED)
    row = [len(mine), sum(run.state is RunState.RECORDED_USABLE for run in mine), sum(run.state is RunState.RECORDED_UNUSABLE for run in mine), spent]
    assert row[1] + row[2] <= row[0], f"cell {label} has more ended runs than runs: {row}"
    return row


def observe(rig):
    site = rig.site
    state = refresh_state(site)
    folder = lifecycle_dir(site.root, site.plan)
    runs = tuple(latest_by_run(load_records(folder)).values())
    stored = read_resume(folder)
    recorded = read_reach(folder)
    labels = {arm: ARM_LABELS[arm] for arm in rig.arms}
    cells = {cell_key(arm): cell_row(runs, label) for arm, label in labels.items()}
    reach = {arm: recorded[label].value if label in recorded else NO_REACH for arm, label in labels.items()}
    budget = units(stored.budget_usd if stored else site.plan.budget_usd)
    observed = {"state": state.value, "worldOk": world_is_validated(site), "budget": budget, "reach": reach, "cells": cells}
    assert tuple(observed) == OBSERVED_KEYS, f"observe returned keys {tuple(observed)}, expected {OBSERVED_KEYS}"
    assert units(money_spent(load_records(folder))) == sum(cell[3] for cell in cells.values()), f"the spent money differs from the sum over cells {cells}"
    return observed


def expected_of(state):
    assert set(OBSERVED_KEYS) <= set(state), f"a model state lacks {set(OBSERVED_KEYS) - set(state)}. Fix: print every observed key in TraceWalk.tla."
    plan_state = PlanState.ANALYZED.value if state["state"] == REPORTED else state["state"]
    reached = all(state["reach"][arm] != NO_REACH for arm in state["arms"])
    if plan_state == PlanState.WORLD_VALIDATED.value and reached:
        plan_state = PlanState.REACHABILITY_CHECKED.value
    reach = {arm: state["reach"][arm] for arm in state["arms"]}
    expected = {"state": plan_state, "worldOk": state["worldOk"], "budget": state["budget"], "reach": reach, "cells": state["cells"]}
    assert tuple(expected) == OBSERVED_KEYS, f"expected_of returned keys {tuple(expected)}, expected {OBSERVED_KEYS}"
    return expected


def narrow_context(site, arm):
    assert arm in ARM_LABELS, f"{arm!r} is not a model arm. Fix: use LOO, Rule or Repeat."
    narrow = replace(site, plan=replace(site.plan, arms=tuple(known for known in site.plan.arms if known.label == ARM_LABELS[arm])))
    assert len(narrow.plan.arms) == 1, f"the plan has no arm {ARM_LABELS[arm]}. Rule: a model cell belongs to a plan arm."
    records = load_records(lifecycle_dir(site.root, site.plan))
    return RunContext(run_setup(narrow), costing_runner(UNIT_COST_USD), ledger_from_records(narrow.plan, records))


def full_context(site):
    assert site.plan.arms, f"the plan {site.plan.name} has no arms. Rule: a plan needs arms. Fix: build the site with make_site."
    records = load_records(lifecycle_dir(site.root, site.plan))
    context = RunContext(run_setup(site), costing_runner(UNIT_COST_USD), ledger_from_records(site.plan, records))
    assert context.ledger.budget > 0, f"the ledger of plan {site.plan.name} has budget {context.ledger.budget}. Rule: a plan has a budget above 0."
    return context


def result_of(outcome, cost):
    assert outcome in OUTCOMES, f"unknown outcome {outcome!r}. Fix: use one of {OUTCOMES}."
    assert cost >= 0, f"a cost cannot be negative, got {cost}. Fix: pass 0 or more."
    if outcome == "timeout":
        return TIMED_OUT
    if outcome == "usable":
        return success_transcript(cost)
    event = {"type": "result", "subtype": UNUSABLE_SUBTYPE, "is_error": True, "total_cost_usd": cost}
    return finished((json.dumps(event, sort_keys=True),))


def running_job(site, arm):
    assert arm in ARM_LABELS, f"{arm!r} is not a model arm. Fix: use LOO, Rule or Repeat."
    assert site.plan.arms, f"the plan {site.plan.name} has no arms. Fix: build the site with make_site."
    started = [run for run in latest_by_run(load_records(lifecycle_dir(site.root, site.plan))).values() if run.arm == ARM_LABELS[arm] and run.state is RunState.STARTED]
    if not started:
        raise LifecycleRefused(f"the model has a run in flight in {arm} but the code has none. Rule: a model Record or Timeout ends a started run")
    oldest = min(started, key=lambda run: (run.rep, run.attempt))
    job = Job(Cell(oldest.arm, oldest.task), oldest.rep, oldest.attempt)
    assert job.attempt >= 1 and job.rep >= 1, f"{job} counts from 1. Rule: run ids count from 1."
    return job


def finish_action(rig, name, args):
    assert name in ("Record", "Timeout"), f"{name} does not end a run. Fix: route Record and Timeout here."
    arm = args[0]
    outcome, cost = (args[2], args[3]) if name == "Record" else ("timeout", 0)
    ended = finish_job(full_context(rig.site), running_job(rig.site, arm), result_of(outcome, dollars(cost)))
    assert ended is not None, f"the run of {arm} was already ended. Rule: the model ends each started run once."
    return rig


def resume_action(rig, budget):
    assert budget >= 0, f"a model budget is 0 or more, got {budget}. Fix: pass the model's integer."
    site = rig.site
    raised = replace(site, plan=replace(site.plan, budget_usd=dollars(budget)))
    rig.site = raised
    resume_plan(raised)
    assert raised.plan.budget_usd == dollars(budget), f"the plan holds budget {raised.plan.budget_usd}, expected {dollars(budget)}. Rule: a resume stores the raised budget. Fix: replace budget_usd before resume_plan."
    return rig


def start_action(site, arm):
    assert arm in ARM_LABELS, f"{arm!r} is not a model arm. Fix: use LOO, Rule or Repeat."
    job = claim_next_job(narrow_context(site, arm))
    if job is None:
        raise LifecycleRefused(f"the model starts a run in {arm} but the code claims nothing. Rule: L1 to L9 decide a start")
    assert job.cell.arm == ARM_LABELS[arm], f"the code claimed {job} for arm {arm}. Rule: a claim stays in the asked cell."
    return job


def replay_action(rig, action, after):
    name, args = action[0], action[1:]
    assert name in (*CODE_ACTIONS, *UNREPLAYED_ACTIONS), f"unknown model action {name!r}. Fix: map it in replay_action."
    site = rig.site
    if name == "ValidateWorld":
        validate_site(site)
    elif name == "WorldChanged":
        rig.edits += 1
        plant(site.world_dir, WORLD_EDIT_FILE, f"edit {rig.edits}")
    elif name == "CheckReach":
        record_reachability(site, ARM_LABELS[args[0]], REACH_OF[after["reach"][args[0]]])
    elif name == "BeginRunning":
        start_running(site)
    elif name == "Start":
        start_action(site, args[0])
    elif name in ("Record", "Timeout"):
        finish_action(rig, name, args)
    elif name in ("FinishComplete", "FinishBudgetStopped"):
        conclude(full_context(site))
    elif name == "Resume":
        resume_action(rig, args[0])
    elif name == "Analyze":
        analyze_gate(site.root, site.plan)
        finish_analysis(site.root, site.plan)
    elif name == "Abort":
        abort_plan(site.root, site.plan)
    assert rig.edits >= 0 and rig.arms, f"{name} broke the rig: {rig}"
    return rig


def refused(call):
    assert callable(call), f"refused needs a function, got {call!r}. Fix: pass the call to try."
    try:
        call()
        outcome = False
    except LifecycleRefused:
        outcome = True
    assert isinstance(outcome, bool), f"refused computed {outcome!r}, not a bool"
    return outcome


def start_problems(site, arms, startable):
    assert isinstance(startable, list), f"startable is {startable!r}, not a list. Fix: print it in TraceWalk.tla."
    assert set(arms) <= set(MODEL_ARMS), f"arms {arms!r} are not model arms. Fix: use LOO, Rule or Repeat."
    return [
        f"the code started a run in {arm} where the model forbids Start. Rule: L1 to L9 and the budget decide a start"
        for arm in arms
        if cell_key(arm) not in startable and claim_next_job(narrow_context(site, arm)) is not None
    ]


def resume_problems(site, state):
    assert state["state"] in STATE_VALUES, f"{state['state']!r} is not a plan state. Fix: print planState in TraceWalk.tla."
    assert state["budget"] >= 0, f"the model budget is {state['budget']}. Fix: print budget in TraceWalk.tla."
    raised = replace(site, plan=replace(site.plan, budget_usd=dollars(state["budget"] + 1)))
    allowed = state["state"] == PlanState.BUDGET_STOPPED.value and state["worldOk"]
    stopped = allowed or refused(lambda: resume_plan(raised))
    return [] if stopped else [f"the code resumed from {state['state']} with world validated {state['worldOk']}. Rule: L10, only a BudgetStopped plan with a validated world resumes"]


def ending_problems(site, state):
    assert state["state"] in STATE_VALUES, f"{state['state']!r} is not a plan state. Fix: print planState in TraceWalk.tla."
    assert isinstance(state["finishable"], bool), f"finishable is {state['finishable']!r}, not a bool. Fix: print it in TraceWalk.tla."
    quiet = all(cell[0] == cell[1] + cell[2] for cell in state["cells"].values())
    if state["state"] == PlanState.RUNNING.value and quiet and not state["finishable"] and conclude(full_context(site)) is not PlanState.RUNNING:
        return ["the code ended a Running plan the model keeps Running. Rule: T2, a plan ends only when no cell is pending or the budget blocks every start"]
    return []


def verdict_problems(site, state):
    assert state["state"] in STATE_VALUES, f"{state['state']!r} is not a plan state. Fix: print planState in TraceWalk.tla."
    assert isinstance(state["analyzable"], bool), f"analyzable is {state['analyzable']!r}, not a bool. Fix: print it in TraceWalk.tla."
    final = state["state"] in FINAL_PLAN_STATES
    problems = []
    if not state["analyzable"] and not final and not refused(lambda: analyze_gate(site.root, site.plan)):
        problems.append(f"the code analysed a plan in {state['state']}. Rule: L5, a verdict needs Complete or BudgetStopped")
    if final and not refused(lambda: abort_plan(site.root, site.plan)):
        problems.append(f"the code aborted a plan in {state['state']}. Rule: abort is possible only before Analyzed")
    return problems


def probe_refusals(rig, state):
    assert state["state"] in STATE_VALUES, f"{state['state']!r} is not a plan state. Fix: print planState in TraceWalk.tla."
    assert isinstance(state["startable"], list), f"startable is {state['startable']!r}, not a list. Fix: print it in TraceWalk.tla."
    with tempfile.TemporaryDirectory(prefix="replay-probe-") as directory:
        root = Path(directory) / PROBE_DIRECTORY
        shutil.copytree(rig.site.root, root)
        site = replace(rig.site, root=root, world_dir=root / WORLD_NAME)
        problems = [*verdict_problems(site, state), *resume_problems(site, state), *start_problems(site, rig.arms, state["startable"]), *ending_problems(site, state)]
    probed = len(rig.arms) + PROBES_PER_STATE
    assert probed > len(rig.arms), f"probed {probed} actions, no more than the arms"
    return problems, probed


def compare_step(rig, action, state):
    assert state["state"] in STATE_VALUES, f"{state['state']!r} is not a plan state. Fix: print planState in TraceWalk.tla."
    assert action, f"the step has no action: {state}. Fix: print act in TraceWalk.tla."
    reason = ""
    try:
        rig = replay_action(rig, action, state) if action[0] != "Init" else rig
        observed = observe(rig)
        problems, probed = probe_refusals(rig, state)
        reason = problems[0] if problems else ""
    except (LifecycleRefused, AssertionError) as refusal:
        observed, probed = {}, 0
        reason = f"the code refused or broke a rule: {refusal}"
    reason = reason or ("" if observed == expected_of(state) else "the code state differs from the model state")
    return rig, observed, probed, reason


def replay_walk(walk, header, work):
    assert walk and header["constants"], "replay_walk needs a walk and the model constants. Fix: load them from the fixture."
    assert all(key in walk[0] for key in OBSERVED_KEYS), f"the first state lacks {OBSERVED_KEYS}. Fix: regenerate the walks."
    rig = build_rig(work, header["constants"], walk[0]["arms"])
    steps = 0
    probes = 0
    for index, state in enumerate(walk):
        rig, observed, probed, reason = compare_step(rig, state["act"], state)
        steps += 1
        probes += probed
        if reason:
            return steps, probes, Divergence(header["scenario"], header["seed"], 0, index, state["act"][0], reason, expected_of(state), observed)
    assert steps == len(walk), f"compared {steps} of {len(walk)} states. Rule: every state is compared. Fix: do not skip states."
    return steps, probes, None


def replay_walks(walks, header):
    assert walks, "replay_walks got no walks. Fix: load a fixture or run TLC."
    assert header["scenario"], f"the header {header} names no scenario. Fix: regenerate the walks."
    steps = 0
    probes = 0
    with tempfile.TemporaryDirectory(prefix="replay-walks-") as directory:
        for number, walk in enumerate(walks):
            walked, probed, divergence = replay_walk(walk, header, Path(directory) / f"walk-{number}")
            steps += walked
            probes += probed
            if divergence:
                return ReplayResult(number + 1, steps, probes, replace(divergence, walk=number))
    return ReplayResult(len(walks), steps, probes, None)
