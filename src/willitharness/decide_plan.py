from dataclasses import dataclass
from pathlib import Path

from willitharness.analysis import AnalysisInput, analyze_plan
from willitharness.decision import decide
from willitharness.lifecycle import ANALYZABLE, lifecycle_dir, read_reach, read_state
from willitharness.guard_result import guard_arm_rules, guard_reading, stored_guard_calls, usable_guard_records
from willitharness.plan import TARGET_OUTCOME, Plan, has_guard_arm
from willitharness.store import load_records
from willitharness.vocabulary import Decision, EffectResult, GuardResult, Reach

THREE_ARM_GUARD_REFUSAL = (
    "plan {name} has a guard_only arm. Rule: a three-arm decision reads no guard evidence, so it would hide the guard arm. "
    "Fix: remove the guard_only arm from the plan."
)
STATE_REFUSAL = (
    "plan {name} is {state}. Rule: a decision needs a finished plan, one that is Complete, BudgetStopped, Analyzed or Reported. "
    "Fix: run the plan to its end, then run decide again."
)


class DecideRefused(Exception):
    pass


@dataclass(frozen=True)
class RuleDecision:
    task: str
    rule: str
    reach: Reach
    effect: EffectResult
    guard: GuardResult
    decision: Decision


def rule_decision_of(row, reach, guard):
    assert isinstance(reach, Reach), f"rule_decision_of needs a Reach, got {reach!r}. Fix: read it with read_reach."
    assert row.effect is not None, f"row {row.task} {row.second} lacks an effect. Rule: target rows carry an effect."
    assert isinstance(guard, GuardResult), f"rule_decision_of needs a GuardResult, got {guard!r}. Fix: read it with guard_result_of."
    return RuleDecision(row.task, row.second, reach, row.effect, guard, decide(reach, row.effect, guard))


def guard_result_of(root, plan, folder, records):
    assert isinstance(root, Path) and isinstance(folder, Path), f"guard_result_of needs Path values, got {root!r} and {folder!r}. Fix: pass the project directory and lifecycle_dir."
    assert isinstance(records, tuple), f"guard_result_of needs a tuple of records, got {type(records).__name__}. Fix: pass load_records output."
    if not has_guard_arm(plan):
        return GuardResult.GUARD_UNTESTED
    calls = stored_guard_calls(folder, plan, records)
    rules = guard_arm_rules(root, plan)
    complete = all(run.run_id in calls for run in usable_guard_records(plan, records))
    result = guard_reading(plan, records, calls, rules).result if rules and complete else GuardResult.GUARD_UNTESTED
    assert result in GuardResult, f"guard_result_of built {result!r}"
    return result


def decidable_folder(root, plan):
    assert isinstance(root, Path), f"decidable_folder needs a Path root, got {root!r}. Fix: pass the project directory."
    assert isinstance(plan, Plan), f"decidable_folder needs a Plan, got {plan!r}. Fix: load the plan."
    folder = lifecycle_dir(root, plan)
    state = read_state(folder)
    if state not in ANALYZABLE:
        raise DecideRefused(STATE_REFUSAL.format(name=plan.name, state=state))
    assert state in ANALYZABLE, f"decidable_folder let plan {plan.name} pass in state {state}"
    return folder


def three_arm_folder(root, plan):
    assert isinstance(root, Path), f"three_arm_folder needs a Path root, got {root!r}. Fix: pass the project directory."
    assert isinstance(plan, Plan), f"three_arm_folder needs a Plan, got {plan!r}. Fix: load the plan."
    folder = decidable_folder(root, plan)
    if has_guard_arm(plan):
        raise DecideRefused(THREE_ARM_GUARD_REFUSAL.format(name=plan.name))
    assert not has_guard_arm(plan), f"three_arm_folder let plan {plan.name} pass with a guard arm"
    assert folder.is_dir(), f"three_arm_folder built {folder}, which is not a directory"
    return folder


def rule_decisions(root, plan):
    assert isinstance(root, Path), f"rule_decisions needs a Path root, got {root!r}. Fix: pass the project directory."
    assert isinstance(plan, Plan), f"rule_decisions needs a Plan, got {plan!r}. Fix: load the plan."
    folder = decidable_folder(root, plan)
    reach = read_reach(folder)
    records = load_records(folder)
    analysis = analyze_plan(AnalysisInput(plan, records, reach, False), False)
    guard = guard_result_of(root, plan, folder, records)
    rows = [row for row in analysis.rows if row.outcome == TARGET_OUTCOME]
    assert all(row.effect is not None for row in rows), f"a target row lacks an effect: {rows!r}. Rule: target rows always carry an effect."
    found = tuple(rule_decision_of(row, reach.get(row.second, Reach.UNKNOWN), guard) for row in rows)
    assert len(found) == len(rows), f"rule_decisions lost rows: {len(found)} of {len(rows)}"
    return found


def decision_line(item):
    assert isinstance(item, RuleDecision), f"decision_line needs a RuleDecision, got {item!r}. Fix: build it with rule_decisions."
    assert item.task and item.rule, f"a decision names its task and rule, got {item!r}"
    return f"decision {item.task} {item.rule}: {item.decision} (reach {item.reach}, effect {item.effect}, guard {item.guard})"
