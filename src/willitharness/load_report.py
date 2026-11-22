import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from willitharness.paths import PathOutsideRoot, inside

AGENTS_FILE = "AGENTS.md"
MASKING_FILES = ("CLAUDE.md", ".claude/CLAUDE.md", "CLAUDE.local.md")
USER_LEVEL_FILE = ".claude/CLAUDE.md"
RULES_FOLDER = Path(".claude") / "rules"
RULE_PATHS_KEY = "paths"
FENCES = ("```", "~~~")
CODE_SPAN = re.compile(r"`[^`\n]*`")
IMPORT_PATTERN = re.compile(r"(?<![\w@])@([\w./-]+)")
MAX_IMPORT_HOPS = 4
SKILLS_FOLDER = Path(".claude") / "skills"
SKILL_FILE = "SKILL.md"
FRONTMATTER_OPEN = "---\n"
FRONTMATTER_CLOSE = "\n---"
SETTINGS_FILES = ("settings.json", "settings.local.json")
SETTINGS_FOLDER = Path(".claude")
NO_MATCHER = "(any)"
NOT_MEASURED = "not measured"
SKIPPED_OUTSIDE = "skipped: outside the project (Claude Code asks for approval first)"
NOT_COUNTED = (
    "not counted: user-level files (~/.claude), managed policy files, subdirectory CLAUDE.md files that load on demand, "
    "auto memory, plugin skills and user-level skills"
)
NOTHING_LOADED = "no instruction files, skills or hooks found"
CONTEXT_EVENTS = ("SessionStart", "UserPromptSubmit")
HOOK_TIMEOUT_SECONDS = 10
HOOK_COMMAND_TYPE = "command"
SUCCESS_CODE = 0
SAMPLE_PROMPT = "sample prompt"
SAMPLE_SESSION = "sample-session"
SAMPLE_SOURCE = "startup"
OUTPUT_KEY = "hookSpecificOutput"
CONTEXT_KEY = "additionalContext"

UNREADABLE = "{path} cannot be read ({reason}). Rule: the report counts every file the agent loads. Fix: make the file readable text inside the project, or remove it."
MISSING_FOLDER = "{path} is not a directory. Rule: the report reads one project folder. Fix: pass the project folder, or run from inside it."
BAD_SETTINGS = "{path} does not hold the hooks layout ({reason}). Rule: hooks sit in an object of events, each a list of {{matcher, hooks}}. Fix: correct the file."


class LoadRefused(Exception):
    pass


@dataclass(frozen=True)
class Section:
    lines: list
    counted: int


@dataclass(frozen=True)
class InstructionScan:
    texts: dict
    skipped: set
    masked: list


@dataclass(frozen=True)
class Skill:
    name: str
    header_characters: int
    body_characters: int


@dataclass(frozen=True)
class Hook:
    source: str
    event: str
    matcher: str
    command: str


def read_file(root, relative):
    assert isinstance(root, Path) and root.is_dir(), f"read_file needs the project folder as a Path, got {root!r}. Fix: pass the folder."
    assert not Path(relative).is_absolute(), f"read_file needs a path relative to the project, got {relative!r}. Rule: loaded files sit under the project."
    try:
        text = inside(root, relative).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError, PathOutsideRoot) as error:
        raise LoadRefused(UNREADABLE.format(path=root / relative, reason=type(error).__name__)) from error
    assert isinstance(text, str), f"read_file returned {text!r} for {relative}. Rule: it returns text."
    return text


def project_folder(cwd, argument):
    assert isinstance(cwd, Path), f"project_folder needs a Path, got {cwd!r}. Fix: pass pathlib.Path."
    folder = (cwd / argument).resolve()
    if not folder.is_dir():
        raise LoadRefused(MISSING_FOLDER.format(path=folder))
    assert folder.is_absolute(), f"{folder} is not absolute after resolve"
    return folder


def importable_text(text):
    assert isinstance(text, str), f"importable_text needs text, got {text!r}."
    kept = []
    fenced = False
    for line in text.splitlines():
        if line.lstrip().startswith(FENCES):
            fenced = not fenced
        elif not fenced:
            kept.append(CODE_SPAN.sub("", line))
    result = "\n".join(kept)
    assert isinstance(result, str), f"importable_text returned {result!r}. Rule: it returns text."
    return result


def imported_files(root, relative, text):
    assert isinstance(root, Path) and root.is_dir(), f"imported_files needs the project folder, got {root!r}."
    assert isinstance(text, str), f"imported_files needs the text of {relative}, got {text!r}."
    found = []
    outside = []
    for name in IMPORT_PATTERN.findall(importable_text(text)):
        if not (root / relative.parent / name).resolve().is_file():
            continue
        try:
            found.append(inside(root, relative.parent / name).relative_to(root))
        except PathOutsideRoot:
            outside.append(name)
    assert all((root / item).is_file() for item in found), f"an import of {relative} is not a file: {found!r}"
    return found, outside


def collect_instructions(root, starts, scan):
    assert root.is_dir(), f"{root} is not a directory. Fix: pass the project folder."
    assert isinstance(scan, InstructionScan), f"collect_instructions needs an InstructionScan, got {scan!r}."
    queue = [(start, 0) for start in starts]
    while queue:
        relative, depth = queue.pop(0)
        if relative in scan.texts or depth > MAX_IMPORT_HOPS:
            continue
        scan.texts[relative] = read_file(root, relative)
        found, outside = imported_files(root, relative, scan.texts[relative])
        scan.skipped.update((name, relative) for name in outside)
        queue.extend((item, depth + 1) for item in found)
    assert all(isinstance(text, str) for text in scan.texts.values()), f"an instruction file has no text: {scan.texts!r}"
    return scan


def masking_file(root):
    assert root.is_dir(), f"{root} is not a directory. Fix: pass the project folder."
    found = None
    for folder in (root, *root.parents):
        for name in MASKING_FILES:
            candidate = folder / name
            if found is None and candidate.is_file() and not (folder == Path.home() and name == USER_LEVEL_FILE):
                found = candidate
    assert found is None or found.is_file(), f"masking_file returned {found!r}. Rule: it returns an existing file or None."
    return found


def shown_path(root, path):
    assert isinstance(path, Path), f"shown_path needs a Path, got {path!r}."
    shown = path.relative_to(root) if path.is_relative_to(root) else path
    assert shown.as_posix(), f"{path} has no name to show"
    return shown.as_posix()


def instruction_scan(root):
    assert root.is_dir(), f"{root} is not a directory. Fix: pass the project folder."
    scan = collect_instructions(root, [Path(name) for name in MASKING_FILES if (root / name).is_file()], InstructionScan({}, set(), []))
    agents = Path(AGENTS_FILE)
    masker = masking_file(root)
    if (root / agents).is_file() and agents not in scan.texts and masker is not None:
        scan.masked.append(f"instruction {AGENTS_FILE}: not loaded: masked by {shown_path(root, masker)}")
    elif (root / agents).is_file():
        collect_instructions(root, [agents], scan)
    assert all(isinstance(path, Path) for path in scan.texts), f"scan holds a non-path key: {scan.texts!r}"
    return scan


def instruction_section(root):
    assert root.is_dir(), f"{root} is not a directory. Fix: pass the project folder."
    scan = instruction_scan(root)
    loaded = [f"instruction {relative.as_posix()}: {len(text)} characters" for relative, text in scan.texts.items()]
    skipped = [f"instruction {name} (imported by {importer.as_posix()}): {SKIPPED_OUTSIDE}" for name, importer in scan.skipped]
    lines = sorted([*loaded, *skipped, *scan.masked])
    assert len(lines) == len(scan.texts) + len(scan.skipped) + len(scan.masked), f"{len(lines)} lines do not match the scan {scan!r}"
    return Section(lines, sum(len(text) for text in scan.texts.values()))


def rule_section(root):
    assert root.is_dir(), f"{root} is not a directory. Fix: pass the project folder."
    files = sorted((root / RULES_FOLDER).rglob("*.md"))
    lines = []
    counted = 0
    for path in files:
        relative = path.relative_to(root)
        text = read_file(root, relative)
        on_demand = RULE_PATHS_KEY in split_skill(text)[0]
        counted += 0 if on_demand else len(text)
        suffix = "on demand, not in the always-loaded total" if on_demand else "always loaded"
        lines.append(f"rule {relative.as_posix()}: {len(text)} characters ({suffix})")
    assert len(lines) == len(files), f"{len(lines)} lines for {len(files)} rule files. Rule: each rule gets one line."
    return Section(sorted(lines), counted)


def split_skill(text):
    assert isinstance(text, str), f"split_skill needs text, got {text!r}."
    fields = {}
    body = text.strip()
    head, closed, rest = text[len(FRONTMATTER_OPEN):].partition(FRONTMATTER_CLOSE)
    if text.startswith(FRONTMATTER_OPEN) and closed:
        body = rest.partition("\n")[2].strip()
        for line in head.splitlines():
            key, colon, value = line.partition(":")
            if colon and not line.startswith(" "):
                fields[key.strip()] = value.strip()
    assert isinstance(body, str) and isinstance(fields, dict), f"split_skill lost its parts: {fields!r} {body!r}"
    return fields, body


def skill_of(root, relative):
    assert relative.name == SKILL_FILE, f"{relative} is not a {SKILL_FILE}. Fix: pass a skill file."
    fields, body = split_skill(read_file(root, relative))
    name = fields.get("name") or relative.parent.name
    skill = Skill(name, len(name) + len(fields.get("description", "")), len(body))
    assert skill.header_characters >= len(skill.name), f"skill {skill} counts fewer characters than its name"
    return skill


def skill_line(skill):
    assert isinstance(skill, Skill), f"skill_line needs a Skill, got {skill!r}."
    line = (
        f"skill {skill.name}: name and description {skill.header_characters} characters (always loaded), "
        f"body {skill.body_characters} characters (loaded after the Skill tool call)"
    )
    assert str(skill.header_characters) in line and str(skill.body_characters) in line, f"skill line {line!r} lost a count of {skill}"
    return line


def skill_lines(root):
    assert root.is_dir(), f"{root} is not a directory. Fix: pass the project folder."
    files = sorted((root / SKILLS_FOLDER).glob(f"*/{SKILL_FILE}"))
    lines = sorted(skill_line(skill_of(root, path.relative_to(root))) for path in files)
    assert len(lines) == len(files), f"{len(lines)} lines for {len(files)} skill files. Rule: each skill gets one line."
    return lines


def parsed_settings(root, relative):
    assert isinstance(root, Path) and relative.name in SETTINGS_FILES, f"parsed_settings needs a settings file under {root}, got {relative!r}."
    try:
        document = json.loads(read_file(root, relative))
    except json.JSONDecodeError as error:
        raise LoadRefused(UNREADABLE.format(path=root / relative, reason=type(error).__name__)) from error
    if not isinstance(document, dict):
        raise LoadRefused(BAD_SETTINGS.format(path=root / relative, reason="top level is not an object"))
    assert isinstance(document, dict), f"parsed_settings returned {document!r} for {relative}. Rule: it returns an object."
    return document


def hooks_of(root, relative):
    assert isinstance(root, Path) and relative.name in SETTINGS_FILES, f"hooks_of needs a settings file under {root}, got {relative!r}."
    events = parsed_settings(root, relative).get("hooks", {})
    found = []
    try:
        for event, groups in events.items():
            for group in groups:
                found.extend(Hook(relative.name, event, group.get("matcher", NO_MATCHER), hook["command"]) for hook in group["hooks"] if hook.get("type") == HOOK_COMMAND_TYPE)
    except (AttributeError, KeyError, TypeError) as error:
        raise LoadRefused(BAD_SETTINGS.format(path=root / relative, reason=type(error).__name__)) from error
    assert all(isinstance(item.command, str) for item in found), f"a hook command is not text in {relative}"
    return found


def configured_hooks(root):
    assert root.is_dir(), f"{root} is not a directory. Fix: pass the project folder."
    paths = [SETTINGS_FOLDER / name for name in SETTINGS_FILES if (root / SETTINGS_FOLDER / name).is_file()]
    found = sorted((hook for path in paths for hook in hooks_of(root, path)), key=lambda hook: (hook.event, hook.matcher, hook.source, hook.command))
    assert all(isinstance(hook, Hook) for hook in found), f"configured_hooks found a non-hook: {found!r}"
    return found


def sample_event(root, event):
    assert isinstance(root, Path) and event, f"sample_event needs the project folder and an event name, got {root!r} and {event!r}."
    text = json.dumps({"hook_event_name": event, "session_id": SAMPLE_SESSION, "cwd": str(root), "source": SAMPLE_SOURCE, "prompt": SAMPLE_PROMPT}, sort_keys=True)
    assert event in text, f"the sample event lost its event name {event!r}: {text!r}"
    return text


def context_text(output):
    assert isinstance(output, str), f"context_text needs the output text of a hook, got {output!r}."
    try:
        document = json.loads(output)
    except json.JSONDecodeError:
        return output
    nested = document.get(OUTPUT_KEY) if isinstance(document, dict) else None
    text = str(nested.get(CONTEXT_KEY, "")) if isinstance(nested, dict) else ""
    assert isinstance(text, str), f"context_text returned {text!r} for {output!r}. Rule: it returns text."
    return text


def measured_context(root, hook, timeout_seconds):
    assert isinstance(hook, Hook) and timeout_seconds > 0, f"measured_context needs a Hook and a positive timeout, got {hook!r} and {timeout_seconds!r}."
    if hook.event not in CONTEXT_EVENTS:
        return NOT_MEASURED
    try:
        finished = subprocess.run(hook.command, shell=True, input=sample_event(root, hook.event), capture_output=True, text=True, timeout=timeout_seconds, cwd=root, check=False)
    except (OSError, subprocess.TimeoutExpired, UnicodeDecodeError):
        return NOT_MEASURED
    if finished.returncode != SUCCESS_CODE:
        return NOT_MEASURED
    size = f"{len(context_text(finished.stdout))} characters"
    assert size.endswith("characters"), f"measured_context returned {size!r}. Rule: a size ends with characters."
    return size


def hook_line(root, hook, timeout_seconds):
    assert timeout_seconds is None or timeout_seconds > 0, f"timeout_seconds is {timeout_seconds!r}. Rule: None means do not run the hook; a number is the timeout in seconds."
    context = NOT_MEASURED if timeout_seconds is None else measured_context(root, hook, timeout_seconds)
    line = f"hook {hook.event} matcher {hook.matcher} ({hook.source}): context {context}; command {hook.command}"
    assert NOT_MEASURED in line or "characters" in line, f"a hook line states a size or {NOT_MEASURED}: {line!r}"
    return line


def build_load_report(root, timeout_seconds=None):
    assert isinstance(root, Path), f"build_load_report needs a Path, got {root!r}. Fix: pass the project folder."
    assert timeout_seconds is None or timeout_seconds > 0, f"timeout_seconds is {timeout_seconds!r}. Rule: None means do not run hooks; a number runs them with that timeout."
    instructions, rules = instruction_section(root), rule_section(root)
    total = [f"always loaded instruction and rule text: {instructions.counted + rules.counted} characters"] if instructions.lines or rules.lines else []
    hooks = [hook_line(root, hook, timeout_seconds) for hook in configured_hooks(root)]
    lines = [*instructions.lines, *rules.lines, *total, *skill_lines(root), *hooks]
    assert all(lines), f"a report line is empty in {lines!r}. Rule: every line states a file, skill or hook."
    return [*(lines or [NOTHING_LOADED]), NOT_COUNTED]
