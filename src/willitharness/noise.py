from dataclasses import dataclass

from willitharness.counts import Counts
from willitharness.plan import ROLE_LEAVE_ONE_OUT, noise_target
from willitharness.store import Cell
from willitharness.verdict import noise_status_of
from willitharness.vocabulary import NoiseStatus


@dataclass(frozen=True)
class NoisePair:
    loo: str
    repeat: str


def loo_label_of(plan):
    labels = [arm.label for arm in plan.arms if arm.role == ROLE_LEAVE_ONE_OUT]
    assert len(labels) <= 1, f"plan {plan.name} has {len(labels)} LOO arms. Rule: the loader keeps one. Fix: load the plan with load_plan."
    assert all(label for label in labels), f"plan {plan.name} has an unlabeled LOO arm. Rule: every arm has a label."
    return labels[0] if labels else None


def noise_pair_of(plan):
    loo = loo_label_of(plan)
    repeats = [arm.label for arm in plan.arms if loo is not None and noise_target(arm.role) == loo]
    assert all(label != loo for label in repeats), f"the LOO arm {loo} repeats itself. Rule: a repeat is its own arm."
    assert loo is not None or not repeats, f"repeats {repeats} found without a LOO arm"
    return NoisePair(loo, repeats[0]) if repeats else None


def noise_status_in(pair, counts, task):
    assert pair is not None, "noise_status_in needs a pair. Rule: V6, a plan with no pair is NoiseUnmeasured. Fix: map None before the call."
    assert isinstance(task, str) and task, f"task is {task!r}. Rule: noise is measured in one task. Fix: pass the task name."
    status = noise_status_of(counts[Cell(pair.loo, task)], counts[Cell(pair.repeat, task)])
    assert status in NoiseStatus, f"noise_status_of returned {status!r}"
    smaller_side = min(counts[Cell(pair.loo, task)].runs, counts[Cell(pair.repeat, task)].runs)
    assert status is not NoiseStatus.NOISE_OK or smaller_side >= 1, f"V6 broken: {status} with {smaller_side} runs on the smaller side of {counts}"
    return status
