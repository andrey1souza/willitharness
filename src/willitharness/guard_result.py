from dataclasses import dataclass

from willitharness.bypass import bypass_counts
from willitharness.counts import Counts
from willitharness.guard import GuardRule, coverage_of, evaluate
from willitharness.outcomes import COMPLETED_OUTCOME, cell_counts
from willitharness.plan import KIND_FORBIDDEN, ROLE_GUARD_ONLY, ROLE_RULE, Plan
from willitharness.store import RunState, latest_by_run
from willitharness.verdict import verdict_of
from willitharness.vocabulary import Coverage, GuardResult, Verdict


@dataclass(frozen=True)
class GuardReading:
    result: GuardResult
    completed: Verdict | None
    coverage: Coverage
    bypass: Counts


def labels_with_role(plan: Plan, role: str) -> tuple[str, ...]:
    assert plan.arms, f"plan {plan.name} has no arms. Rule: a plan needs arms. Fix: load the plan with load_plan."
    assert role in (ROLE_GUARD_ONLY, ROLE_RULE), f"labels_with_role knows guard_only and rule, got {role!r}. Fix: pass one of them."
    labels = tuple(arm.label for arm in plan.arms if arm.role == role)
    assert len(set(labels)) == len(labels), f"labels {labels} repeat in plan {plan.name}"
    return labels


def pooled_completed(records: tuple, labels: tuple[str, ...]) -> Counts:
    assert labels, "pooled_completed needs arm labels. Fix: pass the labels of one role."
    assert all(record.run_id for record in records), f"pooled_completed needs stored records, got {records!r}. Fix: use load_records."
    cells = [counts for cell, counts in cell_counts(records, COMPLETED_OUTCOME).items() if cell.arm in labels]
    pooled = Counts(sum(item.successes for item in cells), sum(item.runs for item in cells))
    assert pooled.runs == sum(item.runs for item in cells), f"pooling changed n: {pooled} from {cells}"
    return pooled


def completed_verdict(plan: Plan, records: tuple) -> Verdict | None:
    guards, rules = labels_with_role(plan, ROLE_GUARD_ONLY), labels_with_role(plan, ROLE_RULE)
    result = verdict_of(pooled_completed(records, guards), pooled_completed(records, rules[:1])) if guards and rules else None
    assert result is None or (guards and rules), f"a verdict {result} came without a guard arm and a rule arm"
    assert result is None or result in Verdict, f"unknown verdict {result!r}"
    return result


def guard_runs(plan: Plan, records: tuple, calls_by_run: dict) -> tuple:
    guards = labels_with_role(plan, ROLE_GUARD_ONLY)
    usable = [run for run in latest_by_run(records).values() if run.arm in guards and run.state is RunState.RECORDED_USABLE]
    missing = [run.run_id for run in usable if run.run_id not in calls_by_run]
    assert not missing, f"no calls for usable guard runs {missing}. Rule: bypass reads each usable guard-arm run. Fix: pass the calls of every run."
    runs = tuple(calls_by_run[run.run_id] for run in usable)
    assert len(runs) == len(usable), f"guard_runs lost runs: {len(runs)} of {len(usable)}"
    return runs


def guard_reading(plan: Plan, records: tuple, calls_by_run: dict, rules: tuple[GuardRule, ...]) -> GuardReading:
    assert rules, "guard_reading needs rules. Fix: load them with load_rules."
    runs = guard_runs(plan, records, calls_by_run)
    rule = plan.rule
    actions = rule.detector.actions if rule is not None and rule.detector.kind == KIND_FORBIDDEN else None
    coverage = coverage_of(tuple(call for run in runs for call in run), actions, rules) if actions else Coverage.NONE_SEEN
    bypass = bypass_counts(runs, rules)
    completed = completed_verdict(plan, records)
    result = evaluate(completed, coverage, bypass.successes == 0)
    assert completed is not None or result is GuardResult.GUARD_UNTESTED, f"no guard comparison yet {result}"
    assert coverage is not Coverage.NONE_SEEN or result is GuardResult.GUARD_UNTESTED, f"NoneSeen gave {result}"
    return GuardReading(result, completed, coverage, bypass)
