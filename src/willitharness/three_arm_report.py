from dataclasses import dataclass
from pathlib import Path

from willitharness.artifacts import RUNS_DIR, TRANSCRIPT_NAME
from willitharness.component_arms import ARM_COMPONENT, ARM_NOTHING, ARM_PLACEBO, ARM_PROMPT
from willitharness.counts import Counts
from willitharness.decide_plan import DecideRefused, three_arm_folder
from willitharness.detectors import calls_of
from willitharness.outcomes import TARGET_OUTCOME, cell_counts, outcome_value
from willitharness.paths import inside
from willitharness.placebo import content_verdict, content_verdict_text
from willitharness.plan import Plan
from willitharness.store import Cell, RunState, latest_by_run, load_records
from willitharness.stream import RESULT_EVENT, TURNS_FIELD, load_event
from willitharness.three_arm import arm_verdict_text, three_arm_verdict
from willitharness.verdict import MIN_RUNS, verdict_of
from willitharness.vocabulary import ArmVerdict, ContentVerdict, Verdict

REMOVE_MIN_RUNS = 20
REMOVE_CANDIDATE_TEXT = "remove candidate"
NEEDS_MORE_RUNS_TEXT = "NeedsMoreRuns: removal needs at least {minimum} runs in each arm"
SKILL_TOOL = "Skill"
SKILL_CHANNEL = "skill"
THREE_ARMS = (ARM_COMPONENT, ARM_PROMPT, ARM_NOTHING)
BULLET = "- "
NOISE_LINE = f"Noise on arm {ARM_COMPONENT} is not measured separately."
NO_COUNTS = Counts(0, 0)
NO_RUNS_REFUSAL = "plan {name} has no stored runs. Rule: a decision counts stored runs. Fix: run the plan first."


@dataclass(frozen=True)
class TaskArms:
    task: str
    other_label: str
    component: Counts
    other: Counts
    nothing: Counts


@dataclass(frozen=True)
class RunFacts:
    arm: str
    task: str
    violated: bool
    cost: float
    fired: bool | None
    turns: int | None


def is_three_arm(plan):
    assert isinstance(plan, Plan), f"is_three_arm needs a Plan, got {plan!r}. Fix: load the plan."
    found = set(THREE_ARMS) <= {arm.label for arm in plan.arms}
    assert isinstance(found, bool), f"is_three_arm returned {found!r}, not a bool"
    return found


def task_arms(records, other_label):
    assert isinstance(records, tuple), f"task_arms needs a tuple of records, got {type(records).__name__}. Fix: pass load_records output."
    counts = cell_counts(records, TARGET_OUTCOME)
    tasks = sorted({cell.task for cell in counts})
    labels = (ARM_COMPONENT, other_label, ARM_NOTHING)
    found = tuple(TaskArms(task, other_label, *(counts.get(Cell(arm, task), NO_COUNTS) for arm in labels)) for task in tasks)
    assert len(found) == len(tasks), f"task_arms lost a task: {found!r}"
    return found


def has_placebo(plan):
    assert isinstance(plan, Plan), f"has_placebo needs a Plan, got {plan!r}. Fix: load the plan."
    found = ARM_PLACEBO in {arm.label for arm in plan.arms}
    assert isinstance(found, bool), f"has_placebo returned {found!r}, not a bool"
    return found


def verdict_of_placebo(arms):
    assert isinstance(arms, TaskArms) and arms.other_label == ARM_PLACEBO, f"verdict_of_placebo needs a TaskArms of arm {ARM_PLACEBO}, got {arms!r}. Fix: build it with task_arms."
    verdict = content_verdict(arms.component, arms.other, arms.nothing)
    assert verdict in ContentVerdict, f"verdict_of_placebo gave {verdict!r}, which is not a ContentVerdict"
    return verdict


def placebo_decision_line(arms):
    assert isinstance(arms, TaskArms), f"placebo_decision_line needs a TaskArms, got {arms!r}. Fix: build it with task_arms."
    line = f"content {arms.task} {ARM_COMPONENT} against {ARM_PLACEBO}: {content_verdict_text(verdict_of_placebo(arms))} ({arms_text(arms)})"
    assert arms.task in line and arms_text(arms) in line, f"placebo_decision_line lost the task or the counts: {line!r}"
    return line


def placebo_lines(found):
    assert found, "placebo_lines needs tasks. Fix: build them with task_arms."
    lines = ["## Content against filler", "", *(f"{BULLET}{arms.task}: {arms_text(arms)}. Verdict: {content_verdict_text(verdict_of_placebo(arms))}" for arms in found)]
    assert len(lines) == len(found) + 2, f"placebo_lines dropped a task: {lines!r}"
    return lines


def arms_text(arms):
    assert isinstance(arms, TaskArms), f"arms_text needs a TaskArms, got {arms!r}. Fix: build it with task_arms."
    parts = ((ARM_COMPONENT, arms.component), (arms.other_label, arms.other), (ARM_NOTHING, arms.nothing))
    text = ", ".join(f"arm {label} {counts.successes} of {counts.runs} runs" for label, counts in parts)
    assert all(f"arm {label} " in text for label, _ in parts), f"arms_text lost an arm: {text!r}"
    return text


def verdict_of_arms(arms):
    assert isinstance(arms, TaskArms), f"verdict_of_arms needs a TaskArms, got {arms!r}. Fix: build it with task_arms."
    verdict = three_arm_verdict(arms.component, arms.other, arms.nothing)
    assert verdict in ArmVerdict, f"verdict_of_arms gave {verdict!r}, which is not an ArmVerdict"
    return verdict


def decision_text(arms):
    assert REMOVE_MIN_RUNS >= MIN_RUNS, f"REMOVE_MIN_RUNS {REMOVE_MIN_RUNS} is below MIN_RUNS {MIN_RUNS}. Rule: removal needs at least the runs a verdict needs. Fix: raise REMOVE_MIN_RUNS."
    verdict = verdict_of_arms(arms)
    enough = min(arms.component.runs, arms.other.runs, arms.nothing.runs) >= REMOVE_MIN_RUNS
    if verdict is not ArmVerdict.DELETE_CANDIDATE:
        text = arm_verdict_text(verdict)
    elif enough:
        text = REMOVE_CANDIDATE_TEXT
    else:
        text = NEEDS_MORE_RUNS_TEXT.format(minimum=REMOVE_MIN_RUNS)
    assert (text == REMOVE_CANDIDATE_TEXT) == (verdict is ArmVerdict.DELETE_CANDIDATE and enough), f"remove candidate printed with too few runs: {text!r} for {arms!r}"
    return text


def three_arm_decision_line(arms):
    assert isinstance(arms, TaskArms), f"three_arm_decision_line needs a TaskArms, got {arms!r}. Fix: build it with task_arms."
    line = f"decision {arms.task} {ARM_COMPONENT}: {decision_text(arms)} ({arms_text(arms)})"
    assert arms.task in line and arms_text(arms) in line, f"decision_line lost the task or the counts: {line!r}"
    return line


def three_arm_decision_lines(root, plan):
    assert isinstance(root, Path), f"three_arm_decision_lines needs a Path root, got {root!r}. Fix: pass the project directory."
    assert is_three_arm(plan), f"plan {plan.name} is not three-arm. Rule: it needs arms {', '.join(THREE_ARMS)}. Fix: add the missing arm."
    folder = three_arm_folder(root, plan)
    records = load_records(folder)
    lines = tuple(three_arm_decision_line(arms) for arms in task_arms(records, ARM_PROMPT))
    if not lines:
        raise DecideRefused(NO_RUNS_REFUSAL.format(name=plan.name))
    return (*lines, *(placebo_decision_line(arms) for arms in task_arms(records, ARM_PLACEBO))) if has_placebo(plan) else lines


def turns_of(lines):
    assert not isinstance(lines, (str, bytes)), f"turns_of needs one line per item, got {type(lines).__name__}. Fix: split the transcript first."
    turns = [load_event(line).get(TURNS_FIELD) for line in lines if load_event(line).get("type") == RESULT_EVENT]
    last = turns[-1] if turns else None
    result = last if isinstance(last, int) and not isinstance(last, bool) else None
    assert result is None or result == last, f"turns_of changed {last!r} into {result!r}"
    return result


def run_facts(folder, records):
    assert isinstance(folder, Path), f"run_facts needs the plan folder as a Path, got {folder!r}. Fix: use lifecycle_dir."
    assert isinstance(records, tuple), f"run_facts needs a tuple of records, got {type(records).__name__}. Fix: pass load_records output."
    found = []
    usable = (run for run in latest_by_run(records).values() if run.state is RunState.RECORDED_USABLE and run.usable.get(TARGET_OUTCOME))
    for run in sorted(usable, key=lambda item: item.run_id):
        transcript = inside(folder, f"{RUNS_DIR}/{run.arm}/{run.task}/{run.rep}/{TRANSCRIPT_NAME.format(attempt=run.attempt)}")
        lines = transcript.read_text().splitlines() if transcript.is_file() else None
        fired = None if lines is None else any(call.tool == SKILL_TOOL for call in calls_of(lines))
        found.append(RunFacts(run.arm, run.task, outcome_value(run, TARGET_OUTCOME), run.cost_usd, fired, None if lines is None else turns_of(lines)))
    assert len(found) <= len(records), f"run_facts invented runs: {len(found)} from {len(records)} records"
    return tuple(found)


def smallest_detectable_drop(other, component_runs):
    assert min(other.runs, component_runs) >= MIN_RUNS, f"a drop is only measurable from {MIN_RUNS} runs per arm, got {other.runs} and {component_runs}. Fix: check the runs first."
    drops = [other.rate() - violations / component_runs for violations in range(component_runs + 1) if verdict_of(other, Counts(violations, component_runs)) is Verdict.FIRST_HIGHER]
    smallest = min(drops, default=None)
    assert smallest is None or smallest > 0, f"smallest_detectable_drop gave {smallest} for {other!r} and {component_runs} runs. Rule: a detected drop is above 0."
    return smallest


def three_arm_verdict_lines(found):
    assert found, "three_arm_verdict_lines needs tasks. Fix: build them with task_arms."
    lines = ["## Three-arm verdict", "", *(f"{BULLET}{arms.task}: {arms_text(arms)}. Verdict: {arm_verdict_text(verdict_of_arms(arms))}" for arms in found), f"{BULLET}{NOISE_LINE}"]
    assert len(lines) == len(found) + 3, f"three_arm_verdict_lines dropped a task: {lines!r}"
    return lines


def fired_effect_lines(fired, nothing):
    assert isinstance(nothing, Counts), f"fired_effect_lines needs the counts of arm N, got {nothing!r}. Fix: pass Counts."
    if not fired:
        return [f"Effect when the skill fires: not measured. No run of arm {ARM_COMPONENT} fired the skill."]
    violated = Counts(sum(fact.violated for fact in fired), len(fired))
    lines = [
        f"Effect when the skill fires: arm {ARM_COMPONENT} violated in {violated.successes} of {violated.runs} runs that fired. "
        f"Arm {ARM_NOTHING} violated in {nothing.successes} of {nothing.runs} runs.",
        f"Arm {ARM_NOTHING} against the fired runs of arm {ARM_COMPONENT}: {verdict_of(nothing, violated)}.",
    ]
    assert len(lines) == 2, f"fired_effect_lines built {lines!r}"
    return lines


def trigger_body(channel, facts):
    assert channel, "trigger_body needs the channel of arm C. Fix: read it from the plan."
    assert isinstance(facts, tuple), f"trigger_body needs a tuple of run facts, got {type(facts).__name__}. Fix: build them with run_facts."
    measured = [fact for fact in facts if fact.arm == ARM_COMPONENT and fact.fired is not None]
    fired = [fact for fact in measured if fact.fired]
    nothing = [fact for fact in facts if fact.arm == ARM_NOTHING]
    if channel != SKILL_CHANNEL:
        return [f"Arm {ARM_COMPONENT} is not a skill. A trigger rate does not apply."]
    if not measured:
        return [f"Trigger not measured. No usable run of arm {ARM_COMPONENT} has a stored transcript."]
    rate = f"Trigger rate of arm {ARM_COMPONENT}: {len(fired)} of {len(measured)} runs ({len(fired) / len(measured):.0%}). A run fired when its transcript has a {SKILL_TOOL} tool call."
    body = [rate, *fired_effect_lines(fired, Counts(sum(fact.violated for fact in nothing), len(nothing)))]
    assert body[0].startswith("Trigger rate"), f"trigger_body lost the trigger rate: {body!r}"
    return body


def trigger_lines(plan, facts):
    assert isinstance(plan, Plan), f"trigger_lines needs a Plan, got {plan!r}. Fix: load the plan."
    channel = next(arm.channel for arm in plan.arms if arm.label == ARM_COMPONENT)
    lines = ["## Trigger", "", *(f"{BULLET}{line}" for line in trigger_body(channel, facts))]
    assert len(lines) >= 3, f"trigger_lines built no body: {lines!r}"
    return lines


def arm_cost_turns_line(arm, facts):
    assert arm in (*THREE_ARMS, ARM_PLACEBO), f"arm_cost_turns_line needs one of {THREE_ARMS} or {ARM_PLACEBO}, got {arm!r}. Fix: pass a plan arm label."
    runs = [fact for fact in facts if fact.arm == arm]
    if not runs:
        return f"{BULLET}Arm {arm}: no usable runs."
    measured = [fact.turns for fact in runs if fact.turns is not None]
    turns = f"mean turns {sum(measured) / len(measured):.1f} over {len(measured)} runs" if measured else "turns not measured, no stored transcript has a result line"
    line = f"{BULLET}Arm {arm}: {len(runs)} runs, mean cost ${sum(fact.cost for fact in runs) / len(runs):.4f}, {turns}."
    assert f"Arm {arm}:" in line, f"arm_cost_turns_line lost the arm: {line!r}"
    return line


def cost_turns_lines(facts, arm_labels):
    assert isinstance(facts, tuple), f"cost_turns_lines needs a tuple of run facts, got {type(facts).__name__}. Fix: build them with run_facts."
    lines = ["## Turns and cost per arm", "", *(arm_cost_turns_line(arm, facts) for arm in arm_labels)]
    assert len(lines) == len(arm_labels) + 2, f"cost_turns_lines dropped an arm: {lines!r}"
    return lines


def detectable_text(other, component_runs):
    assert isinstance(other, Counts), f"detectable_text needs Counts, got {other!r}. Fix: pass the counts of arm P or N."
    assert component_runs >= 0, f"detectable_text got {component_runs} runs. Rule: a run count is not negative. Fix: pass the runs of arm C."
    if min(other.runs, component_runs) < MIN_RUNS:
        text = f"not measurable. An arm has fewer than {MIN_RUNS} runs."
    else:
        drop = smallest_detectable_drop(other, component_runs)
        text = "no drop is detectable with these runs." if drop is None else f"the runs could detect an absolute drop of {drop:.1%} in the violation rate, from {other.rate():.0%}."
    assert text, "detectable_text built no text"
    return text


def detectable_lines(found):
    assert found, "detectable_lines needs tasks. Fix: build them with task_arms."
    items = [
        f"{BULLET}{arms.task}, arm {ARM_COMPONENT} against arm {label}: {detectable_text(other, arms.component.runs)}"
        for arms in found
        for label, other in ((ARM_PROMPT, arms.other), (ARM_NOTHING, arms.nothing))
    ]
    lines = ["## Smallest detectable change", "", *items]
    assert len(items) == 2 * len(found), f"detectable_lines dropped a comparison: {lines!r}"
    return lines


def decision_section(found):
    assert found, "decision_section needs tasks. Fix: build them with task_arms."
    lines = ["## Decision", "", *(f"{BULLET}{three_arm_decision_line(arms)}" for arms in found)]
    assert len(lines) == len(found) + 2, f"decision_section dropped a task: {lines!r}"
    return lines


def three_arm_sections(folder, plan, records):
    assert isinstance(plan, Plan) and is_three_arm(plan), f"three_arm_sections needs a three-arm plan, got {plan!r}. Fix: check is_three_arm first."
    found = task_arms(records, ARM_PROMPT)
    facts = run_facts(folder, records)
    labels = (*THREE_ARMS, ARM_PLACEBO) if has_placebo(plan) else THREE_ARMS
    placebo = (placebo_lines(task_arms(records, ARM_PLACEBO)),) if has_placebo(plan) else ()
    sections = (three_arm_verdict_lines(found), *placebo, trigger_lines(plan, facts), cost_turns_lines(facts, labels), detectable_lines(found), decision_section(found))
    assert all(section[0].startswith("## ") for section in sections), f"a section lacks its heading: {sections!r}"
    return sections
