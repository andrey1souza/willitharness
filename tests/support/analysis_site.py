import json
from dataclasses import dataclass

from files import write_tree
from lifecycle_site import SCHEMA_VERSION, TASK_NAME, TASK_PROMPT, WORLD_NAME, reach_every_arm, validate_site

from willitharness.analysis import AnalysisInput, analyze_plan
from willitharness.lifecycle import PlanSite, lifecycle_dir, read_reach, write_state
from willitharness.plan import load_plan
from willitharness.store import UNKNOWN_MODEL, Cell, Record, RunState, append_record, load_records, run_id_of
from willitharness.vocabulary import Reach

LOO_LABEL = "C"
REPEAT_LABEL = "C2"
RULE_LABEL = "B"
FULL_ROLES = {RULE_LABEL: "rule", LOO_LABEL: "leave_one_out", REPEAT_LABEL: f"noise_of:{LOO_LABEL}"}
NO_PAIR_ROLES = {RULE_LABEL: "rule", LOO_LABEL: "leave_one_out"}
RUN_COST_USD = 0.01
TARGET = "attempted_violation"
COMPLETED = "completed"


@dataclass(frozen=True)
class CellShape:
    n: int
    k: int
    unusable_for_completed: int = 0
    denied: int = 0
    incomplete: int = 1
    model: str = UNKNOWN_MODEL


def stored_usable_record(cell, rep, shape):
    assert 1 <= rep <= shape.n, f"rep {rep} is outside 1..{shape.n}. Fix: count reps from 1 to n."
    assert shape.k <= shape.n and shape.denied <= shape.n, f"shape {shape} counts more runs than n. Fix: keep k and denied at or below n."
    return Record(
        run_id_of(cell, rep, 1),
        cell.arm,
        cell.task,
        rep,
        1,
        RunState.RECORDED_USABLE,
        {TARGET: True, COMPLETED: rep <= shape.n - shape.unusable_for_completed},
        RUN_COST_USD,
        {TARGET: rep <= shape.k, COMPLETED: rep > shape.incomplete},
        1 if rep <= shape.denied else 0,
        model=shape.model,
    )


def cell_records(cell, shape):
    records = [stored_usable_record(cell, rep, shape) for rep in range(1, shape.n + 1)]
    assert len(records) == shape.n, f"cell_records built {len(records)} records for n {shape.n}"
    assert sum(record.outcome[TARGET] for record in records) == shape.k, f"cell_records built the wrong k for {shape}"
    return records


def analysis_plan_data(roles):
    assert roles, "plan_data needs roles. Fix: pass a label to role mapping."
    assert all(isinstance(label, str) for label in roles), f"labels are text, got {roles!r}"
    arms = [{"label": label, "role": role, "overlay": f"{label}.md"} for label, role in roles.items()]
    return {
        "schema": SCHEMA_VERSION,
        "name": "demo",
        "world": WORLD_NAME,
        "budget_usd": 100.0,
        "run_cap_usd": 1.0,
        "reps": 20,
        "max_retries": 2,
        "arms": arms,
    }


def make_analysis_site(root, roles):
    data = analysis_plan_data(roles)
    write_tree(root, {"plan.json": json.dumps(data), f"{WORLD_NAME}/tasks.txt": f"{TASK_NAME}: ls\n", f"{WORLD_NAME}/real.txt": "ls\n", f"{WORLD_NAME}/prompts/{TASK_NAME}.txt": TASK_PROMPT})
    site = PlanSite(root, load_plan(data), root / WORLD_NAME)
    validate_site(site)
    reach_every_arm(site, Reach.LOADED)
    assert (root / "plan.json").is_file(), "the plan file was not written"
    return site


def store_cells(site, cells):
    assert cells, "store_cells needs cells. Fix: pass a mapping from Cell to CellShape."
    assert all(isinstance(cell, Cell) for cell in cells), f"keys must be cells, got {list(cells)!r}"
    folder = lifecycle_dir(site.root, site.plan)
    for cell, shape in cells.items():
        for record in cell_records(cell, shape):
            append_record(folder, record)
    return site


def site_with_state(root, roles, cells_and_state):
    cells, state = cells_and_state
    site = store_cells(make_analysis_site(root, roles), cells)
    write_state(lifecycle_dir(site.root, site.plan), state)
    assert cells, "site_with_state got no cells. Fix: name at least one cell."
    return site


def analyze_site(site, pooled, with_warnings):
    folder = lifecycle_dir(site.root, site.plan)
    inputs = AnalysisInput(site.plan, load_records(folder), read_reach(folder), pooled)
    assert inputs.records, f"site {site.plan.name} stores no records. Fix: store cells first."
    return analyze_plan(inputs, with_warnings)


TASK = "stop-server"
OTHER_TASK = "backup-delete"
DEFAULT_SHAPE = CellShape(n=20, k=10)
TWO_TASK_CELLS = {
    Cell(LOO_LABEL, TASK): CellShape(20, 17),
    Cell(REPEAT_LABEL, TASK): CellShape(20, 16),
    Cell(RULE_LABEL, TASK): CellShape(20, 0),
    Cell(LOO_LABEL, OTHER_TASK): CellShape(20, 15),
    Cell(REPEAT_LABEL, OTHER_TASK): CellShape(20, 14),
    Cell(RULE_LABEL, OTHER_TASK): CellShape(20, 2),
}


def filled_cells(roles, given):
    tasks = {cell.task for cell in given} or {TASK}
    cells = {Cell(arm, task): DEFAULT_SHAPE for arm in roles for task in tasks}
    cells.update(given)
    assert set(cells) >= set(given), f"filled_cells dropped a cell of {given}"
    assert all(cell.arm in roles for cell in cells), f"cells {sorted(cells)} name an arm outside {sorted(roles)}"
    return cells
