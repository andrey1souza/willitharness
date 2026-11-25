from dataclasses import dataclass
from pathlib import Path

from willitharness.agent_line import read_agent_line
from willitharness.analysis import Analysis, AnalysisInput, analyze_plan
from willitharness.artifacts import RUNS_DIR, TRANSCRIPT_NAME
from willitharness.decide_plan import RuleDecision, decision_line, rule_decisions, three_arm_folder
from willitharness.detectors import calls_of
from willitharness.lifecycle import ANALYZE_AFTER_ABORT, FINAL_STATES, PlanState, lifecycle_dir, read_reach, read_state
from willitharness.world_facts import world_facts
from willitharness.outcomes import COMPLETED_OUTCOME, TARGET_OUTCOME, cell_counts
from willitharness.paths import inside
from willitharness.plan import Plan, has_guard_arm
from willitharness.side_effects import MIN_ARMS, side_effect_report_lines
from willitharness.store import RunState, latest_by_run, load_records, spent
from willitharness.three_arm_report import is_three_arm, three_arm_sections
from willitharness.vocabulary import Decision, EffectResult, GuardResult, NoiseStatus
from willitharness.warning_rules import SATURATED_WARNING

PLAN_FILE = "plan.json"
NO_VERDICTS_REFUSAL = "no verdicts yet; run: willitharness analyze"
NO_TRANSCRIPTS_LINE = "Side effects were not measured. Not every arm has a stored transcript."
NO_WARNINGS_LINE = "none"
BULLET = "- "
CONTINUATION = "  "
COUNTS_MEANING = "The counts are attempts, not executed commands. An attempt is a command the agent tried to run."
NOT_MEASURABLE_LINE = "The effect is not measurable at this n."
SIDE_EFFECTS_NEVER_DECIDE = "Side effects never change the decision."
GUARD_LINE = f"Guard: {GuardResult.GUARD_UNTESTED}. The plan has no guard arm, so no guard was run."
GUARD_READ_LINE = "Guard: {guard}. The result reads the runs of the guard arms of the plan."
LIMIT_COUNT = 3
LIMITS = (
    "The result covers one model. Other models can behave differently.",
    "The result covers tasks written by the plan author. Your real tasks can differ.",
    "The result covers the isolation flags used. Effect runs use the sandbox of Claude and have no network.",
)


class ReportRefused(Exception):
    pass


@dataclass(frozen=True)
class ReportInput:
    plan: Plan
    agent: str
    analysis: Analysis
    decisions: tuple
    cost_usd: float
    cells: tuple
    side_effects: tuple


def check_reportable(folder):
    assert isinstance(folder, Path), f"check_reportable needs the plan folder as a Path, got {folder!r}. Fix: use lifecycle_dir."
    state = read_state(folder)
    if state is PlanState.ABORTED:
        raise ReportRefused(ANALYZE_AFTER_ABORT)
    if state not in FINAL_STATES:
        raise ReportRefused(NO_VERDICTS_REFUSAL)
    assert state in FINAL_STATES, f"check_reportable let state {state} pass. Rule: L5, a report needs an analyzed plan."
    return state


def calls_by_arm(folder, records):
    assert isinstance(folder, Path), f"calls_by_arm needs the plan folder as a Path, got {folder!r}. Fix: use lifecycle_dir."
    assert isinstance(records, tuple), f"calls_by_arm needs a tuple of records, got {type(records).__name__}. Fix: pass load_records output."
    found = {}
    for run in latest_by_run(records).values():
        transcript = inside(folder, f"{RUNS_DIR}/{run.arm}/{run.task}/{run.rep}/{TRANSCRIPT_NAME.format(attempt=run.attempt)}")
        if run.state is RunState.RECORDED_USABLE and transcript.is_file():
            found.setdefault(run.arm, []).append(calls_of(transcript.read_text().splitlines()))
    result = {arm: tuple(runs) for arm, runs in sorted(found.items())}
    assert all(result.values()), f"calls_by_arm kept an arm with no runs: {result!r}"
    return result


def side_effect_lines(plan, calls):
    assert isinstance(plan, Plan), f"side_effect_lines needs a Plan, got {plan!r}. Fix: load the plan."
    assert isinstance(calls, dict), f"side_effect_lines needs calls by arm, got {calls!r}. Fix: build them with calls_by_arm."
    every_arm_has_runs = set(calls) == {arm.label for arm in plan.arms} and len(calls) >= MIN_ARMS
    lines = tuple(side_effect_report_lines(calls)) if every_arm_has_runs else (NO_TRANSCRIPTS_LINE,)
    assert lines, f"side_effect_lines built no lines for plan {plan.name}"
    return lines


def rows_of_target_outcome(analysis):
    assert isinstance(analysis, Analysis), f"rows_of_target_outcome needs an Analysis, got {analysis!r}. Fix: build it with analyze_plan."
    rows = tuple(row for row in analysis.rows if row.outcome == TARGET_OUTCOME)
    assert rows, "the analysis has no target rows. Rule: each task and rule has one. Fix: analyze a plan with a rule arm."
    return rows


def saturated_by_rule(analysis):
    assert isinstance(analysis, Analysis), f"saturated_by_rule needs an Analysis, got {analysis!r}. Fix: build it with analyze_plan."
    flags = {(row.task, row.second): SATURATED_WARNING.format(arm=row.first, task=row.task) in analysis.warnings for row in rows_of_target_outcome(analysis)}
    assert len(flags) == len(rows_of_target_outcome(analysis)), f"saturated_by_rule merged rows: {flags!r}"
    return flags


def summary_lines(data):
    assert isinstance(data, ReportInput), f"summary_lines needs a ReportInput, got {data!r}. Fix: build it with report_input."
    lines = [f"# Report for plan {data.plan.name}", "", data.agent, f"Total cost: ${data.cost_usd:.2f}.", COUNTS_MEANING]
    assert data.agent in lines, f"summary_lines lost the agent line {data.agent!r}"
    return lines


def runs_lines(data):
    assert isinstance(data, ReportInput), f"runs_lines needs a ReportInput, got {data!r}. Fix: build it with report_input."
    lines = ["## Usable runs per cell", "", *(f"{BULLET}arm {cell.arm}, task {cell.task}: {counts.runs}" for cell, counts in data.cells)]
    assert len(lines) == len(data.cells) + 2, f"runs_lines dropped a cell: {lines!r}"
    return lines


def reach_lines(decisions):
    assert all(isinstance(item, RuleDecision) for item in decisions), f"reach_lines needs rule decisions, got {decisions!r}. Fix: build them with rule_decisions."
    reaches = sorted({(item.rule, item.reach) for item in decisions})
    lines = ["## Q1 Reachability", "", *(f"{BULLET}Arm {rule}: {reach}." for rule, reach in reaches)]
    assert len(lines) == len(reaches) + 2, f"reach_lines dropped a rule: {lines!r}"
    return lines


def effect_item(row, completed_noise):
    assert isinstance(completed_noise, NoiseStatus), f"effect_item needs the completed noise as a NoiseStatus, got {completed_noise!r}. Fix: read it from the completed row."
    assert row.effect is not None, f"row {row.task} {row.second} lacks an effect. Rule: target rows carry an effect."
    verdict = "No verdict." if row.verdict is None else f"Verdict: {row.verdict}."
    first, second = row.first_counts, row.second_counts
    lines = [
        f"{BULLET}{row.task}, rule {row.second}: {row.effect}.",
        f"{CONTINUATION}Arm {row.first} attempted a violation in {first.successes} of {first.runs} runs. "
        f"Arm {row.second} did so in {second.successes} of {second.runs} runs.",
        f"{CONTINUATION}Noise: {row.noise}. {verdict} Noise on completed runs: {completed_noise}.",
    ]
    result = [*lines, f"{CONTINUATION}{row.message}."] if row.message else lines
    assert result[0].endswith(f"{row.effect}."), f"effect_item lost the effect of {row.task} {row.second}: {result!r}"
    return result


def effect_lines(analysis):
    assert isinstance(analysis, Analysis), f"effect_lines needs an Analysis, got {analysis!r}. Fix: build it with analyze_plan."
    completed = {(row.task, row.second): row.noise for row in analysis.rows if row.outcome == COMPLETED_OUTCOME}
    items = [line for row in rows_of_target_outcome(analysis) for line in effect_item(row, completed[(row.task, row.second)])]
    lines = ["## Q2 Effect", "", *items]
    assert all(str(row.effect) in "\n".join(lines) for row in rows_of_target_outcome(analysis)), f"effect_lines dropped an effect: {lines!r}"
    return lines


def guard_lines(plan, decisions):
    assert isinstance(plan, Plan), f"guard_lines needs a Plan, got {plan!r}. Fix: load the plan."
    assert decisions, "guard_lines needs decisions. Fix: build them with rule_decisions."
    guard = decisions[0].guard
    line = GUARD_READ_LINE.format(guard=guard) if has_guard_arm(plan) else GUARD_LINE
    lines = ["## Q3 Guard", "", f"{BULLET}{line}"]
    assert str(guard) in lines[-1], f"guard_lines lost the guard value: {lines!r}"
    return lines


def side_effect_section(side_effects):
    assert side_effects and all(isinstance(line, str) for line in side_effects), f"side_effect_section needs text lines, got {side_effects!r}. Fix: build them with side_effect_lines."
    lines = ["## Q4 Side effects", "", SIDE_EFFECTS_NEVER_DECIDE, "", *(f"{BULLET}{line}" for line in side_effects)]
    assert len(lines) == len(side_effects) + 4, f"side_effect_section dropped a line: {lines!r}"
    return lines


def decision_item(item, saturated):
    assert isinstance(item, RuleDecision), f"decision_item needs a RuleDecision, got {item!r}. Fix: build it with rule_decisions."
    assert isinstance(saturated, bool), f"decision_item needs the saturated flag as a bool, got {saturated!r}. Fix: read it with saturated_by_rule."
    lines = [f"{BULLET}{decision_line(item)}; saturated: {str(saturated).lower()}"]
    caveat = item.decision is Decision.DELETE_CANDIDATE and item.effect is EffectResult.NO_MEASURABLE_EFFECT
    return [*lines, f"{CONTINUATION}{NOT_MEASURABLE_LINE}"] if caveat else lines


def decision_lines(decisions, saturated):
    assert decisions, "decision_lines needs decisions. Fix: build them with rule_decisions."
    assert isinstance(saturated, dict), f"decision_lines needs the saturated flags, got {saturated!r}. Fix: build them with saturated_by_rule."
    items = [line for item in decisions for line in decision_item(item, saturated[(item.task, item.rule)])]
    lines = ["## Decision", "", *items]
    assert all(str(item.decision) in "\n".join(lines) for item in decisions), f"decision_lines dropped a decision: {lines!r}"
    return lines


def warning_lines(analysis):
    assert isinstance(analysis, Analysis), f"warning_lines needs an Analysis, got {analysis!r}. Fix: build it with analyze_plan."
    shown = analysis.warnings or (NO_WARNINGS_LINE,)
    lines = ["## Warnings", "", *(f"{BULLET}{line}" for line in shown)]
    assert len(lines) == len(shown) + 2, f"warning_lines dropped a warning: {lines!r}"
    return lines


def limit_lines():
    assert len(LIMITS) == LIMIT_COUNT, f"the report lists {len(LIMITS)} limits, not {LIMIT_COUNT}. Rule: one model, the tasks and the isolation flags. Fix: restore the limit."
    lines = ["## Limits", "", *(f"{BULLET}{line}" for line in LIMITS)]
    assert len(lines) == len(LIMITS) + 2, f"limit_lines dropped a limit: {lines!r}"
    return lines


def report_text(data):
    assert isinstance(data, ReportInput), f"report_text needs a ReportInput, got {data!r}. Fix: build it with report_input."
    sections = (
        summary_lines(data),
        runs_lines(data),
        reach_lines(data.decisions),
        effect_lines(data.analysis),
        guard_lines(data.plan, data.decisions),
        side_effect_section(data.side_effects),
        decision_lines(data.decisions, saturated_by_rule(data.analysis)),
        warning_lines(data.analysis),
        limit_lines(),
    )
    text = "\n\n".join("\n".join(section) for section in sections) + "\n"
    assert text.count("\n## ") >= len(sections) - 1, f"report_text lost a section: {text!r}"
    return text


def report_input(root, plan):
    assert isinstance(root, Path), f"report_input needs a Path root, got {root!r}. Fix: pass the project directory."
    assert isinstance(plan, Plan), f"report_input needs a Plan, got {plan!r}. Fix: load the plan."
    folder = lifecycle_dir(root, plan)
    check_reportable(folder)
    records = load_records(folder)
    analysis = analyze_plan(AnalysisInput(plan, records, read_reach(folder), False, world_facts(root, plan)), True)
    data = ReportInput(
        plan,
        read_agent_line(root, plan),
        analysis,
        rule_decisions(root, plan),
        spent(records),
        tuple(sorted(cell_counts(records, TARGET_OUTCOME).items())),
        side_effect_lines(plan, calls_by_arm(folder, records)),
    )
    assert data.decisions, f"report_input found no decision for plan {plan.name}"
    return data


def three_arm_report_text(root, plan):
    assert isinstance(root, Path), f"three_arm_report_text needs a Path root, got {root!r}. Fix: pass the project directory."
    assert is_three_arm(plan), f"three_arm_report_text needs a three-arm plan, got {plan!r}. Fix: check is_three_arm first."
    folder = lifecycle_dir(root, plan)
    check_reportable(folder)
    three_arm_folder(root, plan)
    records = load_records(folder)
    summary = [f"# Report for plan {plan.name}", "", read_agent_line(root, plan), f"Total cost: ${spent(records):.2f}.", COUNTS_MEANING]
    runs = ["## Usable runs per cell", "", *(f"{BULLET}arm {cell.arm}, task {cell.task}: {counts.runs}" for cell, counts in sorted(cell_counts(records, TARGET_OUTCOME).items()))]
    sections = (summary, runs, *three_arm_sections(folder, plan, records), limit_lines())
    text = "\n\n".join("\n".join(section) for section in sections) + "\n"
    assert text.count("\n## ") >= len(sections) - 1, f"three_arm_report_text lost a section: {text!r}"
    return text


def build_report(root, plan):
    assert isinstance(root, Path), f"build_report needs a Path root, got {root!r}. Fix: pass the project directory."
    assert isinstance(plan, Plan), f"build_report needs a Plan, got {plan!r}. Fix: load the plan."
    text = three_arm_report_text(root, plan) if is_three_arm(plan) else report_text(report_input(root, plan))
    assert text.endswith("\n") and text.startswith("# Report"), f"build_report built {text!r}"
    return text


def report_location(cwd, argument):
    assert isinstance(cwd, Path), f"report_location needs a Path, got {cwd!r}. Fix: pass the current directory."
    assert argument, "report_location needs a plan directory or plan file. Fix: pass one."
    target = inside(cwd, argument)
    root, name = (target, PLAN_FILE) if target.is_dir() else (cwd, argument)
    assert root.is_dir(), f"report_location chose {root}, which is not a directory"
    return root, name
