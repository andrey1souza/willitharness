import json
import re
from pathlib import Path

from willitharness.load_report import SETTINGS_FOLDER, LoadRefused, configured_hooks, read_file
from willitharness.paths import PathOutsideRoot, inside

GUARD_EVENT = "PreToolUse"
HOOK_FILE_NAME = "hooks.json"
SKIPPED_FOLDERS = frozenset({".git", "node_modules", ".venv"})
SCRIPT_TOKEN = re.compile(r"[^\s\"']+\.(?:sh|bash|py|js|mjs|cjs|ts|rb)\b")
VARIABLE_PREFIX = re.compile(r"^\$\{?\w+\}?/")
RELATIVE_IMPORT = re.compile(r"""(?:from|import|require\()\s*['"](\.{1,2}/[^'"]+)['"]""")
HOOKS_KEY = "hooks"
COMMAND_KEY = "command"


def hook_files(root):
    assert isinstance(root, Path) and root.is_dir(), f"hook_files needs the project folder, got {root!r}. Fix: pass the folder."
    found = sorted(path for path in root.rglob(HOOK_FILE_NAME) if not SKIPPED_FOLDERS.intersection(path.relative_to(root).parts))
    assert all(path.is_file() for path in found), f"hook_files returned a non-file: {found!r}"
    return found


def commands_of_file(root, path):
    assert isinstance(root, Path) and root.is_dir(), f"commands_of_file needs the project folder, got {root!r}. Fix: pass the folder."
    assert isinstance(path, Path), f"commands_of_file needs a Path, got {path!r}. Fix: pass the hooks file."
    try:
        events = json.loads(read_file(root, path.relative_to(root))).get(HOOKS_KEY, {})
        groups = events.get(GUARD_EVENT, [])
        commands = [hook[COMMAND_KEY] for group in groups for hook in group[HOOKS_KEY] if COMMAND_KEY in hook]
    except (LoadRefused, json.JSONDecodeError, AttributeError, KeyError, TypeError):
        commands = []
    assert all(isinstance(command, str) for command in commands), f"commands_of_file found a non-text command in {path}: {commands!r}"
    return commands


def settings_commands(root):
    assert root.is_dir(), f"{root} is not a directory. Fix: pass the project folder."
    found = [hook.command for hook in configured_hooks(root) if hook.event == GUARD_EVENT]
    assert all(isinstance(command, str) for command in found), f"settings_commands found a non-text command: {found!r}"
    return found


def script_candidates(command):
    assert isinstance(command, str), f"script_candidates needs the command text, got {command!r}. Fix: pass the hook command."
    names = [VARIABLE_PREFIX.sub("", token) for token in SCRIPT_TOKEN.findall(command)]
    assert all(name for name in names), f"script_candidates found an empty name in {command!r}"
    return names


def readable_file(root, path):
    assert isinstance(root, Path) and root.is_dir(), f"readable_file needs the project folder, got {root!r}. Fix: pass the folder."
    try:
        resolved = inside(root, path)
        text = resolved.read_text(encoding="utf-8") if resolved.is_file() else None
    except (PathOutsideRoot, OSError, UnicodeDecodeError):
        return None
    assert text is None or isinstance(text, str), f"readable_file returned {text!r}. Rule: text or None."
    return None if text is None else (resolved, text)


def script_code(root, base_folders, name):
    assert isinstance(root, Path) and root.is_dir(), f"script_code needs the project folder, got {root!r}. Fix: pass the folder."
    for folder in base_folders:
        first = readable_file(root, folder / name)
        if first is None:
            continue
        resolved, text = first
        texts = [text]
        for specifier in RELATIVE_IMPORT.findall(text):
            imported = readable_file(root, resolved.parent / specifier)
            texts += [imported[1]] if imported else []
        assert texts and texts[0] == text, f"script_code lost the script text of {name}: {texts!r}"
        return texts
    return []


def guard_texts(root):
    assert isinstance(root, Path) and root.is_dir(), f"guard_texts needs the project folder, got {root!r}. Fix: pass the folder."
    sources = [(root / SETTINGS_FOLDER, command) for command in settings_commands(root)]
    sources += [(path.parent, command) for path in hook_files(root) for command in commands_of_file(root, path)]
    texts = []
    for folder, command in sources:
        texts.append(command)
        bases = [root, folder, folder.parent]
        for name in script_candidates(command):
            texts += script_code(root, bases, name)
    assert all(isinstance(text, str) for text in texts), f"guard_texts found non-text: {texts!r}"
    return texts
