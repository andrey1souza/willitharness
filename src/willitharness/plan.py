import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from willitharness.paths import PathOutsideRoot, inside

DEFAULT_REPS = 20
MAX_RETRIES = 2
MIN_PROBE_RUNS = 3
SCHEMA_VERSION = 1
ROLE_LEAVE_ONE_OUT = "leave_one_out"
ROLE_RULE = "rule"
ROLE_GUARD_ONLY = "guard_only"
NOISE_ROLE_PREFIX = "noise_of:"
FIXED_ROLES = frozenset({ROLE_LEAVE_ONE_OUT, ROLE_RULE, ROLE_GUARD_ONLY})
CHANNELS = ("file", "hook", "skill", "system_prompt")
DEFAULT_CHANNEL = "file"
ARM_KEYS = ("label", "role", "overlay")
BUDGET_KEY = "budget_usd"
TARGET_OUTCOME = "attempted_violation"
KIND_FORBIDDEN = "forbidden"
KIND_REQUIRED = "required"
DETECTOR_KINDS = (KIND_FORBIDDEN, KIND_REQUIRED)
POINT_FIRST_EDIT = "first_edit"
POINT_FINAL_ANSWER = "final_answer"
POINTS = (POINT_FIRST_EDIT, POINT_FINAL_ANSWER)
CHECK_CALLS_CONTAIN = "calls_contain"
COMPLETED_CHECKS = (CHECK_CALLS_CONTAIN,)
RULE_KEYS = ("id", "file", "section")


class PlanError(Exception):
    pass


@dataclass(frozen=True)
class Arm:
    label: str
    role: str
    overlay: str
    channel: str


@dataclass(frozen=True)
class Detector:
    kind: str
    action: str
    before: str = ""


@dataclass(frozen=True)
class Rule:
    id: str
    file: str
    section: str
    target_outcome: str
    detector: Detector
    offered_alternatives: tuple[str, ...]


@dataclass(frozen=True)
class CompletedCheck:
    kind: str
    command: str


@dataclass(frozen=True)
class Task:
    id: str
    completed_check: CompletedCheck


@dataclass(frozen=True)
class Plan:
    name: str
    budget_usd: float
    run_cap_usd: float
    reps: int
    max_retries: int
    world: str
    arms: tuple[Arm, ...]
    rule: Rule | None = None
    tasks: tuple[Task, ...] = ()


def plan_fingerprint(plan):
    assert isinstance(plan, Plan), f"plan_fingerprint needs a Plan, got {plan!r}. Fix: load the plan."
    content = {key: value for key, value in asdict(plan).items() if key != BUDGET_KEY}
    assert BUDGET_KEY not in content, f"the fingerprint of plan {plan.name} still holds {BUDGET_KEY}. Rule: A-FP, the fingerprint leaves the budget out."
    return hashlib.sha256(json.dumps(content, sort_keys=True).encode()).hexdigest()


def has_guard_arm(plan):
    assert isinstance(plan, Plan), f"has_guard_arm needs a Plan, got {plan!r}. Fix: load the plan."
    assert plan.arms, f"plan {plan.name} has no arms. Rule: a plan needs arms. Fix: load the plan with load_plan."
    found = any(arm.role == ROLE_GUARD_ONLY for arm in plan.arms)
    assert isinstance(found, bool), f"has_guard_arm returned {found!r}, not a bool"
    return found


def noise_target(role):
    assert isinstance(role, str), f"a role is text, got {role!r}. Fix: write the role as a string in the plan."
    assert role, "a role cannot be empty. Fix: use one of rule, leave_one_out, guard_only or noise_of:<label>."
    return role[len(NOISE_ROLE_PREFIX):] if role.startswith(NOISE_ROLE_PREFIX) else None


def read_arm(entry):
    assert entry is not None, "read_arm got None. Rule: each arm is an object. Fix: remove the empty item from the arms list."
    if not isinstance(entry, dict):
        raise PlanError(f"an arm must be an object, got {entry!r}. Rule: each arm has label, role and overlay. Fix: write each arm as an object.")
    missing = [key for key in ARM_KEYS if not isinstance(entry.get(key), str) or not entry.get(key)]
    if missing:
        raise PlanError(f"arm {entry!r} lacks {missing}. Rule: each arm has label, role and overlay as text. Fix: add the missing keys.")
    role = entry["role"]
    if noise_target(role) is None and role not in FIXED_ROLES:
        raise PlanError(f"arm {entry['label']} has role {role!r}. Rule: a role is rule, leave_one_out, guard_only or noise_of:<label>. Fix: correct the role.")
    channel = entry.get("channel", DEFAULT_CHANNEL)
    if channel not in CHANNELS:
        raise PlanError(
            f"arm {entry['label']} has channel {channel!r}, which is not one of {', '.join(CHANNELS)}. "
            f"Rule: a channel says how the rule text reaches the agent. Fix: set channel to one of them or remove it for {DEFAULT_CHANNEL}."
        )
    arm = Arm(entry["label"], role, entry["overlay"], channel)
    assert arm.label == entry["label"] and arm.role == role, f"read_arm changed the entry {entry!r} into {arm!r}"
    return arm


def check_arms(arms):
    assert arms, "check_arms got no arms. Rule: a plan needs arms. Fix: add arms to the plan."
    assert all(isinstance(arm, Arm) for arm in arms), f"every arm must be an Arm, got {arms!r}"
    labels = [arm.label for arm in arms]
    duplicates = sorted({label for label in labels if labels.count(label) > 1})
    if duplicates:
        raise PlanError(f"arm labels {duplicates} repeat. Rule: a label names one arm. Fix: give each arm its own label.")
    leave_one_out = [arm.label for arm in arms if arm.role == ROLE_LEAVE_ONE_OUT]
    loo_label = leave_one_out[0] if leave_one_out else None
    if len(leave_one_out) > 1:
        raise PlanError(f"arms {leave_one_out} are all leave_one_out. Rule: a plan has one LOO arm. Fix: keep one and change the others.")
    for arm in arms:
        target = noise_target(arm.role)
        if target is None:
            continue
        if not leave_one_out:
            raise PlanError(f"arm {arm.label} repeats {target}, but the plan has no LOO arm. Rule: a noise pair repeats the LOO arm. Fix: give arm {target} the role leave_one_out.")
        if target != loo_label:
            raise PlanError(
                f"noise pair must repeat the LOO arm {loo_label}; {arm.label} repeats {target}. "
                f"Fix: set the role of {arm.label} to noise_of:{loo_label}."
            )


def text_field(entry, key, owner):
    assert isinstance(entry, dict), f"text_field needs an object, got {entry!r}. Fix: pass the parsed {owner}."
    assert key, f"text_field needs a key for {owner}. Fix: name the field to read."
    value = entry.get(key)
    if not isinstance(value, str) or not value.strip():
        raise PlanError(f"{owner} has {key} {value!r}. Rule: {key} is non-empty text. Fix: set {key} in the {owner}.")
    assert value.strip(), f"{owner} {key} came out empty after the check"
    return value


def read_detector(entry):
    assert entry is not None, "read_detector got None. Rule: a rule has a detector. Fix: add detector to the rule."
    if isinstance(entry, str):
        entry = {"kind": KIND_FORBIDDEN, "action": entry}
    if not isinstance(entry, dict):
        raise PlanError(f"detector is {entry!r}. Rule: a detector is a command name or an object with kind and action. Fix: write the detector as text or an object.")
    kind = entry.get("kind")
    if kind not in DETECTOR_KINDS:
        raise PlanError(f"detector kind is {kind!r}. Rule: a kind is {', '.join(DETECTOR_KINDS)}. Fix: set kind to one of them.")
    action = text_field(entry, "action", "detector")
    before = entry.get("before", "")
    if kind == KIND_REQUIRED and before not in POINTS:
        raise PlanError(f"required detector has before {before!r}. Rule: a required action names its point, one of {', '.join(POINTS)}. Fix: set before.")
    if kind == KIND_FORBIDDEN and before:
        raise PlanError(f"forbidden detector has before {before!r}. Rule: only a required detector names a point. Fix: remove before.")
    detector = Detector(kind, action, before)
    assert detector.kind in DETECTOR_KINDS and detector.action, f"read_detector built {detector!r} from {entry!r}"
    return detector


def read_rule(entry):
    assert entry is not None, "read_rule got None. Fix: pass the rule object."
    if not isinstance(entry, dict):
        raise PlanError(f"rule is {entry!r}. Rule: a rule is an object with id, file, section, target_outcome and detector. Fix: write the rule as an object.")
    id_, file, section = (text_field(entry, key, "rule") for key in RULE_KEYS)
    if entry.get("target_outcome") != TARGET_OUTCOME:
        raise PlanError(f"rule {id_} has target_outcome {entry.get('target_outcome')!r}. Rule: a detector decides {TARGET_OUTCOME}. Fix: set target_outcome to {TARGET_OUTCOME}.")
    alternatives = entry.get("offered_alternatives", [])
    if not isinstance(alternatives, list) or not all(isinstance(item, str) and item for item in alternatives):
        raise PlanError(f"rule {id_} has offered_alternatives {alternatives!r}. Rule: alternatives are a list of text. Fix: write a list of commands.")
    rule = Rule(id_, file, section, TARGET_OUTCOME, read_detector(entry.get("detector")), tuple(alternatives))
    assert rule.detector.action, f"rule {id_} has no detector action"
    return rule


def read_check(entry, task_id):
    assert task_id, "read_check needs the task id. Fix: pass the id of the task."
    if not isinstance(entry, dict) or entry.get("kind") not in COMPLETED_CHECKS:
        raise PlanError(f"task {task_id} has completed_check {entry!r}. Rule: a check is an object with kind one of {', '.join(COMPLETED_CHECKS)} and a command. Fix: correct completed_check.")
    check = CompletedCheck(entry["kind"], text_field(entry, "command", f"completed_check of task {task_id}"))
    assert check.kind in COMPLETED_CHECKS, f"read_check built {check!r}"
    return check


def read_tasks(raw):
    assert raw is not None, "read_tasks got None. Fix: pass the tasks list."
    if not isinstance(raw, list):
        raise PlanError(f"tasks is {raw!r}. Rule: tasks is a list of objects with id and completed_check. Fix: write a list.")
    for entry in raw:
        if not isinstance(entry, dict):
            raise PlanError(f"a task must be an object, got {entry!r}. Fix: write each task as an object with id and completed_check.")
    tasks = tuple(Task(text_field(entry, "id", "task"), read_check(entry.get("completed_check"), entry.get("id"))) for entry in raw)
    ids = [task.id for task in tasks]
    duplicates = sorted({item for item in ids if ids.count(item) > 1})
    if duplicates:
        raise PlanError(f"task ids {duplicates} repeat. Rule: an id names one task. Fix: give each task its own id.")
    assert len(tasks) == len(raw), f"read_tasks lost tasks: {len(raw)} in, {len(tasks)} out"
    return tasks


def positive_number(data, key):
    assert isinstance(data, dict), f"positive_number needs the plan object, got {data!r}. Fix: pass the parsed plan."
    assert key, "positive_number needs a key. Fix: name the plan field to read."
    value = data.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise PlanError(f"{key} is {value!r}. Rule: {key} is a number above 0. Fix: set {key} in the plan.")
    result = float(value)
    assert result > 0, f"{key} came out as {result}. Rule: the check above keeps it above 0."
    return result


def whole_number(data, key, default, minimum):
    assert isinstance(data, dict), f"whole_number needs the plan object, got {data!r}. Fix: pass the parsed plan."
    assert default >= minimum, f"the default {default} for {key} is below the minimum {minimum}. Fix: correct the constants."
    value = data.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise PlanError(f"{key} is {value!r}. Rule: {key} is a whole number of at least {minimum}. Fix: set {key} in the plan or remove it for the default {default}.")
    assert value >= minimum, f"{key} came out as {value}. Rule: the check above keeps it at or above {minimum}."
    return value


def load_plan(data):
    if not isinstance(data, dict):
        raise PlanError(f"a plan must be an object, got {type(data).__name__}. Fix: write the plan as a JSON object.")
    if data.get("schema") != SCHEMA_VERSION:
        raise PlanError(f"schema is {data.get('schema')!r}. Rule: this version reads schema {SCHEMA_VERSION}. Fix: set schema to {SCHEMA_VERSION}.")
    name = data.get("name")
    if not isinstance(name, str) or not name:
        raise PlanError(f"name is {name!r}. Rule: a plan has a name. Fix: set name in the plan.")
    world = data.get("world")
    if not isinstance(world, str) or not world:
        raise PlanError(f"world is {world!r}. Rule: a plan names its world directory. Fix: set world in the plan, for example \"world/\".")
    budget = positive_number(data, "budget_usd")
    run_cap = positive_number(data, "run_cap_usd")
    if run_cap > budget:
        raise PlanError(f"run_cap_usd {run_cap} is above budget_usd {budget}. Rule: one run cannot cost more than the budget. Fix: lower run_cap_usd or raise budget_usd.")
    raw_arms = data.get("arms")
    if not isinstance(raw_arms, list) or not raw_arms:
        raise PlanError(f"arms is {raw_arms!r}. Rule: a plan has a list of arms. Fix: add arms to the plan.")
    arms = tuple(read_arm(entry) for entry in raw_arms)
    check_arms(arms)
    loaded = Plan(
        name=name,
        budget_usd=budget,
        run_cap_usd=run_cap,
        reps=whole_number(data, "reps", DEFAULT_REPS, 1),
        max_retries=whole_number(data, "max_retries", MAX_RETRIES, 0),
        world=world,
        arms=arms,
        rule=read_rule(data["rule"]) if "rule" in data else None,
        tasks=read_tasks(data.get("tasks", [])),
    )
    assert loaded.run_cap_usd <= loaded.budget_usd, f"load_plan built {loaded!r}, but one run may not cost more than the budget"
    assert len(loaded.arms) == len(raw_arms), f"load_plan lost arms: {len(raw_arms)} in, {len(loaded.arms)} out"
    return loaded


def read_plan(root, name):
    assert isinstance(root, Path), f"read_plan needs a Path root, got {root!r}. Fix: pass pathlib.Path."
    assert name, "read_plan needs a plan file name. Fix: pass the path of a plan.json."
    try:
        path = inside(root, name)
    except PathOutsideRoot as error:
        raise PlanError(str(error)) from error
    if not path.is_file():
        raise PlanError(f"plan file {path} does not exist. Rule: a plan is a JSON file. Fix: pass the path of a plan.json.")
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as error:
        raise PlanError(f"{path} is not valid JSON ({error}). Rule: a plan is JSON. Fix: correct the file.") from error
    loaded = load_plan(data)
    try:
        inside(root, loaded.world)
    except PathOutsideRoot as error:
        raise PlanError(f"world {loaded.world!r} is outside the project. Rule: a plan's world stays inside the project root. Fix: point world at a directory under the project.") from error
    assert isinstance(loaded, Plan), f"load_plan returned {loaded!r}, not a Plan"
    return loaded
