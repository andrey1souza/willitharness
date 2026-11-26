import json
import re
from pathlib import Path

import docs_freshness
from willitharness.load_report import split_skill

MANIFEST_FILE = Path("plugin") / ".claude-plugin" / "plugin.json"
SKILL_FILE = Path("plugin") / "skills" / "audit-rules" / "SKILL.md"
MANIFEST_FIELDS = ("name", "version", "description")
SKILL_FIELDS = ("name", "description")
COMMAND_NAME = "audit"
COMMAND_TEXT = "willitharness audit"
REQUIRED_PHRASES = ("Never edit", "Paid tests")
MAX_SENTENCE_WORDS = 20
SENTENCE_BREAK = re.compile(r"(?<=[.!?])\s+|\n+")
WORD = re.compile(r"\S+")


def manifest_errors(root):
    assert root.is_dir(), f"{root} is not a directory. Fix: pass the repository root."
    path = root / MANIFEST_FILE
    if not path.is_file():
        return [f"{MANIFEST_FILE} is missing. Rule: the plugin has a manifest. Fix: restore the file."]
    try:
        manifest = json.loads(path.read_text())
    except json.JSONDecodeError:
        return [f"{MANIFEST_FILE} is not valid JSON. Rule: Claude Code reads the manifest as JSON. Fix: correct the file."]
    missing = [field for field in MANIFEST_FIELDS if not isinstance(manifest, dict) or not str(manifest.get(field, "")).strip()]
    errors = [f"{MANIFEST_FILE} lacks {field}. Rule: the manifest names the plugin. Fix: add the field." for field in missing]
    assert len(errors) == len(missing), f"manifest_errors lost an error: {errors!r} for {missing!r}"
    return errors


def sentence_errors(body):
    assert isinstance(body, str), f"sentence_errors needs text, got {body!r}."
    errors = [
        f"{SKILL_FILE} has a sentence of {len(WORD.findall(sentence))} words: {sentence!r}. Rule: a sentence has {MAX_SENTENCE_WORDS} words or fewer. Fix: split it."
        for sentence in SENTENCE_BREAK.split(body)
        if len(WORD.findall(sentence)) > MAX_SENTENCE_WORDS
    ]
    assert all(isinstance(error, str) for error in errors), f"sentence_errors must return text, got {errors!r}"
    return errors


def skill_command_errors(root, body):
    assert root.is_dir(), f"{root} is not a directory. Fix: pass the repository root."
    assert isinstance(body, str), f"skill_command_errors needs the skill text, got {body!r}. Fix: pass the body."
    commands = docs_freshness.usage_commands(docs_freshness.usage_text((root / docs_freshness.CLI_FILE).read_text()))
    errors = [] if COMMAND_NAME in commands else [f"the CLI has no {COMMAND_NAME} command, but {SKILL_FILE} names it. Rule: a skill names a real command. Fix: add the command or correct the skill."]
    if COMMAND_TEXT not in body:
        errors.append(f"{SKILL_FILE} never names `{COMMAND_TEXT}`. Rule: the skill runs the real command. Fix: add the line.")
    assert all(isinstance(error, str) for error in errors), f"skill_command_errors must return text, got {errors!r}"
    return errors


def skill_errors(root):
    assert root.is_dir(), f"{root} is not a directory. Fix: pass the repository root."
    path = root / SKILL_FILE
    if not path.is_file():
        return [f"{SKILL_FILE} is missing. Rule: the plugin has the audit skill. Fix: restore the file."]
    fields, body = split_skill(path.read_text())
    if not fields:
        return [f"{SKILL_FILE} has no frontmatter. Rule: a skill opens with a name and a description. Fix: add the block."]
    errors = [f"{SKILL_FILE} lacks {field} in its frontmatter. Rule: a skill has both fields. Fix: add it." for field in SKILL_FIELDS if not fields.get(field)]
    if fields.get("name") and fields["name"] != SKILL_FILE.parent.name:
        errors.append(f"the skill name {fields['name']!r} differs from its folder {SKILL_FILE.parent.name!r}. Rule: the folder carries the name. Fix: make them equal.")
    errors += [f"{SKILL_FILE} lacks the phrase {phrase!r}. Rule: the skill states the read-only rule and the paid step. Fix: restore the sentence." for phrase in REQUIRED_PHRASES if phrase not in body]
    result = [*errors, *skill_command_errors(root, body), *sentence_errors(body)]
    assert len(result) >= len(errors), f"skill_errors lost an error: {result!r}"
    return result


def plugin_errors(root):
    assert root.is_dir(), f"{root} is not a directory. Fix: pass the repository root."
    result = [*manifest_errors(root), *skill_errors(root)]
    assert all(isinstance(error, str) for error in result), f"plugin_errors must return text, got {result!r}"
    return result


CHECKS = {"plugin-files": plugin_errors}
