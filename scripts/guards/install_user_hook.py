import argparse
import copy
import json
import os
import shlex
import shutil
import sys
import tempfile
from pathlib import Path

from willitharness.paths import inside

SCRIPT_NAME = "remote_write_guard.py"
INTERPRETER = "python3"
MATCHER = "Bash|Write|Edit|MultiEdit|NotebookEdit"
HOOK_EVENT = "PreToolUse"
HOOKS_KEY = "hooks"
HANDLER_TYPE = "command"
BACKUP_SUFFIX = ".before-willitharness-guard"
TEMP_PREFIX = ".settings-"
WORKTREE_MARKER = ".git"
INSTALL = "install"
REMOVE = "remove"
CHECK = "check"
ACTIONS = (INSTALL, REMOVE, CHECK)
EXIT_OK = 0
EXIT_CHECK_FAILED = 1
EXIT_REFUSED = 2
INDENTS = (2, 4, "\t")
ASCII_MODES = (False, True)
TRAILERS = ("", "\n")
STYLE_PARTS = 3
USAGE_EPILOG = (
    "Point --script at remote_write_guard.py in the MAIN checkout, never at a linked worktree:\n"
    "the path must stay valid after the worktree is deleted.\n"
    "Example script: /Users/NAME/Develop/willitharness/scripts/guards/remote_write_guard.py\n"
    "Typical targets: /Users/NAME/.claude/settings.json /Users/NAME/.claude-thoughtworks/settings.json\n"
    "Every target is validated before any is written.\n"
    "Run from the repository: uv run python scripts/guards/install_user_hook.py ACTION --script PATH TARGET..."
)


class SettingsRefused(Exception):
    pass


def guard_command(script):
    assert isinstance(script, Path), f"guard_command needs a Path, got {script!r}. Rule: the command embeds one absolute path. Fix: pass the validated script."
    assert script.is_absolute(), f"{script} is not absolute. Rule: the hook runs from any directory. Fix: call validated_script first."
    return f"{INTERPRETER} {script}"


def canonical_group(command):
    assert isinstance(command, str) and command.startswith(INTERPRETER + " "), f"command {command!r} must start with {INTERPRETER!r}. Rule: the guard runs under {INTERPRETER}. Fix: build it with guard_command."
    assert SCRIPT_NAME in command, f"command {command!r} does not name {SCRIPT_NAME}. Rule: the entry is found by script name. Fix: build it with guard_command."
    return {"matcher": MATCHER, "hooks": [{"type": HANDLER_TYPE, "command": command}]}


def in_linked_worktree(script):
    assert isinstance(script, Path), f"in_linked_worktree needs a Path, got {script!r}. Fix: pass the script path."
    assert script.is_absolute(), f"{script} is not absolute. Rule: parents are walked from the filesystem root. Fix: pass an absolute path."
    return any((parent / WORKTREE_MARKER).is_file() for parent in script.parents)


def validated_script(text):
    assert isinstance(text, str), f"validated_script needs text, got {type(text).__name__}. Fix: pass the --script value."
    assert text, "the script path is empty. Rule: the guard path is explicit. Fix: pass --script."
    script = Path(text)
    if not script.is_absolute():
        raise SettingsRefused(f"{text} is not an absolute path. Rule: the hook runs from any directory. Fix: pass the absolute path in the main checkout.")
    if not script.is_file():
        raise SettingsRefused(f"{text} is not an existing file. Rule: a hook that points nowhere guards nothing. Fix: pass the real script path.")
    if script.name != SCRIPT_NAME:
        raise SettingsRefused(f"{script.name} is not {SCRIPT_NAME}. Rule: the entry is found by script name. Fix: pass the guard script.")
    if shlex.quote(text) != text:
        raise SettingsRefused(f"{text} needs shell quoting. Rule: the command string is not quoted. Fix: install the checkout under a path without spaces or symbols.")
    if in_linked_worktree(script):
        raise SettingsRefused(f"{text} lies in a linked worktree. Rule: the path must outlive the worktree. Fix: pass the script of the main checkout.")
    assert script.is_absolute() and script.is_file(), f"{script} passed validation but is not an absolute file"
    return script


def render(document, style):
    assert isinstance(document, dict), f"render needs an object, got {type(document).__name__}. Fix: pass the settings document."
    assert len(style) == STYLE_PARTS, f"style must be (indent, ascii, trailer), got {style!r}. Fix: use detect_style output."
    indent, ascii_mode, trailer = style
    return json.dumps(document, indent=indent, ensure_ascii=ascii_mode) + trailer


def detect_style(text, document):
    assert isinstance(text, str), f"detect_style needs text, got {type(text).__name__}. Fix: pass the file text."
    assert isinstance(document, dict), f"detect_style needs the parsed object, got {type(document).__name__}. Fix: parse first."
    for indent in INDENTS:
        for ascii_mode in ASCII_MODES:
            for trailer in TRAILERS:
                if render(document, (indent, ascii_mode, trailer)) == text:
                    return (indent, ascii_mode, trailer)
    raise SettingsRefused("the file formatting is not plain JSON with 2-space, 4-space or tab indent. Rule: only the guard entry may change, so the rest must reserialize byte for byte. Fix: reformat the file or edit it by hand.")


def load_settings(path):
    assert isinstance(path, Path), f"load_settings needs a Path, got {path!r}. Fix: pass the settings path."
    assert path.is_absolute(), f"{path} is not absolute. Rule: targets are explicit. Fix: pass absolute settings paths."
    if not path.is_file():
        raise SettingsRefused(f"{path} does not exist. Rule: the installer edits an existing settings file. Fix: create it or pass the right path.")
    text = inside(path.parent, path.name).read_bytes().decode("utf-8")
    try:
        document = json.loads(text)
    except json.JSONDecodeError as problem:
        raise SettingsRefused(f"{path} is not valid JSON ({problem}). Rule: a broken file is never rewritten. Fix: repair it first.") from problem
    if not isinstance(document, dict):
        raise SettingsRefused(f"{path} holds {type(document).__name__}, not an object. Rule: settings are one JSON object. Fix: repair it first.")
    return text, document, detect_style(text, document)


def handler_commands(group):
    assert isinstance(group, dict), f"a hook group must be an object, got {group!r}. Rule: groups are objects. Fix: repair the file."
    handlers = group.get("hooks", [])
    assert isinstance(handlers, list), f"group hooks must be a list, got {handlers!r}. Rule: hooks are a list. Fix: repair the file."
    return [str(handler.get("command", "")) if isinstance(handler, dict) else "" for handler in handlers]


def event_groups(document):
    assert isinstance(document, dict), f"event_groups needs an object, got {type(document).__name__}. Fix: pass the settings document."
    hooks = document.get(HOOKS_KEY, {})
    if not isinstance(hooks, dict):
        raise SettingsRefused(f"{HOOKS_KEY} is {type(hooks).__name__}, not an object. Rule: only {HOOKS_KEY}.{HOOK_EVENT} is edited. Fix: repair the file.")
    groups = hooks.get(HOOK_EVENT, [])
    if not isinstance(groups, list) or not all(isinstance(group, dict) for group in groups):
        raise SettingsRefused(f"{HOOKS_KEY}.{HOOK_EVENT} is not a list of objects. Rule: only {HOOKS_KEY}.{HOOK_EVENT} is edited. Fix: repair the file.")
    assert all(isinstance(group, dict) for group in groups), f"groups must be objects, got {groups!r}. Rule: the list was validated above. Fix: repair the file."
    return groups


def our_positions(document):
    groups = event_groups(document)
    assert isinstance(groups, list), f"groups must be a list, got {type(groups).__name__}. Fix: use event_groups."
    positions = []
    for position, group in enumerate(groups):
        commands = handler_commands(group)
        named = [SCRIPT_NAME in command for command in commands]
        if any(named) and not all(named):
            raise SettingsRefused(f"group {position} of {HOOK_EVENT} mixes {SCRIPT_NAME} with other handlers. Rule: only our own group is rewritten. Fix: split the group by hand.")
        if any(named):
            positions.append(position)
    assert positions == sorted(set(positions)), f"positions must ascend without repeats, got {positions}"
    return positions


def installed_document(document, command):
    positions = our_positions(document)
    assert isinstance(command, str), f"command must be text, got {command!r}. Fix: pass guard_command output."
    result = copy.deepcopy(document)
    groups = result.setdefault(HOOKS_KEY, {}).setdefault(HOOK_EVENT, [])
    canonical = canonical_group(command)
    if not positions:
        groups.append(canonical)
    else:
        groups[positions[0]] = canonical
        for position in reversed(positions[1:]):
            del groups[position]
    assert our_positions(result) == [positions[0] if positions else len(groups) - 1], f"exactly one entry must remain, got {our_positions(result)}"
    return result


def removed_document(document):
    positions = our_positions(document)
    assert isinstance(document, dict), f"removed_document needs an object, got {type(document).__name__}. Fix: pass the settings document."
    result = copy.deepcopy(document)
    if HOOKS_KEY not in result:
        return result
    hooks = result[HOOKS_KEY]
    groups = hooks.get(HOOK_EVENT, [])
    for position in reversed(positions):
        del groups[position]
    if positions and not groups:
        del hooks[HOOK_EVENT]
    if positions and not hooks:
        del result[HOOKS_KEY]
    assert our_positions(result) == [], f"no entry may remain, got {our_positions(result)}"
    return result


def temp_directory(path):
    assert isinstance(path, Path), f"temp_directory needs a Path, got {path!r}. Fix: pass the target path."
    assert path.is_absolute(), f"{path} is not absolute. Fix: pass an absolute path."
    return path.parent


def atomic_write(path, text):
    assert isinstance(text, str), f"atomic_write needs text, got {type(text).__name__}. Fix: pass the new file text."
    assert path.is_file(), f"{path} does not exist. Rule: an atomic write replaces an existing file. Fix: create it first."
    target = inside(path.parent, path.name)
    descriptor, name = tempfile.mkstemp(dir=temp_directory(target), prefix=TEMP_PREFIX)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
        shutil.copymode(target, name)
        os.replace(name, target)
    finally:
        Path(name).unlink(missing_ok=True)
    assert target.read_bytes().decode("utf-8") == text, f"{target} does not hold the text just written"


def backup_path(path):
    assert isinstance(path, Path), f"backup_path needs a Path, got {path!r}. Fix: pass the target path."
    assert path.name, f"{path} has no file name. Fix: pass a file path."
    return path.with_name(path.name + BACKUP_SUFFIX)


def plan_target(path, action, command):
    assert action in (INSTALL, REMOVE), f"plan_target handles {INSTALL} and {REMOVE}, got {action!r}. Fix: pick one."
    text, document, style = load_settings(path)
    changed = installed_document(document, command) if action == INSTALL else removed_document(document)
    planned = render(changed, style)
    assert changed != document or planned == text, f"text changed but the document did not for {path}"
    return path, text, planned


def commit(plans, action):
    assert plans, "commit got no plans. Rule: at least one target. Fix: pass a target."
    assert action in (INSTALL, REMOVE), f"commit handles {INSTALL} and {REMOVE}, got {action!r}. Fix: pick one."
    written = []
    backups = []
    try:
        for path, original, planned in plans:
            if planned == original:
                continue
            backup = backup_path(path)
            if action == INSTALL and not backup.exists():
                backup.write_bytes(original.encode("utf-8"))
                backups.append(backup)
            atomic_write(path, planned)
            written.append((path, original))
    except OSError as problem:
        for path, original in written:
            atomic_write(path, original)
        for backup in backups:
            backup.unlink(missing_ok=True)
        raise SettingsRefused(f"writing failed ({problem}); every earlier target was restored. Rule: all targets change or none. Fix: make the folder writable.") from problem
    assert len(written) <= len(plans), f"wrote {len(written)} of {len(plans)} plans"
    return [path for path, _ in written]


def check_problems(path, script):
    assert isinstance(script, Path) and script.is_absolute(), f"check needs the absolute script path, got {script!r}. Fix: call validated_script."
    assert isinstance(path, Path), f"check needs a Path, got {path!r}. Fix: pass the settings path."
    try:
        _, document, _ = load_settings(path)
        positions = our_positions(document)
        problems = []
        if len(positions) != 1:
            problems.append(f"{path} holds {len(positions)} guard entries. Rule: exactly one. Fix: run install.")
        elif event_groups(document)[positions[0]] != canonical_group(guard_command(script)):
            problems.append(f"{path} has a guard entry that differs from the expected command. Rule: the command is exact. Fix: run install.")
        if not os.access(script, os.X_OK):
            problems.append(f"{script} is not executable. Rule: the hook must run. Fix: chmod +x it.")
        backup = backup_path(path)
        if backup.is_file():
            _, original, _ = load_settings(backup)
            if json.dumps(removed_document(document).get(HOOKS_KEY)) != json.dumps(removed_document(original).get(HOOKS_KEY)):
                problems.append(f"{path} has hook groups that differ from {backup.name}. Rule: only the guard entry may differ. Fix: restore the other groups.")
    except SettingsRefused as refusal:
        problems = [str(refusal)]
    assert all(isinstance(problem, str) for problem in problems), f"problems must be text, got {problems!r}"
    return problems


def apply_action(action, script, targets):
    assert action in ACTIONS, f"unknown action {action!r}. Fix: use one of {ACTIONS}."
    assert targets, "run got no targets. Rule: at least one settings file. Fix: pass a path."
    command = guard_command(script)
    if action == CHECK:
        return [problem for path in targets for problem in check_problems(path, script)]
    plans = [plan_target(path, action, command) for path in targets]
    commit(plans, action)
    return []


def build_parser():
    parser = argparse.ArgumentParser(prog="install_user_hook", epilog=USAGE_EPILOG, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("action", choices=ACTIONS)
    parser.add_argument("--script", required=True)
    parser.add_argument("targets", nargs="+", type=Path)
    assert parser.epilog == USAGE_EPILOG, "the usage text must carry the epilog"
    assert parser.prog == "install_user_hook", f"unexpected prog {parser.prog!r}"
    return parser


def main(argv):
    assert isinstance(argv, list), f"main needs a list of arguments, got {argv!r}. Fix: pass sys.argv[1:]."
    assert all(isinstance(item, str) for item in argv), f"every argument must be text, got {argv!r}"
    arguments = build_parser().parse_args(argv)
    try:
        problems = apply_action(arguments.action, validated_script(arguments.script), [target.resolve() for target in arguments.targets])
    except SettingsRefused as refusal:
        print(f"install-user-hook: refused: {refusal}")
        return EXIT_REFUSED
    for problem in problems:
        print(f"install-user-hook: {problem}")
    if problems:
        return EXIT_CHECK_FAILED
    print(f"install-user-hook: {arguments.action} ok for {len(arguments.targets)} target(s)")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
