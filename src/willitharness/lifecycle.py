import json
import threading
from dataclasses import asdict, dataclass, replace
from decimal import Decimal
from enum import StrEnum
from pathlib import Path

from willitharness.budget import Ledger, abort_records, capped_record, timed_out_record, to_money
from willitharness.claude_agent import transcript_cost
from willitharness.paths import inside
from willitharness.plan import Plan, plan_fingerprint
from willitharness.store import (
    EMPTY_COUNTERS,
    Cell,
    Record,
    RunState,
    append_record,
    cell_counters,
    facts_from_plan,
    in_flight_runs,
    latest_by_run,
    load_records,
    run_id_of,
    runs_to_start,
)
from willitharness.stream import parse_stream
from willitharness.vocabulary import Reach
from willitharness.world import STORE_DIR, stored_hash, world_changed

STATE_FILE = "state.json"
REACH_FILE = "reach.json"
RESUME_FILE = "resume.json"
NOT_ENDED = "none"
STATE_KEY = "state"
MAX_PARALLEL_RUNNERS = 4
WORLD_NOT_VALIDATED = "world not validated; run: willitharness world check"
WORLD_CHANGED = "world changed since validation; run: willitharness world check"
ABORT_AFTER_ANALYSIS = "plan already analyzed; abort is not possible"
ANALYZE_AFTER_ABORT = "plan aborted; no verdict"
ANALYZE_WHILE_RUNNING = "plan still running; analyze after Complete or BudgetStopped"
RESUME_WORLD_REFUSED = "world not validated or changed since validation. Rule: L10, the world must be validated again before a resume. Fix: run willitharness world check."
RESUME_NO_RECORD = "plan has no stored budget and fingerprint. Rule: L10, a plan stores both when it first runs. Fix: start the plan with run before resuming."
RESUME_PLAN_CHANGED = "plan differs from the stored plan in more than budget_usd. Rule: A-FP, a resume changes only the budget. Fix: restore the plan and raise only budget_usd."
NOTHING_TO_RESUME = "plan is Complete; there is nothing to resume. Rule: L10, only a BudgetStopped plan resumes. Fix: run willitharness analyze."
ANALYZE_BEFORE_RUN = "plan has not run yet; analyze after Complete or BudgetStopped"
STORE_LOCK = threading.Lock()


class LifecycleRefused(Exception):
    pass


class PlanState(StrEnum):
    DRAFTED = "Drafted"
    WORLD_VALIDATED = "WorldValidated"
    REACHABILITY_CHECKED = "ReachabilityChecked"
    RUNNING = "Running"
    COMPLETE = "Complete"
    BUDGET_STOPPED = "BudgetStopped"
    ABORTED = "Aborted"
    ANALYZED = "Analyzed"
    REPORTED = "Reported"


PRE_RUN_ORDER = (PlanState.DRAFTED, PlanState.WORLD_VALIDATED, PlanState.REACHABILITY_CHECKED)
ANALYZABLE = frozenset({PlanState.COMPLETE, PlanState.BUDGET_STOPPED, PlanState.ANALYZED, PlanState.REPORTED})
FINAL_STATES = frozenset({PlanState.ANALYZED, PlanState.REPORTED})
LEGAL_MOVES = {
    PlanState.DRAFTED: frozenset({PlanState.WORLD_VALIDATED, PlanState.ABORTED}),
    PlanState.WORLD_VALIDATED: frozenset({PlanState.REACHABILITY_CHECKED, PlanState.DRAFTED, PlanState.ABORTED}),
    PlanState.REACHABILITY_CHECKED: frozenset({PlanState.RUNNING, PlanState.DRAFTED, PlanState.ABORTED}),
    PlanState.RUNNING: frozenset({PlanState.COMPLETE, PlanState.BUDGET_STOPPED, PlanState.ABORTED}),
    PlanState.COMPLETE: frozenset({PlanState.ANALYZED, PlanState.ABORTED}),
    PlanState.BUDGET_STOPPED: frozenset({PlanState.ANALYZED, PlanState.ABORTED, PlanState.RUNNING}),
    PlanState.ABORTED: frozenset(),
    PlanState.ANALYZED: frozenset({PlanState.REPORTED}),
    PlanState.REPORTED: frozenset(),
}


@dataclass(frozen=True)
class ResumeRecord:
    budget_usd: float
    fingerprint: str
    ended_by: str


@dataclass(frozen=True)
class PlanSite:
    root: Path
    plan: Plan
    world_dir: Path


@dataclass(frozen=True)
class RunSetup:
    site: PlanSite
    tasks: tuple[str, ...]
    timeout_seconds: float


@dataclass(frozen=True)
class RunResult:
    transcript: tuple[str, ...]
    timed_out: bool


@dataclass(frozen=True)
class Job:
    cell: Cell
    rep: int
    attempt: int


@dataclass(frozen=True)
class RunContext:
    setup: RunSetup
    runner: object
    ledger: Ledger


TIMED_OUT = RunResult((), True)


def finished(lines):
    assert not isinstance(lines, (str, bytes)), f"finished needs one line per item, got {type(lines).__name__}. Fix: split the transcript first."
    result = RunResult(tuple(lines), False)
    assert not result.timed_out, "a finished result was marked timed out. Rule: only TIMED_OUT carries the timeout flag."
    return result


def lifecycle_dir(root, plan):
    assert isinstance(root, Path), f"lifecycle_dir needs a Path root, got {root!r}. Fix: pass the project directory."
    assert plan.name, "the plan has no name. Rule: the plan name names its folder. Fix: load the plan with load_plan."
    folder = inside(root, f"{STORE_DIR}/{plan.name}")
    folder.mkdir(parents=True, exist_ok=True)
    assert folder.is_dir(), f"{folder} was not created. Rule: the lifecycle files live next to the run store."
    return folder


def read_state(folder):
    assert isinstance(folder, Path), f"read_state needs the plan folder as a Path, got {folder!r}. Fix: use lifecycle_dir."
    path = folder / STATE_FILE
    state = PlanState(json.loads(path.read_text())[STATE_KEY]) if path.is_file() else PlanState.DRAFTED
    assert state in PlanState, f"{path} holds {state!r}, which is not a plan state. Rule: only legal states are written."
    return state


def write_state(folder, state):
    assert isinstance(state, PlanState), f"write_state needs a PlanState, got {state!r}. Fix: pass a member of PlanState."
    (folder / STATE_FILE).write_text(json.dumps({STATE_KEY: state.value}))
    assert read_state(folder) is state, f"{folder / STATE_FILE} did not keep {state}. Rule: the state is persisted."


def move_to(folder, target):
    assert isinstance(target, PlanState), f"move_to needs a PlanState, got {target!r}. Fix: pass a member of PlanState."
    current = read_state(folder)
    if current is target:
        return current
    if target not in LEGAL_MOVES[current]:
        raise LifecycleRefused(f"plan cannot move from {current} to {target}. Rule: contract section 7 lists the legal moves. Fix: follow the order of the lifecycle.")
    write_state(folder, target)
    assert read_state(folder) is target, f"the state is {read_state(folder)} after the move to {target}"
    return target


def read_reach(folder):
    assert isinstance(folder, Path), f"read_reach needs the plan folder as a Path, got {folder!r}. Fix: use lifecycle_dir."
    path = folder / REACH_FILE
    stored = json.loads(path.read_text()) if path.is_file() else {}
    reach = {arm: Reach(value) for arm, value in stored.items()}
    assert len(reach) == len(stored), f"{path} lost arms while loading: {len(stored)} in, {len(reach)} out"
    return reach


def read_resume(folder):
    assert isinstance(folder, Path), f"read_resume needs the plan folder as a Path, got {folder!r}. Fix: use lifecycle_dir."
    path = folder / RESUME_FILE
    record = ResumeRecord(**json.loads(path.read_text())) if path.is_file() else None
    assert record is None or record.fingerprint, f"{path} holds no fingerprint. Rule: the fingerprint is stored with the budget."
    return record


def write_resume(folder, record):
    assert isinstance(record, ResumeRecord), f"write_resume needs a ResumeRecord, got {record!r}. Fix: build one with the budget, fingerprint and ended marker."
    (folder / RESUME_FILE).write_text(json.dumps(asdict(record)))
    assert read_resume(folder) == record, f"{folder / RESUME_FILE} did not keep {record}. Rule: the stored budget, fingerprint and ended marker persist."


def missing_arms(site):
    assert isinstance(site, PlanSite), f"missing_arms needs a PlanSite, got {site!r}. Fix: build one with the root, plan and world directory."
    recorded = read_reach(lifecycle_dir(site.root, site.plan))
    missing = tuple(arm.label for arm in site.plan.arms if arm.label not in recorded)
    assert set(missing) <= {arm.label for arm in site.plan.arms}, f"missing arms {missing} are not arms of the plan"
    return missing


def world_is_validated(site):
    assert isinstance(site, PlanSite), f"world_is_validated needs a PlanSite, got {site!r}. Fix: build one with the root, plan and world directory."
    validated = stored_hash(site.root, site.world_dir) is not None and not world_changed(site.root, site.world_dir)
    assert isinstance(validated, bool), f"world_is_validated returned {validated!r}, not a bool"
    return validated


def pre_run_target(site):
    assert isinstance(site, PlanSite), f"pre_run_target needs a PlanSite, got {site!r}. Fix: build one with the root, plan and world directory."
    if not world_is_validated(site):
        target = PlanState.DRAFTED
    elif missing_arms(site):
        target = PlanState.WORLD_VALIDATED
    else:
        target = PlanState.REACHABILITY_CHECKED
    assert target in PRE_RUN_ORDER, f"pre_run_target returned {target}. Rule: before Running only the first three states apply."
    return target


def refresh_state(site):
    assert isinstance(site, PlanSite), f"refresh_state needs a PlanSite, got {site!r}. Fix: build one with the root, plan and world directory."
    folder = lifecycle_dir(site.root, site.plan)
    state = read_state(folder)
    if state not in PRE_RUN_ORDER:
        return state
    position = PRE_RUN_ORDER.index(state)
    goal = PRE_RUN_ORDER.index(pre_run_target(site))
    if goal < position:
        move_to(folder, PlanState.DRAFTED)
        position = 0
    for step in PRE_RUN_ORDER[position + 1:goal + 1]:
        move_to(folder, step)
    settled = read_state(folder)
    assert settled in PRE_RUN_ORDER, f"refresh_state left the plan in {settled}. Rule: a refresh never leaves the pre-run states."
    assert settled is PRE_RUN_ORDER[goal], f"refresh_state ended in {settled}, expected {PRE_RUN_ORDER[goal]}. Rule: W3, the state follows the world."
    return settled


def record_reachability(site, arm, reach):
    assert isinstance(reach, Reach), f"record_reachability needs a Reach, got {reach!r}. Fix: pass Reach.LOADED, MASKED or UNKNOWN."
    assert arm in {known.label for known in site.plan.arms}, f"{arm} is not an arm of plan {site.plan.name}. Rule: reachability belongs to a plan arm. Fix: use an arm label."
    folder = lifecycle_dir(site.root, site.plan)
    recorded = {name: value.value for name, value in read_reach(folder).items()}
    recorded[arm] = reach.value
    (folder / REACH_FILE).write_text(json.dumps(recorded))
    assert read_reach(folder)[arm] is reach, f"{arm} did not keep {reach}. Rule: a result is recorded once given."
    return refresh_state(site)


def start_running(site):
    state = refresh_state(site)
    folder = lifecycle_dir(site.root, site.plan)
    if stored_hash(site.root, site.world_dir) is None:
        raise LifecycleRefused(WORLD_NOT_VALIDATED)
    if world_changed(site.root, site.world_dir):
        raise LifecycleRefused(WORLD_CHANGED)
    absent = missing_arms(site)
    if absent:
        raise LifecycleRefused(f"no reachability result for arm {absent[0]} of plan {site.plan.name} (missing: {', '.join(absent)}); probe the arm and record the result")
    if state is not PlanState.RUNNING and state is not PlanState.REACHABILITY_CHECKED:
        raise LifecycleRefused(f"plan is {state}; a run can start only from ReachabilityChecked or Running")
    if state is PlanState.REACHABILITY_CHECKED:
        write_resume(folder, ResumeRecord(site.plan.budget_usd, plan_fingerprint(site.plan), NOT_ENDED))
    running = move_to(folder, PlanState.RUNNING)
    assert running is PlanState.RUNNING, f"start_running ended in {running}. Rule: L1, runs start only in Running."
    assert not absent and world_is_validated(site), f"start_running passed for plan {site.plan.name} with missing arms {absent}. Rule: L1. Fix: check the world and the arms first."
    return running


def started_record(job):
    assert isinstance(job, Job), f"started_record needs a Job, got {job!r}. Fix: build the job with Job(cell, rep, attempt)."
    record = Record(run_id_of(job.cell, job.rep, job.attempt), job.cell.arm, job.cell.task, job.rep, job.attempt, RunState.STARTED, {}, 0.0)
    assert record.state is RunState.STARTED, f"a new run is {record.state}. Rule: a run begins Started."
    return record


def begin_run(folder, job):
    state = read_state(folder)
    if state is not PlanState.RUNNING:
        raise LifecycleRefused(f"plan is {state}; a run starts only while the plan is Running. Rule: L1. Fix: run willitharness run first.")
    assert isinstance(folder, Path), f"begin_run needs the plan folder as a Path, got {folder!r}. Fix: use lifecycle_dir."
    record = started_record(job)
    append_record(folder, record)
    stored = latest_by_run(load_records(folder)).get(record.run_id)
    assert stored == record, f"{record.run_id} is stored as {stored!r}, expected {record!r}. Rule: a Started run is stored as written."
    assert stored.state is RunState.STARTED, f"{record.run_id} is stored as {stored.state}. Rule: a new run begins Started."
    return record


def money_spent(records):
    assert isinstance(records, tuple), f"money_spent needs a tuple of records, got {type(records).__name__}. Fix: pass load_records output."
    total = sum((to_money(run.cost_usd) for run in latest_by_run(records).values() if run.state is not RunState.STARTED), Decimal(0))
    assert total >= 0, f"money_spent is {total}. Rule: a cost is never negative."
    return total


def ledger_from_records(plan, records):
    assert isinstance(plan, Plan), f"ledger_from_records needs a Plan, got {plan!r}. Fix: load the plan."
    assert isinstance(records, tuple), f"ledger_from_records needs a tuple of records, got {type(records).__name__}. Fix: pass load_records output."
    ledger = Ledger(plan.budget_usd, plan.run_cap_usd)
    ledger.spent = money_spent(records)
    ledger.reserved = ledger.run_cap * len(in_flight_runs(records))
    assert ledger.spent + ledger.reserved >= 0, f"the ledger holds {ledger.spent} spent and {ledger.reserved} reserved. Rule: amounts are never negative."
    return ledger


def claim_next_job(context):
    assert isinstance(context, RunContext), f"claim_next_job needs a RunContext, got {context!r}. Fix: build one in execute_plan."
    site = context.setup.site
    folder = lifecycle_dir(site.root, site.plan)
    facts = facts_from_plan(site.plan, context.setup.tasks)
    with STORE_LOCK:
        if read_state(folder) is not PlanState.RUNNING or world_changed(site.root, site.world_dir):
            return None
        records = load_records(folder)
        missing = runs_to_start(facts, records)
        cell = next((candidate for candidate in facts.cells if missing[candidate] > 0), None)
        if cell is None or not context.ledger.reserve():
            return None
        seen = cell_counters(records).get(cell, EMPTY_COUNTERS)
        job = Job(cell, seen.usable + seen.in_flight + 1, seen.attempts + 1)
        begin_run(folder, job)
        assert context.ledger.spent + context.ledger.reserved <= context.ledger.budget, f"L2 broken after claiming {job}"
        assert job.attempt <= site.plan.reps + site.plan.max_retries, f"L9 broken: {job} is past reps plus max_retries. Fix: claim only what runs_to_start allows."
        return job


def call_runner(context, job):
    assert isinstance(job, Job), f"call_runner needs a Job, got {job!r}. Fix: claim one with claim_next_job."
    assert context.setup.timeout_seconds > 0, f"the timeout is {context.setup.timeout_seconds}. Rule: every run has a wall-clock limit above 0. Fix: pass a positive limit."
    outcome = []
    worker = threading.Thread(target=lambda: outcome.append(context.runner(job.cell, job.rep, job.attempt)), daemon=True)
    worker.start()
    worker.join(context.setup.timeout_seconds)
    if worker.is_alive():
        return TIMED_OUT
    return outcome[0] if outcome else finished(())


def judged_record(started, result, run_cap):
    assert started.state is RunState.STARTED, f"judged_record needs a Started run, got {started.state}. Fix: pass the record written at the start."
    assert isinstance(result, RunResult), f"judged_record needs a RunResult, got {result!r}. Fix: the runner returns RunResult."
    lines = list(result.transcript)
    parsed = parse_stream(lines, (), run_cap)
    flags = {"attempted_violation": parsed.usable_for_attempted_violation, "completed": parsed.usable_for_completed}
    final = capped_record(replace(started, usable=flags), parsed.state, transcript_cost(lines), run_cap)
    assert final.state is not RunState.STARTED, f"the judged run is still {final.state}. Rule: T1, every run ends recorded."
    return final


def finish_job(context, job, result):
    site = context.setup.site
    folder = lifecycle_dir(site.root, site.plan)
    run_cap = site.plan.run_cap_usd
    with STORE_LOCK:
        started = latest_by_run(load_records(folder)).get(started_record(job).run_id)
        if started is None or started.state is not RunState.STARTED:
            return None
        final = timed_out_record(started, run_cap) if result.timed_out else judged_record(started, result, run_cap)
        append_record(folder, final)
        context.ledger.settle(final.cost_usd)
        assert final.cost_usd <= run_cap, f"run {final.run_id} cost {final.cost_usd} above RUN_CAP {run_cap}. Rule: A-CAP."
        assert not result.timed_out or final.state is RunState.RECORDED_UNUSABLE, f"timed out run {final.run_id} became {final.state}. Rule: a timeout is unusable."
        return final


def work_loop(context):
    assert isinstance(context, RunContext), f"work_loop needs a RunContext, got {context!r}. Fix: build one in execute_plan."
    assert context.setup.tasks, "work_loop got no tasks. Rule: a cell is an arm and a task. Fix: name at least one task."
    job = claim_next_job(context)
    while job is not None:
        finish_job(context, job, call_runner(context, job))
        job = claim_next_job(context)


def conclude(context):
    assert isinstance(context, RunContext), f"conclude needs a RunContext, got {context!r}. Fix: build one in execute_plan."
    site = context.setup.site
    folder = lifecycle_dir(site.root, site.plan)
    facts = facts_from_plan(site.plan, context.setup.tasks)
    with STORE_LOCK:
        state = read_state(folder)
        if state is not PlanState.RUNNING or world_changed(site.root, site.world_dir):
            return state
        pending = any(count > 0 for count in runs_to_start(facts, load_records(folder)).values())
        target = PlanState.BUDGET_STOPPED if pending else PlanState.COMPLETE
        assert target in (PlanState.COMPLETE, PlanState.BUDGET_STOPPED), f"conclude chose {target}. Rule: a finished Running plan is Complete or BudgetStopped."
        concluded = move_to(folder, target)
        write_resume(folder, replace(read_resume(folder), ended_by=target.value))
        return concluded


def resume_plan(site):
    assert isinstance(site, PlanSite), f"resume_plan needs a PlanSite, got {site!r}. Fix: build one with the root, plan and world directory."
    folder = lifecycle_dir(site.root, site.plan)
    with STORE_LOCK:
        state = read_state(folder)
        if state is not PlanState.BUDGET_STOPPED:
            raise LifecycleRefused(f"plan is {state}; only a BudgetStopped plan resumes. Rule: L10. Fix: run willitharness run on a BudgetStopped plan.")
        stored = read_resume(folder)
        if stored is None:
            raise LifecycleRefused(RESUME_NO_RECORD)
        if not world_is_validated(site):
            raise LifecycleRefused(RESUME_WORLD_REFUSED)
        if plan_fingerprint(site.plan) != stored.fingerprint:
            raise LifecycleRefused(RESUME_PLAN_CHANGED)
        if to_money(site.plan.budget_usd) <= to_money(stored.budget_usd):
            raise LifecycleRefused(f"budget_usd {site.plan.budget_usd} is not above the stored budget {stored.budget_usd}. Rule: L11, a resume raises the budget. Fix: set budget_usd above {stored.budget_usd} in the plan.")
        write_resume(folder, ResumeRecord(site.plan.budget_usd, stored.fingerprint, NOT_ENDED))
        resumed = move_to(folder, PlanState.RUNNING)
    assert resumed is PlanState.RUNNING, f"resume_plan ended in {resumed}. Rule: L10, a resume ends in Running."
    assert read_resume(folder).ended_by == NOT_ENDED, f"plan {site.plan.name} is Running but marked as ended. Rule: L12. Fix: reset the ended marker on resume."
    return resumed


def resume_if_stopped(site):
    assert isinstance(site, PlanSite), f"resume_if_stopped needs a PlanSite, got {site!r}. Fix: build one with the root, plan and world directory."
    state = read_state(lifecycle_dir(site.root, site.plan))
    if state is PlanState.COMPLETE:
        raise LifecycleRefused(NOTHING_TO_RESUME)
    resumed = resume_plan(site) if state is PlanState.BUDGET_STOPPED else state
    assert resumed in PlanState, f"resume_if_stopped returned {resumed!r}, not a plan state"
    return resumed


def execute_plan(setup, runner):
    assert isinstance(setup, RunSetup), f"execute_plan needs a RunSetup, got {setup!r}. Fix: build one with the site, tasks and timeout."
    assert callable(runner), f"the runner is {runner!r}. Rule: the runner is injected as runner(cell, rep, attempt). Fix: pass a function."
    start_running(setup.site)
    folder = lifecycle_dir(setup.site.root, setup.site.plan)
    ledger = ledger_from_records(setup.site.plan, load_records(folder))
    context = RunContext(setup, runner, ledger)
    workers = [threading.Thread(target=work_loop, args=(context,)) for _ in range(MAX_PARALLEL_RUNNERS)]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join()
    outcome = conclude(context)
    assert ledger.spent + ledger.reserved <= ledger.budget, f"L2 broken: spent {ledger.spent} plus reserved {ledger.reserved} above {ledger.budget}"
    assert outcome in PlanState, f"execute_plan ended in {outcome!r}, not a plan state"
    return outcome


def abort_plan(root, plan):
    assert isinstance(root, Path), f"abort_plan needs a Path root, got {root!r}. Fix: pass the project directory."
    assert isinstance(plan, Plan), f"abort_plan needs a Plan, got {plan!r}. Fix: load the plan."
    folder = lifecycle_dir(root, plan)
    with STORE_LOCK:
        state = read_state(folder)
        if state in FINAL_STATES:
            raise LifecycleRefused(ABORT_AFTER_ANALYSIS)
        records = load_records(folder)
        for record in abort_records(records, plan.run_cap_usd)[len(records):]:
            append_record(folder, record)
        move_to(folder, PlanState.ABORTED)
    assert not in_flight_runs(load_records(folder)), f"runs are still in flight after abort: {in_flight_runs(load_records(folder))}. Rule: T2a."
    assert read_state(folder) is PlanState.ABORTED, f"the plan is {read_state(folder)} after abort. Rule: abort ends in Aborted."
    return PlanState.ABORTED


def analyze_gate(root, plan):
    assert isinstance(root, Path), f"analyze_gate needs a Path root, got {root!r}. Fix: pass the project directory."
    assert isinstance(plan, Plan), f"analyze_gate needs a Plan, got {plan!r}. Fix: load the plan."
    state = read_state(lifecycle_dir(root, plan))
    if state is PlanState.ABORTED:
        raise LifecycleRefused(ANALYZE_AFTER_ABORT)
    if state is PlanState.RUNNING:
        raise LifecycleRefused(ANALYZE_WHILE_RUNNING)
    if state not in ANALYZABLE:
        raise LifecycleRefused(ANALYZE_BEFORE_RUN)
    assert state in ANALYZABLE, f"analyze_gate let state {state} pass. Rule: L5, a verdict needs Complete or BudgetStopped."
    return state

