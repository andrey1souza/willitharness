import json
from dataclasses import dataclass
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
ARM_KEYS = ("label", "role", "overlay")


class PlanError(Exception):
    pass


@dataclass(frozen=True)
class Arm:
    label: str
    role: str
    overlay: str


@dataclass(frozen=True)
class Plan:
    name: str
    budget_usd: float
    run_cap_usd: float
    reps: int
    max_retries: int
    arms: tuple[Arm, ...]


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
    arm = Arm(entry["label"], role, entry["overlay"])
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
        arms=arms,
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
    assert isinstance(loaded, Plan), f"load_plan returned {loaded!r}, not a Plan"
    return loaded
