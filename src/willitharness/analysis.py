from dataclasses import dataclass
from typing import NamedTuple

from willitharness.counts import Counts
from willitharness.effect import map_effect
from willitharness.noise import NoisePair, loo_label_of, noise_pair_of, noise_status_in
from willitharness.outcomes import OUTCOMES, TARGET_OUTCOME, AnalysisError, cell_counts, denied_cells
from willitharness.plan import ROLE_RULE, Plan
from willitharness.probe import loo_arm_valid
from willitharness.store import Cell
from willitharness.verdict import MIN_RUNS, verdict_of
from willitharness.vocabulary import EffectResult, NoiseStatus, Reach, Verdict
from willitharness.warning_rules import cell_warnings, row_warnings

LOO_INVALID_MESSAGE = "LOO arm does not load its other rules; the effect cannot be reported"
RULE_UNKNOWN_MESSAGE = "the rule arm's reachability is Unknown; run the probe again before measuring an effect"
NO_NOISE_PAIR_MESSAGE = "no noise pair; add a repeat of arm {loo} with role noise_of:{loo}"
POOLED_TASK = "all:pooled"
POOLED_LABEL = "[pooled]"
NO_COMPARISON_MESSAGE = (
    "plan {name} has no leave_one_out arm or no rule arm to compare. Rule: Q2 compares the LOO arm with a rule arm. "
    "Fix: give one arm the role leave_one_out and one arm the role rule."
)
NO_RUNS_MESSAGE = "plan {name} has no stored runs. Rule: a verdict counts stored runs. Fix: run the plan first."
NOISE_MESSAGES = {
    NoiseStatus.NOISE_UNMEASURED: "the noise pair has fewer than {minimum} usable runs on one side; run more repeats of arm {loo}",
    NoiseStatus.NOISE_FLOOR_TOO_HIGH: "the two identical arms differed; do not trust this comparison",
}


@dataclass(frozen=True)
class PlanFacts:
    has_noise_pair: bool
    noise: NoiseStatus
    loo_probe: Reach
    rule_reach: Reach


@dataclass(frozen=True)
class EffectAnalysis:
    effect: EffectResult
    verdict: Verdict | None
    message: str | None


def can_report(facts):
    assert isinstance(facts.has_noise_pair, bool), f"has_noise_pair must be a flag, got {facts.has_noise_pair!r}"
    assert facts.noise in NoiseStatus and facts.loo_probe in Reach and facts.rule_reach in Reach, f"unknown value in {facts}"
    return (
        facts.has_noise_pair
        and facts.noise is NoiseStatus.NOISE_OK
        and loo_arm_valid(facts.loo_probe)
        and facts.rule_reach is not Reach.UNKNOWN
    )


def blocking_message(facts, loo_label):
    assert loo_label, "blocking_message needs the LOO arm label. Fix: pass the label of the leave_one_out arm."
    assert not can_report(facts), f"blocking_message was called for a plan that can report: {facts}"
    if not facts.has_noise_pair:
        return NO_NOISE_PAIR_MESSAGE.format(loo=loo_label)
    if not loo_arm_valid(facts.loo_probe):
        return LOO_INVALID_MESSAGE
    if facts.rule_reach is Reach.UNKNOWN:
        return RULE_UNKNOWN_MESSAGE
    return NOISE_MESSAGES[facts.noise].format(minimum=MIN_RUNS, loo=loo_label)


def analyze_effect(facts, verdict, loo_label):
    assert verdict in Verdict, f"unknown verdict {verdict!r}"
    assert loo_label, "analyze_effect needs the LOO arm label. Fix: pass the label of the leave_one_out arm."
    if can_report(facts):
        outcome = EffectAnalysis(map_effect(facts.noise, verdict), verdict, None)
    else:
        outcome = EffectAnalysis(EffectResult.INVALID, None, blocking_message(facts, loo_label))
    assert (outcome.verdict is not None) == can_report(facts), f"V6 or L8 broken: {outcome} for {facts}"
    assert outcome.verdict is None or outcome.message is None, f"a reported effect carries no blocking message: {outcome}"
    return outcome


@dataclass(frozen=True)
class AnalysisInput:
    plan: Plan
    records: tuple
    reach: dict
    pooled: bool


@dataclass(frozen=True)
class RowSource:
    pair: NoisePair | None
    loo: str
    reach: dict
    rules: tuple


class RowKey(NamedTuple):
    outcome: str
    task: str
    rule: str
    pooled: bool


@dataclass(frozen=True)
class Row:
    outcome: str
    task: str
    first: str
    second: str
    pooled: bool
    first_counts: Counts
    second_counts: Counts
    noise: NoiseStatus
    verdict: Verdict | None
    effect: EffectResult | None
    message: str | None


@dataclass(frozen=True)
class Analysis:
    rows: tuple
    warnings: tuple


def messages_of(analysis):
    assert isinstance(analysis, Analysis), f"messages_of needs an Analysis, got {analysis!r}. Fix: build it with analyze_plan."
    found = list(dict.fromkeys(row.message for row in analysis.rows if row.message))
    assert len(found) <= len(analysis.rows), f"messages_of invented messages: {found}"
    return found


def has_verdict(analysis):
    assert isinstance(analysis, Analysis), f"has_verdict needs an Analysis, got {analysis!r}. Fix: build it with analyze_plan."
    result = any(row.outcome == TARGET_OUTCOME and row.verdict is not None for row in analysis.rows)
    assert not result or analysis.rows, "a verdict needs rows"
    return result


def build_row(source, counts, key):
    assert key.outcome in OUTCOMES, f"unknown outcome {key.outcome!r}. Rule: v0 defines {OUTCOMES}. Fix: use one of them."
    assert Cell(source.loo, key.task) in counts and Cell(key.rule, key.task) in counts, f"counts lack a cell of {key}. Fix: fill every arm and task."
    first_counts, second_counts = counts[Cell(source.loo, key.task)], counts[Cell(key.rule, key.task)]
    verdict = verdict_of(first_counts, second_counts)
    noise = NoiseStatus.NOISE_UNMEASURED if source.pair is None else noise_status_in(source.pair, counts, key.task)
    head = (key.outcome, key.task, source.loo, key.rule, key.pooled)
    if key.outcome == TARGET_OUTCOME:
        facts = PlanFacts(source.pair is not None, noise, source.reach.get(source.loo, Reach.UNKNOWN), source.reach.get(key.rule, Reach.UNKNOWN))
        reported = analyze_effect(facts, verdict, source.loo)
        row = Row(*head, first_counts, second_counts, noise, reported.verdict, reported.effect, reported.message)
    else:
        row = Row(*head, first_counts, second_counts, noise, verdict if noise is NoiseStatus.NOISE_OK else None, None, None)
    assert row.verdict is None or row.noise is NoiseStatus.NOISE_OK, f"V6 broken: verdict {row.verdict} with {row.noise}"
    return row


def with_all_cells(counts, plan, tasks):
    cells = {Cell(arm.label, task): counts.get(Cell(arm.label, task), Counts(0, 0)) for arm in plan.arms for task in tasks}
    assert set(counts) <= set(cells), f"records name cells outside the plan: {sorted(set(counts) - set(cells))}. Fix: analyze the plan that ran them."
    assert len(cells) == len(plan.arms) * len(tasks), f"with_all_cells built {len(cells)} cells for {len(plan.arms)} arms and {len(tasks)} tasks from {sorted(counts)} and {tasks}"
    return cells


def pooled_cells(counts, plan, tasks):
    assert tasks, "pooled_cells needs tasks. Rule: a pooled verdict spans tasks. Fix: pass the task names."
    pooled = {
        Cell(arm.label, POOLED_TASK): Counts(
            sum(counts[Cell(arm.label, task)].successes for task in tasks),
            sum(counts[Cell(arm.label, task)].runs for task in tasks),
        )
        for arm in plan.arms
    }
    assert all(item.runs == sum(counts[Cell(cell.arm, task)].runs for task in tasks) for cell, item in pooled.items()), f"pooling changed n over tasks {tasks}: {counts} gave {pooled}"
    return pooled


def outcome_rows(source, counts, outcome):
    assert outcome in OUTCOMES, f"unknown outcome {outcome!r}. Rule: v0 defines {OUTCOMES}. Fix: use one of them."
    assert source.rules, "outcome_rows needs rule arms. Rule: Q2 compares the LOO arm with a rule arm. Fix: check the plan first."
    tasks = sorted({cell.task for cell in counts if cell.task != POOLED_TASK})
    tasks += [POOLED_TASK] if any(cell.task == POOLED_TASK for cell in counts) else []
    keys = [RowKey(outcome, task, rule, task == POOLED_TASK) for task in tasks for rule in source.rules]
    return [build_row(source, counts, key) for key in keys]


def analyze_plan(inputs, with_warnings):
    plan = inputs.plan
    loo = loo_label_of(plan)
    rules = tuple(arm.label for arm in plan.arms if arm.role == ROLE_RULE)
    if loo is None or not rules:
        raise AnalysisError(NO_COMPARISON_MESSAGE.format(name=plan.name))
    tasks = sorted({run.task for run in inputs.records})
    if not tasks:
        raise AnalysisError(NO_RUNS_MESSAGE.format(name=plan.name))
    source = RowSource(noise_pair_of(plan), loo, inputs.reach, rules)
    rows, target_counts = [], {}
    for outcome in OUTCOMES:
        counts = with_all_cells(cell_counts(inputs.records, outcome), plan, tasks)
        target_counts = counts if outcome == TARGET_OUTCOME else target_counts
        shown = {**counts, **pooled_cells(counts, plan, tasks)} if inputs.pooled else counts
        rows.extend(outcome_rows(source, shown, outcome))
    lines = (*cell_warnings(target_counts, denied_cells(inputs.records)), *row_warnings(rows)) if with_warnings else ()
    analysis = Analysis(tuple(rows), lines)
    assert with_warnings or not analysis.warnings, f"warnings were off but {analysis.warnings} came out"
    assert analysis.rows, f"plan {plan.name} gave no rows. Rule: each task and outcome has a row."
    return analysis


def render_row(row):
    assert row.first and row.second, f"row {row.key} lacks an arm label. Rule: a row compares two arms."
    assert row.verdict is None or row.noise is NoiseStatus.NOISE_OK, f"V6 broken: verdict {row.verdict} with {row.noise}"
    verdict = "no verdict" if row.verdict is None else f"verdict {row.verdict}"
    effect = "" if row.effect is None else f"; effect {row.effect}"
    label = f" {POOLED_LABEL}" if row.pooled else ""
    first, second = row.first_counts, row.second_counts
    return (
        f"{row.outcome} {row.task} {row.first} {first.successes}/{first.runs} against {row.second} "
        f"{second.successes}/{second.runs}: {verdict}; noise {row.noise}{effect}{label}"
    )


def report_lines(analysis):
    assert analysis.rows, "report_lines needs rows. Fix: build the analysis with analyze_plan."
    lines = [render_row(row) for row in analysis.rows] + messages_of(analysis) + list(analysis.warnings)
    assert len(lines) >= len(analysis.rows), f"report_lines dropped a row: {len(lines)} lines for {len(analysis.rows)} rows"
    return lines
