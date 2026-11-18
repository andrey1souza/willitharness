from dataclasses import dataclass

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from lifecycle_site import SiteSpec, costing_runner, make_site, run_setup, success_transcript, validate_site

from files import plant
from willitharness.lifecycle import (
    TIMED_OUT,
    LifecycleRefused,
    PlanState,
    RunContext,
    abort_plan,
    claim_next_job,
    finish_job,
    finished,
    ledger_from_records,
    lifecycle_dir,
    read_state,
    record_reachability,
    start_running,
)
from willitharness.store import EMPTY_COUNTERS, Cell, RunState, cell_counters, latest_by_run, load_records, spent
from willitharness.vocabulary import Reach

EXAMPLES = 60
STEPS = 30
SPEC = SiteSpec(arm_count=2, budget_usd=0.10, run_cap_usd=0.02, reps=2, max_retries=1)
OPERATIONS = ("start", "claim", "usable", "unusable", "timeout", "overcap", "abort", "edit_world", "validate", "reach")
RESULTS = {
    "usable": lambda: success_transcript(0.01),
    "unusable": lambda: finished(()),
    "timeout": lambda: TIMED_OUT,
    "overcap": lambda: success_transcript(0.05),
}
chaos_settings = settings(max_examples=EXAMPLES, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])


@dataclass(frozen=True)
class Step:
    operation: str
    arm_index: int
    reach: Reach


step_strategy = st.builds(Step, st.sampled_from(OPERATIONS), st.integers(min_value=0, max_value=1), st.sampled_from(list(Reach)))
steps = st.lists(step_strategy, min_size=1, max_size=STEPS)


def fresh_context(site):
    ledger = ledger_from_records(site.plan, load_records(lifecycle_dir(site.root, site.plan)))
    return RunContext(run_setup(site), costing_runner(0.01), ledger)


def snapshot(site):
    runs = tuple(latest_by_run(load_records(lifecycle_dir(site.root, site.plan))).values())
    counters = cell_counters(runs)
    cells = [Cell(arm.label, "stop-server") for arm in site.plan.arms]
    per_cell = {cell: (counters.get(cell, EMPTY_COUNTERS).usable, counters.get(cell, EMPTY_COUNTERS).attempts) for cell in cells}
    in_flight = sum(1 for run in runs if run.state is RunState.STARTED)
    return {"runs": runs, "spent": spent(runs), "reserved": SPEC.run_cap_usd * in_flight, "per_cell": per_cell, "stored": len(load_records(lifecycle_dir(site.root, site.plan)))}


def apply_step(site, held, step):
    operation = step.operation
    if operation == "start":
        try:
            start_running(site)
        except LifecycleRefused:
            return
    elif operation == "claim":
        job = claim_next_job(fresh_context(site))
        if job is not None:
            held.append(job)
    elif operation in RESULTS and held:
        finish_job(fresh_context(site), held.pop(0), RESULTS[operation]())
    elif operation == "abort":
        abort_plan(site.root, site.plan)
        held.clear()
    elif operation == "edit_world":
        plant(site.world_dir, "note.txt", f"edit {len(held)} {step.arm_index} {step.reach}")
    elif operation == "validate":
        validate_site(site)
    elif operation == "reach":
        record_reachability(site, site.plan.arms[step.arm_index].label, step.reach)


def check_invariants(site, before, ever_running):
    after = snapshot(site)
    assert ever_running or not after["runs"], f"L1 broken: runs {after['runs']} exist before the plan was ever Running"
    assert after["spent"] + after["reserved"] <= SPEC.budget_usd + 1e-9, f"L2 broken: spent {after['spent']} plus reserved {after['reserved']} above {SPEC.budget_usd}"
    for cell, (usable, attempts) in after["per_cell"].items():
        assert usable <= SPEC.reps, f"L4 broken: {usable} usable runs in {cell}, reps {SPEC.reps}"
        assert attempts <= SPEC.reps + SPEC.max_retries, f"L9 broken: {attempts} attempts in {cell}, cap {SPEC.reps + SPEC.max_retries}"
        assert usable >= before["per_cell"][cell][0] and attempts >= before["per_cell"][cell][1], f"L3 broken: counters of {cell} fell from {before['per_cell'][cell]} to {(usable, attempts)}"
    assert after["spent"] >= before["spent"] - 1e-9 and after["stored"] >= before["stored"], f"L3 broken: spent or stored records fell, {before['spent']} to {after['spent']}"
    return after


@chaos_settings
@given(steps)
def test_L1_to_L9_hold_after_every_step_of_a_random_sequence(tmp_path, sequence):
    site = make_site(tmp_path / f"example-{len(list(tmp_path.iterdir()))}", SPEC)
    held = []
    before = snapshot(site)
    ever_running = False
    checked = 0
    for step in sequence:
        apply_step(site, held, step)
        ever_running = ever_running or read_state(lifecycle_dir(site.root, site.plan)) is PlanState.RUNNING
        before = check_invariants(site, before, ever_running)
        checked += 1
    assert checked == len(sequence), f"checked {checked} of {len(sequence)} steps. Rule: every step is checked. Fix: check after each step."
