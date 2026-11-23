import json
from collections import Counter
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import NamedTuple

from willitharness.paths import inside
from willitharness.plan import Plan

APPEND_MODE = "a"
RUNS_FILE_NAME = "runs.jsonl"
EMPTY_LINE = ""
UNKNOWN_WORLD = ""
UNKNOWN_MODEL = ""


class StoreError(Exception):
    pass


class RunState(StrEnum):
    STARTED = "Started"
    RECORDED_USABLE = "RecordedUsable"
    RECORDED_UNUSABLE = "RecordedUnusable"


class Cell(NamedTuple):
    arm: str
    task: str


@dataclass(frozen=True)
class Record:
    run_id: str
    arm: str
    task: str
    rep: int
    attempt: int
    state: RunState
    usable: dict
    cost_usd: float
    outcome: dict = field(default_factory=dict)
    denials: int = 0
    world_hash: str = UNKNOWN_WORLD
    model: str = UNKNOWN_MODEL


@dataclass(frozen=True)
class CellCounters:
    usable: int
    in_flight: int
    attempts: int


@dataclass(frozen=True)
class PlanFacts:
    cells: tuple[Cell, ...]
    reps: int
    max_retries: int


EMPTY_COUNTERS = CellCounters(usable=0, in_flight=0, attempts=0)


def run_id_of(cell, rep, attempt):
    assert isinstance(cell, Cell), f"run_id_of needs a Cell, got {cell!r}. Fix: build the cell with Cell(arm, task)."
    assert rep >= 1 and attempt >= 1, f"rep {rep} and attempt {attempt} start at 1. Rule: run ids count from 1. Fix: pass positive numbers."
    return f"{cell.arm}/{cell.task}/{rep}#{attempt}"


def cell_of(record):
    assert isinstance(record, Record), f"cell_of needs a Record, got {record!r}. Fix: pass a stored record."
    assert record.arm and record.task, f"record {record.run_id} lacks an arm or a task. Rule: every run belongs to a cell. Fix: name both."
    return Cell(record.arm, record.task)


def facts_from_plan(plan, tasks):
    assert isinstance(plan, Plan), f"facts_from_plan needs a Plan, got {plan!r}. Fix: load the plan with load_plan."
    assert tasks, "facts_from_plan got no tasks. Rule: a cell is an arm and a task. Fix: name at least one task."
    cells = tuple(Cell(arm.label, task) for arm in plan.arms for task in tasks)
    return PlanFacts(cells=cells, reps=plan.reps, max_retries=plan.max_retries)


def record_to_line(record):
    assert isinstance(record, Record), f"record_to_line needs a Record, got {record!r}. Fix: pass a Record."
    line = json.dumps({**asdict(record), "state": record.state.value}, sort_keys=True)
    assert "\n" not in line, f"the line for {record.run_id} holds a line break. Rule: one record is one line. Fix: remove the break from the values."
    return line


def record_from_line(line):
    assert line.strip(), "record_from_line got an empty line. Fix: skip empty lines before parsing."
    try:
        data = json.loads(line)
        record = Record(**{**data, "state": RunState(data["state"])})
    except (ValueError, KeyError, TypeError) as error:
        raise StoreError(f"cannot read the record {line!r} ({error}). Rule: a line is one record. Fix: repair or remove the line.") from error
    assert record.run_id, f"the line {line!r} has no run id. Rule: every record names its run. Fix: add run_id."
    return record


def runs_file(root):
    assert isinstance(root, Path), f"runs_file needs a Path, got {root!r}. Fix: pass the plan folder as pathlib.Path."
    path = inside(root, RUNS_FILE_NAME)
    assert path.name == RUNS_FILE_NAME, f"the store file is {path.name}, not {RUNS_FILE_NAME}. Rule: the store is one runs file. Fix: restore the constant."
    return path


def load_records(root):
    path = runs_file(root)
    if not path.exists():
        return ()
    lines = [line for line in path.read_text().splitlines() if line.strip() != EMPTY_LINE]
    records = tuple(record_from_line(line) for line in lines)
    assert len(records) == len(lines), f"load_records lost lines of {path}: {len(lines)} in, {len(records)} out"
    assert all(isinstance(record, Record) for record in records), f"load_records returned a non-record from {path}"
    return records


def latest_by_run(records):
    assert isinstance(records, tuple), f"latest_by_run needs a tuple of records, got {type(records).__name__}. Fix: pass load_records output."
    latest = {}
    for record in records:
        latest[record.run_id] = record
    assert len(latest) <= len(records), f"{len(latest)} runs from {len(records)} records. Rule: a run has at least one record."
    return latest


def same_run(first, second):
    assert isinstance(first, Record) and isinstance(second, Record), f"same_run compares records, got {first!r} and {second!r}"
    assert first.run_id == second.run_id, f"same_run compared {first.run_id} with {second.run_id}. Fix: compare records of one run."
    return (first.arm, first.task, first.rep, first.attempt) == (second.arm, second.task, second.rep, second.attempt)


def with_record(records, record):
    assert isinstance(record, Record), f"with_record needs a Record, got {record!r}. Fix: pass a Record."
    assert isinstance(records, tuple), f"with_record needs a tuple of records, got {type(records).__name__}. Fix: pass load_records output."
    prior = latest_by_run(records).get(record.run_id)
    if prior is None:
        return (*records, record)
    if prior == record:
        return records
    if prior.state is RunState.STARTED and record.state is not RunState.STARTED and same_run(prior, record):
        return (*records, record)
    raise StoreError(
        f"run {record.run_id} is already stored as {prior!r} and cannot become {record!r}. "
        "Rule: a recorded run never changes (L3). Fix: record a new attempt under a new run id."
    )


def append_record(root, record):
    path = runs_file(root)
    existing = load_records(root)
    updated = with_record(existing, record)
    if len(updated) > len(existing):
        with path.open(APPEND_MODE) as handle:
            handle.write(record_to_line(record) + "\n")
    assert len(load_records(root)) == len(updated), f"{path} does not hold {len(updated)} records after the append. Rule: the store only grows."
    assert record.run_id in latest_by_run(updated), f"run {record.run_id} is missing after the append. Rule: a record is stored or refused."
    return updated


def cell_counters(records):
    runs = latest_by_run(records).values()
    cells = {run.run_id: cell_of(run) for run in runs}
    attempts = Counter(cells.values())
    usable = Counter(cells[run.run_id] for run in runs if run.state is RunState.RECORDED_USABLE)
    in_flight = Counter(cells[run.run_id] for run in runs if run.state is RunState.STARTED)
    counters = {cell: CellCounters(usable[cell], in_flight[cell], attempts[cell]) for cell in attempts}
    assert sum(item.attempts for item in counters.values()) == len(latest_by_run(records)), "cell_counters lost or doubled a run"
    assert all(item.usable + item.in_flight <= item.attempts for item in counters.values()), f"a cell has more usable and in flight runs than attempts: {counters}"
    return counters


def spent(records):
    runs = latest_by_run(records).values()
    assert all(run.cost_usd >= 0 for run in runs), f"a run has a negative cost in {records}. Rule: a cost is never negative. Fix: record the cost as 0 or more."
    total = sum(run.cost_usd for run in runs if run.state is not RunState.STARTED)
    assert total >= 0, f"spent is {total}. Rule: a cost is never negative. Fix: record the cost as 0 or more."
    return total


def in_flight_runs(records):
    runs = tuple(run for run in latest_by_run(records).values() if run.state is RunState.STARTED)
    assert all(run.state is RunState.STARTED for run in runs), f"in_flight_runs returned a finished run: {runs}"
    assert len(runs) <= len(records), f"{len(runs)} runs in flight from {len(records)} records"
    return runs


def runs_to_start(facts, records):
    assert isinstance(facts, PlanFacts), f"runs_to_start needs PlanFacts, got {facts!r}. Fix: build them with facts_from_plan."
    assert facts.reps >= 1 and facts.max_retries >= 0, f"reps {facts.reps} and max_retries {facts.max_retries} are out of range. Rule: reps is 1 or more. Fix: load the plan."
    counters = cell_counters(records)
    missing = {}
    for cell in facts.cells:
        seen = counters.get(cell, EMPTY_COUNTERS)
        room_for_reps = facts.reps - seen.usable - seen.in_flight
        room_for_attempts = facts.reps + facts.max_retries - seen.attempts
        missing[cell] = max(0, min(room_for_reps, room_for_attempts))
    assert set(missing) == set(facts.cells), f"runs_to_start dropped a cell: {set(facts.cells) - set(missing)}"
    assert all(count >= 0 for count in missing.values()), f"a cell has a negative number of runs to start: {missing}"
    return missing
