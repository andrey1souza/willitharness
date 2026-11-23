import json
from dataclasses import dataclass, field

from analysis_site import RUN_COST_USD, TARGET
from files import write_tree
from lifecycle_site import SCHEMA_VERSION, TASK_NAME, TASK_PROMPT, WORLD_NAME, reach_every_arm, validate_site

from willitharness.artifacts import RUNS_DIR, TRANSCRIPT_NAME
from willitharness.component_arms import ARM_COMPONENT, ARM_NOISE, ARM_NOTHING, ARM_PLACEBO, ARM_PROMPT
from willitharness.lifecycle import PlanSite, PlanState, lifecycle_dir, write_state
from willitharness.plan import load_plan
from willitharness.real_runner import AGENT_RECORD
from willitharness.store import Record, RunState, append_record, run_id_of, Cell
from willitharness.vocabulary import Reach

THREE_ARM_ROLES = {ARM_COMPONENT: "rule", ARM_PROMPT: "rule", ARM_NOTHING: "leave_one_out", ARM_NOISE: f"noise_of:{ARM_NOTHING}"}
FAKE_MODEL = "fake-model-1"
FAKE_VERSION = "9.9.9 (Fake Claude)"
FIRED_TURNS = 4
PLAIN_TURNS = 3
SKILL_NAME = "pkill-guard"
PLACEBO_CHANNEL = "system_prompt"


@dataclass(frozen=True)
class ArmShape:
    runs: int
    violating: frozenset = field(default_factory=frozenset)
    fired: frozenset = field(default_factory=frozenset)
    transcripts: bool = True


def first(count):
    return frozenset(range(1, count + 1))


def three_arm_data(channel, name="demo"):
    arms = [{"label": label, "role": role, "overlay": f"{label}.md"} for label, role in THREE_ARM_ROLES.items()]
    arms[0]["channel"] = channel
    return {"schema": SCHEMA_VERSION, "name": name, "world": WORLD_NAME, "budget_usd": 100.0, "run_cap_usd": 1.0, "reps": 20, "max_retries": 2, "arms": arms}


def transcript_lines(fired, turns):
    skill = [{"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Skill", "input": {"skill": SKILL_NAME}}]}}] if fired else []
    events = [
        {"type": "system", "subtype": "init", "model": FAKE_MODEL},
        *skill,
        {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Bash", "input": {"command": "ls"}}]}},
        {"type": "result", "subtype": "success", "is_error": False, "total_cost_usd": RUN_COST_USD, "num_turns": turns},
    ]
    return "\n".join(json.dumps(event, sort_keys=True) for event in events) + "\n"


def store_arm(site, arm, shape):
    folder = lifecycle_dir(site.root, site.plan)
    for rep in range(1, shape.runs + 1):
        cell = Cell(arm, TASK_NAME)
        usable = {TARGET: True, "completed": True}
        outcome = {TARGET: rep in shape.violating, "completed": True}
        append_record(folder, Record(run_id_of(cell, rep, 1), arm, TASK_NAME, rep, 1, RunState.RECORDED_USABLE, usable, RUN_COST_USD, outcome))
        if shape.transcripts:
            fired = rep in shape.fired
            path = folder / RUNS_DIR / arm / TASK_NAME / str(rep) / TRANSCRIPT_NAME.format(attempt=1)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(transcript_lines(fired, FIRED_TURNS if fired else PLAIN_TURNS))


@dataclass(frozen=True)
class SiteOptions:
    state: PlanState = PlanState.ANALYZED
    channel: str = "skill"
    extra_arms: tuple = ()
    placebo: bool = False


def three_arm_site(root, shapes, options=SiteOptions()):
    data = three_arm_data(options.channel)
    if options.placebo:
        data["arms"].append({"label": ARM_PLACEBO, "role": "rule", "overlay": f"{ARM_PLACEBO}.md", "channel": PLACEBO_CHANNEL})
    data["arms"] += [{"label": label, "role": "guard_only", "overlay": f"{label}.md"} for label in options.extra_arms]
    write_tree(root, {"plan.json": json.dumps(data), f"{WORLD_NAME}/tasks.txt": f"{TASK_NAME}: ls\n", f"{WORLD_NAME}/real.txt": "ls\n", f"{WORLD_NAME}/prompts/{TASK_NAME}.txt": TASK_PROMPT})
    site = PlanSite(root, load_plan(data), root / WORLD_NAME)
    validate_site(site)
    reach_every_arm(site, Reach.LOADED)
    for arm, shape in shapes.items():
        store_arm(site, arm, shape)
    folder = lifecycle_dir(site.root, site.plan)
    (folder / AGENT_RECORD).write_text(json.dumps({"claude_version": FAKE_VERSION}))
    write_state(folder, options.state)
    return site
