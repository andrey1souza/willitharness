import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from willitharness.component_arms import ARM_COMPONENT, ARM_NOISE, ARM_NOTHING, ARM_PLACEBO, ARM_PROMPT
from willitharness.load_report import (
    CONTEXT_EVENTS,
    NO_MATCHER,
    SETTINGS_FOLDER,
    SKILL_FILE,
    SKILLS_FOLDER,
    HOOK_TIMEOUT_SECONDS,
    LoadRefused,
    configured_hooks,
    hook_output,
    read_file,
    split_skill,
)
from willitharness.plan import (
    BUDGET_KEY,
    NOISE_ROLE_PREFIX,
    ROLE_LEAVE_ONE_OUT,
    ROLE_RULE,
    SCHEMA_VERSION,
    TARGET_OUTCOME,
    PlanError,
    load_plan,
)
from willitharness.stubs import SYSTEM_PROMPT_NAME

PLAN_FILE = "plan.json"
ARMS_FOLDER = "arms"
WORLD_FOLDER = "world/"
CHANNEL_FILE = "file"
CHANNEL_SKILL = "skill"
CHANNEL_HOOK = "hook"
CHANNEL_SYSTEM_PROMPT = "system_prompt"
SKILL_SECTION = "body"
HOOK_TYPE = "command"
FILLER_SENTENCE = "This sentence is filler text and holds no instruction. "
JSON_INDENT = 2
DETECTOR_KEY = "detector"
TASKS_KEY = "tasks"
RULE_KEYS_ORDER = ("id", "file", "section", "target_outcome", DETECTOR_KEY)

MISSING_DETECTOR = (
    "no detector given. Rule: the detector that judges every run is declared in the plan before the first run, and the builder cannot infer it. "
    "Fix: pass --detector with a JSON file that holds a command name, a list of command names or an object with kind and actions."
)
UNREADABLE_DETECTOR = "detector file {path} is not valid JSON ({reason}). Rule: the detector file holds one JSON value. Fix: write a command name, a list of command names or an object with kind and actions."
MISSING_TASKS = (
    "no task file given. Rule: the plan holds the tasks and their completed check, because analyze reads the check of each task. "
    "Fix: pass --task-file with a JSON list of tasks, each with an id and a completed_check."
)
UNREADABLE_TASKS = "task file {path} is not valid JSON ({reason}). Rule: the task file holds one JSON list of tasks. Fix: write a list of objects with id and completed_check."
EMPTY_TASKS = "task file {path} holds no task. Rule: a plan needs at least one task, and the plan has no tasks without one. Fix: add a task with an id and a completed_check."
EXISTING_PLAN = "{path} exists. Rule: a build never overwrites a plan, because runs may depend on it. Fix: pass a new --out folder."
EMPTY_TEXT = "{owner} has no text. Rule: arm P delivers the component text through {name}, and an empty file is refused. Fix: give the component text to inject."
HOOK_NEEDS_RUN = (
    "hook {event} gives its text only when it runs. Rule: a hook is arbitrary code, so the builder never runs one unless asked. "
    "Fix: read the hook command in settings.json, then pass --run-hook."
)
HOOK_NOT_ONE = (
    "{count} command hooks match event {event}. Rule: the builder needs exactly one hook, so arm C is that hook alone. "
    "Fix: keep one command hook for {event} in the project settings."
)
HOOK_NO_TEXT = (
    "hook {event} returned no text for the sample event. Rule: the builder reads text only from {events}, and the hook must exit 0. "
    "Fix: pick a hook on one of those events that exits 0 and prints text."
)
NO_SKILL = "skill {name} is not at {path}. Rule: a skill lives at .claude/skills/<name>/SKILL.md in the project. Fix: pass the name of a skill in the project folder."


class BuildRefused(Exception):
    pass


@dataclass(frozen=True)
class Component:
    name: str
    file: str
    section: str
    channel: str
    text: str
    install: Callable[[Path], None]


@dataclass(frozen=True)
class BuildOptions:
    project: Path
    out: Path
    detector: object
    tasks: list
    budget_usd: float
    run_cap_usd: float
    placebo: bool = False
    plan_name: str = ""


def filler_text(length):
    assert isinstance(length, int) and length > 0, f"filler_text needs a length above 0, got {length!r}. Rule: the filler has the length of the component text."
    text = (FILLER_SENTENCE * (length // len(FILLER_SENTENCE) + 1))[:length]
    assert len(text) == length, f"filler_text made {len(text)} characters, not {length}. Rule: the placebo has the same character count."
    return text


def read_detector_file(path):
    assert isinstance(path, (Path, type(None))), f"read_detector_file needs a Path or None, got {path!r}. Fix: pass the --detector value as a Path."
    if path is None:
        raise BuildRefused(MISSING_DETECTOR)
    try:
        detector = json.loads(read_file(path.resolve().parent, Path(path.name)))
    except json.JSONDecodeError as error:
        raise BuildRefused(UNREADABLE_DETECTOR.format(path=path, reason=type(error).__name__)) from error
    except LoadRefused as error:
        raise BuildRefused(str(error)) from error
    assert detector is not None, f"detector file {path} holds null. Rule: a detector is a command name, a list or an object."
    return detector


def read_task_file(path):
    assert isinstance(path, (Path, type(None))), f"read_task_file needs a Path or None, got {path!r}. Fix: pass the --task-file value as a Path."
    if path is None:
        raise BuildRefused(MISSING_TASKS)
    try:
        tasks = json.loads(read_file(path.resolve().parent, Path(path.name)))
    except json.JSONDecodeError as error:
        raise BuildRefused(UNREADABLE_TASKS.format(path=path, reason=type(error).__name__)) from error
    except LoadRefused as error:
        raise BuildRefused(str(error)) from error
    if not tasks:
        raise BuildRefused(EMPTY_TASKS.format(path=path))
    assert tasks, f"read_task_file returned {tasks!r}. Rule: a plan needs at least one task."
    return tasks


def skill_component(project, name):
    assert isinstance(project, Path) and project.is_dir(), f"skill_component needs the project folder, got {project!r}. Fix: pass the folder."
    assert name, "skill_component needs a skill name. Fix: pass --skill."
    folder = Path(SKILLS_FOLDER) / name
    if not (project / folder / SKILL_FILE).is_file():
        raise BuildRefused(NO_SKILL.format(name=name, path=project / folder / SKILL_FILE))
    try:
        body = split_skill(read_file(project, folder / SKILL_FILE))[1]
    except LoadRefused as error:
        raise BuildRefused(str(error)) from error

    def install(overlay):
        assert overlay.is_dir(), f"{overlay} is not a directory. Rule: an overlay is made before the component is installed."
        installed = shutil.copytree(project / folder, overlay / folder)
        assert (installed / SKILL_FILE).is_file(), f"the install of skill {name} left no {SKILL_FILE} in {installed}"

    component = Component(name, (folder / SKILL_FILE).as_posix(), SKILL_SECTION, CHANNEL_SKILL, body, install)
    assert component.text == body, f"skill_component changed the body of {name}"
    return component


def hook_settings(hook):
    assert hook.command, f"hook {hook!r} has no command. Rule: only command hooks are built."
    group = {"hooks": [{"type": HOOK_TYPE, "command": hook.command}]}
    if hook.matcher != NO_MATCHER:
        group["matcher"] = hook.matcher
    settings = {"hooks": {hook.event: [group]}}
    assert settings["hooks"][hook.event][0]["hooks"][0]["command"] == hook.command, f"hook_settings lost the command of {hook!r}"
    return settings


def hook_component(project, event, run_hook):
    assert isinstance(project, Path) and project.is_dir(), f"hook_component needs the project folder, got {project!r}. Fix: pass the folder."
    assert event, "hook_component needs an event name. Fix: pass --hook."
    if not run_hook:
        raise BuildRefused(HOOK_NEEDS_RUN.format(event=event))
    try:
        matching = [hook for hook in configured_hooks(project) if hook.event == event]
    except LoadRefused as error:
        raise BuildRefused(str(error)) from error
    if len(matching) != 1:
        raise BuildRefused(HOOK_NOT_ONE.format(count=len(matching), event=event))
    hook = matching[0]
    text = hook_output(project, hook, HOOK_TIMEOUT_SECONDS)
    if text is None:
        raise BuildRefused(HOOK_NO_TEXT.format(event=event, events=" or ".join(CONTEXT_EVENTS)))

    def install(overlay):
        assert overlay.is_dir(), f"{overlay} is not a directory. Rule: an overlay is made before the component is installed."
        target = overlay / SETTINGS_FOLDER / hook.source
        target.parent.mkdir(parents=True)
        target.write_text(json.dumps(hook_settings(hook), indent=JSON_INDENT, sort_keys=True) + "\n")
        assert json.loads(target.read_text())["hooks"][event][0]["hooks"][0]["command"] == hook.command, f"the install of hook {event} lost its command in {target}"

    component = Component(event, (Path(SETTINGS_FOLDER) / hook.source).as_posix(), event, CHANNEL_HOOK, text, install)
    assert component.text == text, f"hook_component changed the text of {event}"
    return component


def arm_entry(label, role, channel, overlay_label=None):
    assert label and role and channel, f"arm_entry needs a label, a role and a channel, got {label!r}, {role!r}, {channel!r}."
    entry = {"label": label, "role": role, "overlay": f"{ARMS_FOLDER}/{overlay_label or label}", "channel": channel}
    assert entry["overlay"].startswith(f"{ARMS_FOLDER}/"), f"arm_entry built {entry!r}. Rule: overlays sit under {ARMS_FOLDER}."
    return entry


def arm_entries(component, placebo):
    assert component.text, f"component {component.name} has no text. Rule: arm P needs text."
    entries = [
        arm_entry(ARM_NOTHING, ROLE_LEAVE_ONE_OUT, CHANNEL_FILE),
        arm_entry(ARM_NOISE, f"{NOISE_ROLE_PREFIX}{ARM_NOTHING}", CHANNEL_FILE, ARM_NOTHING),
        arm_entry(ARM_PROMPT, ROLE_RULE, CHANNEL_SYSTEM_PROMPT),
        arm_entry(ARM_COMPONENT, ROLE_RULE, component.channel),
    ]
    if placebo:
        entries.append(arm_entry(ARM_PLACEBO, ROLE_RULE, CHANNEL_SYSTEM_PROMPT))
    assert len({entry["label"] for entry in entries}) == len(entries), f"arm_entries repeated a label in {entries!r}"
    return entries


def component_plan_data(component, options):
    assert isinstance(options, BuildOptions), f"component_plan_data needs BuildOptions, got {options!r}. Fix: build them in the command."
    assert options.tasks, "component_plan_data needs tasks. Rule: the plan holds the tasks and their completed check."
    rule = {"id": component.name, "file": component.file, "section": component.section, "target_outcome": TARGET_OUTCOME, DETECTOR_KEY: options.detector}
    data = {
        "schema": SCHEMA_VERSION,
        "name": options.plan_name or f"component-{component.name}",
        BUDGET_KEY: options.budget_usd,
        "run_cap_usd": options.run_cap_usd,
        "world": WORLD_FOLDER,
        "rule": rule,
        "arms": arm_entries(component, options.placebo),
        TASKS_KEY: options.tasks,
    }
    assert tuple(rule) == RULE_KEYS_ORDER, f"component_plan_data built the rule {rule!r}. Rule: the rule holds the detector from the first run."
    return data


def write_arm_overlays(component, options, entries):
    assert component.text, f"component {component.name} has no text. Rule: arm P needs text."
    texts = {ARM_PROMPT: component.text, ARM_PLACEBO: filler_text(len(component.text))}
    for label in sorted({Path(entry["overlay"]).name for entry in entries}):
        overlay = options.out / ARMS_FOLDER / label
        overlay.mkdir(parents=True)
        if label == ARM_COMPONENT:
            component.install(overlay)
        if label in texts:
            (overlay / SYSTEM_PROMPT_NAME).write_text(texts[label])
    assert all((options.out / entry["overlay"]).is_dir() for entry in entries), f"an overlay of {entries!r} is missing under {options.out}"


def build_component_plan(component, options):
    assert isinstance(component, Component), f"build_component_plan needs a Component, got {component!r}. Fix: build one with skill_component or hook_component."
    assert isinstance(options, BuildOptions), f"build_component_plan needs BuildOptions, got {options!r}. Fix: build them in the command."
    plan_path = options.out / PLAN_FILE
    if plan_path.exists():
        raise BuildRefused(EXISTING_PLAN.format(path=plan_path))
    if not component.text.strip():
        raise BuildRefused(EMPTY_TEXT.format(owner=component.name, name=SYSTEM_PROMPT_NAME))
    data = component_plan_data(component, options)
    try:
        load_plan(data)
    except PlanError as error:
        raise BuildRefused(str(error)) from error
    write_arm_overlays(component, options, data["arms"])
    plan_path.write_text(json.dumps(data, indent=JSON_INDENT) + "\n")
    assert plan_path.is_file(), f"build_component_plan did not write {plan_path}"
    return plan_path
