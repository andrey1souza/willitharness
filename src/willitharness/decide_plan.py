from dataclasses import dataclass
from pathlib import Path

from willitharness.analysis import AnalysisInput, analyze_plan
from willitharness.decision import decide
from willitharness.lifecycle import ANALYZABLE, lifecycle_dir, read_reach, read_state
from willitharness.plan import TARGET_OUTCOME, Plan, has_guard_arm
from willitharness.store import load_records
from willitharness.vocabulary import Decision, EffectResult, GuardResult, Reach

GUARD_ARM_REFUSAL = (
    "plan {name} has a guard_only arm. Rule: decide cannot read guard evidence yet, so it would call a tested guard GuardUntested. "
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
    decision: Decision


def rule_decision_of(row, reach):
    assert isinstance(reach, Reach), f"rule_decision_of needs a Reach, got {reach!r}. Fix: read it with read_reach."
    assert row.effect is not None, f"row {row.task} {row.second} lacks an effect. Rule: target rows carry an effect."
    return RuleDecision(row.task, row.second, reach, row.effect, decide(reach, row.effect, GuardResult.GUARD_UNTESTED))


def decidable_folder(root, plan):
    assert isinstance(root, Path), f"decidable_folder needs a Path root, got {root!r}. Fix: pass the project directory."
    assert isinstance(plan, Plan), f"decidable_folder needs a Plan, got {plan!r}. Fix: load the plan."
    folder = lifecycle_dir(root, plan)
    state = read_state(folder)
    if state not in ANALYZABLE:
        raise DecideRefused(STATE_REFUSAL.format(name=plan.name, state=state))
    if has_guard_arm(plan):
        raise DecideRefused(GUARD_ARM_REFUSAL.format(name=plan.name))
    assert state in ANALYZABLE and not has_guard_arm(plan), f"decidable_folder let plan {plan.name} pass in state {state}"
    return folder


def rule_decisions(root, plan):
    assert isinstance(root, Path), f"rule_decisions needs a Path root, got {root!r}. Fix: pass the project directory."
    assert isinstance(plan, Plan), f"rule_decisions needs a Plan, got {plan!r}. Fix: load the plan."
    folder = decidable_folder(root, plan)
    reach = read_reach(folder)
    analysis = analyze_plan(AnalysisInput(plan, load_records(folder), reach, False), False)
    rows = [row for row in analysis.rows if row.outcome == TARGET_OUTCOME]
    assert all(row.effect is not None for row in rows), f"a target row lacks an effect: {rows!r}. Rule: target rows always carry an effect."
    found = tuple(rule_decision_of(row, reach.get(row.second, Reach.UNKNOWN)) for row in rows)
    assert len(found) == len(rows), f"rule_decisions lost rows: {len(found)} of {len(rows)}"
    return found


def decision_line(item):
    assert isinstance(item, RuleDecision), f"decision_line needs a RuleDecision, got {item!r}. Fix: build it with rule_decisions."
    assert item.task and item.rule, f"a decision names its task and rule, got {item!r}"
    return f"decision {item.task} {item.rule}: {item.decision} (reach {item.reach}, effect {item.effect}, guard {GuardResult.GUARD_UNTESTED})"
