import difflib
import json
import re
from dataclasses import dataclass
from pathlib import Path

from willitharness.flags import parse_action
from willitharness.hook_code import guard_texts
from willitharness.load_report import (
    AGENTS_FILES,
    RULE_PATHS_KEY,
    RULES_FOLDER,
    build_load_report,
    InstructionScan,
    instruction_scan,
    masking_file,
    read_file,
    shown_path,
    split_skill,
)
from willitharness.rule_class import COMMAND, ENFORCED, FORBIDS, NOT_TESTABLE, Classification, Rule, classify_rule, extract_rules, spans_of

PREDICTION_LABEL = "predicted, not verified; a paid probe confirms it"
SHORT_LIMIT = 60
ELLIPSIS = "..."
SECTION_HEADINGS = ("## What loads", "## Rules", "## Predictions", "## Proposed changes", "## Limits")
IMPORT_TARGET = "CLAUDE.md"
NEW_FILE_NAME = "/dev/null"
LOADS = "yes"
ON_DEMAND = "on demand"
MASKED_LOADS = "no (masked)"
NONE_PROPOSED = "None. No change follows from the text of this folder alone."
NOT_APPLIED = "Nothing below is applied. The audit writes nothing to the folder."

NO_ENTRY_REQUIRES = "line {line}: the rule requires `{command}`. A guard blocks a command, and the rule names none to block."
NO_ENTRY_SHAPE = "line {line}: `{command}` is not one program with at most one option, so no entry derivable."

LIMITS = (
    "The free scan predicts. It does not measure.",
    "Loading is modelled on Claude Code. A paid probe confirms it.",
    "Paid tests are not run. They are a separate step.",
    "The class of a rule comes from its text. Only a behaviour test shows what an agent does.",
    "Hooks are not run. Hook code is read as text and never run.",
    "A hook guard is found when its command or the code it names mentions the command. Imports are followed one level.",
    "Skills are counted, not read for rules.",
)


@dataclass(frozen=True)
class Source:
    path: Path
    text: str
    loads: str


@dataclass(frozen=True)
class Audited:
    rule: Rule
    loads: str
    verdict: Classification


def shortened(text):
    assert isinstance(text, str), f"shortened needs text, got {text!r}."
    cut = text if len(text) <= SHORT_LIMIT else text[: SHORT_LIMIT - len(ELLIPSIS)] + ELLIPSIS
    assert len(cut) <= SHORT_LIMIT, f"shortened returned {len(cut)} characters, over {SHORT_LIMIT}"
    return cut.replace("|", "\\|")


def unloaded_agents(root, scan):
    assert root.is_dir(), f"{root} is not a directory. Fix: pass the project folder."
    assert isinstance(scan, InstructionScan), f"unloaded_agents needs an InstructionScan, got {scan!r}. Fix: pass instruction_scan output."
    found = [Path(name) for name in AGENTS_FILES if (root / name).is_file() and Path(name) not in scan.texts]
    assert all(path not in scan.texts for path in found), f"unloaded_agents returned a loaded file: {found!r}"
    return found


def rule_files(root):
    assert root.is_dir(), f"{root} is not a directory. Fix: pass the project folder."
    found = []
    for path in sorted((root / RULES_FOLDER).rglob("*.md")):
        relative = path.relative_to(root)
        text = read_file(root, relative)
        found.append(Source(relative, text, ON_DEMAND if RULE_PATHS_KEY in split_skill(text)[0] else LOADS))
    assert all(source.loads in (LOADS, ON_DEMAND) for source in found), f"rule_files gave a bad load state: {found!r}"
    return found


def sources_of(root, scan):
    assert root.is_dir(), f"{root} is not a directory. Fix: pass the project folder."
    assert isinstance(scan, InstructionScan), f"sources_of needs an InstructionScan, got {scan!r}. Fix: pass instruction_scan output."
    loaded = [Source(path, text, LOADS) for path, text in sorted(scan.texts.items())]
    masked = [Source(path, read_file(root, path), MASKED_LOADS) for path in unloaded_agents(root, scan)]
    sources = [*loaded, *masked, *rule_files(root)]
    assert len(sources) >= len(scan.texts), f"sources_of lost a loaded file: {sources!r} for {sorted(scan.texts)!r}"
    return sources


def audited_rules(root, sources):
    assert root.is_dir(), f"{root} is not a directory. Fix: pass the project folder."
    assert all(isinstance(source, Source) for source in sources), f"audited_rules needs Sources, got {sources!r}. Fix: pass sources_of output."
    found = [
        Audited(rule, source.loads, classify_rule(rule.text, root))
        for source in sources
        for rule in extract_rules(source.path.as_posix(), source.text)
    ]
    assert all(item.verdict.reason for item in found), f"a rule has no reason: {found!r}. Rule: every class has a reason."
    return found


def rule_table(audited):
    assert isinstance(audited, list), f"rule_table needs a list, got {audited!r}."
    header = ["| Source | Rule | Loads (predicted) | Class | Reason |", "|---|---|---|---|---|"]
    rows = [f"| {item.rule.source}:{item.rule.line} | {shortened(item.rule.text)} | {item.loads} | {item.verdict.label} | {item.verdict.reason} |" for item in audited]
    counts = [sum(item.verdict.label == label for item in audited) for label in (ENFORCED, COMMAND, NOT_TESTABLE)]
    summary = f"{len(audited)} rules: {counts[0]} enforced by a script, {counts[1]} command rules, {counts[2]} not testable by behaviour."
    assert sum(counts) == len(audited), f"the classes {counts} do not cover {len(audited)} rules"
    return [*header, *rows, "", summary] if audited else ["No rules found in the loaded files."]


def prediction_lines(root, ceiling, sources):
    assert root.is_dir(), f"{root} is not a directory. Fix: pass the project folder."
    masker = masking_file(root, ceiling)
    lines = [f"Label: {PREDICTION_LABEL}.", "A rule loads when its file loads."]
    for source in sources:
        reason = f"not loaded (masked by {shown_path(root, masker)})" if source.loads == MASKED_LOADS and masker else None
        verdict = reason or ("loads on demand" if source.loads == ON_DEMAND else "loads")
        lines.append(f"- {source.path.as_posix()}: predicted {verdict}")
    assert len(lines) == len(sources) + 2, f"prediction_lines lost a file of {sources!r}"
    return lines


def import_diff(root, targets):
    assert targets, "import_diff needs a file to import. Fix: pass the unloaded files."
    path = root / IMPORT_TARGET
    old = path.read_text(encoding="utf-8") if path.is_file() else ""
    separator = "" if not old or old.endswith("\n") else "\n"
    new = old + separator + "".join(f"@{target.as_posix()}\n" for target in targets)
    source_name = IMPORT_TARGET if old else NEW_FILE_NAME
    diff = "".join(difflib.unified_diff(old.splitlines(keepends=True), new.splitlines(keepends=True), source_name, IMPORT_TARGET))
    assert diff.startswith("--- "), f"import_diff built {diff!r}. Rule: a unified diff starts with the old file name."
    return diff


def guarded(texts, program):
    assert isinstance(texts, list), f"guarded needs the list of guard texts, got {texts!r}. Fix: pass guard_texts output."
    assert isinstance(program, str) and program, f"guarded needs a program name, got {program!r}. Fix: pass the program."
    pattern = re.compile(rf"(?<![\w-]){re.escape(program)}(?![\w-])")
    found = any(pattern.search(text) for text in texts)
    assert found in (True, False), f"guarded computed {found!r} for {program!r}. Rule: a guard exists or it does not."
    return found


def guard_entry(rule, command):
    assert isinstance(rule, Rule) and command, f"guard_entry needs a rule and a command, got {rule!r} and {command!r}."
    try:
        words, patterns = parse_action(command)
    except ValueError:
        return None
    if len(words) != 1 or len(patterns) > 1:
        return None
    program = words[0]
    alternatives = [span for _, span in spans_of(rule.text) if span != command and len(span.split()) > 1]
    blocked = {"program": program, **({"flag_pattern": patterns[0]} if patterns else {})}
    entry = {"name": program, "message": f"Blocked by guard ({program}): {rule.text}", "offered_alternatives": alternatives, "blocked": [blocked]}
    assert entry["blocked"][0]["program"] == program, f"guard_entry lost its program: {entry!r}"
    return entry


def guard_proposals(root, audited):
    assert root.is_dir(), f"{root} is not a directory. Fix: pass the project folder."
    entries, notes = [], []
    texts = guard_texts(root)
    for item in audited:
        verdict = item.verdict
        if verdict.label != COMMAND or item.loads == MASKED_LOADS:
            continue
        location = item.rule.line
        if verdict.direction != FORBIDS:
            notes.append(NO_ENTRY_REQUIRES.format(line=location, command=verdict.command))
            continue
        entry = guard_entry(item.rule, verdict.command)
        if entry is None:
            notes.append(NO_ENTRY_SHAPE.format(line=location, command=verdict.command))
        elif not guarded(texts, entry["name"]):
            entries.append((item.rule, entry))
    assert len(entries) + len(notes) <= len(audited), f"more proposals than rules: {entries!r} {notes!r}"
    return entries, notes


def proposal_lines(root, scan, audited):
    assert root.is_dir(), f"{root} is not a directory. Fix: pass the project folder."
    assert isinstance(scan, InstructionScan) and isinstance(audited, list), f"proposal_lines needs a scan and a list, got {scan!r} and {audited!r}. Fix: pass both."
    lines = [NOT_APPLIED, ""]
    blocks = []
    targets = unloaded_agents(root, scan)
    if targets:
        names = ", ".join(target.as_posix() for target in targets)
        blocks.append([f"### Import {names} in {IMPORT_TARGET}", "", f"Claude Code does not load {names} here. A line `@{targets[0].as_posix()}` in {IMPORT_TARGET} loads it.", "", "```diff", import_diff(root, targets).rstrip("\n"), "```"])
    entries, notes = guard_proposals(root, audited)
    for rule, entry in entries:
        blocks.append([f"### Guard entry for {rule.source}:{rule.line}", "", "Text block in the format of `fixtures/guard/rules.json`. No guard that names this command was found.", "", "```json", json.dumps(entry, indent=2), "```"])
    for block in blocks:
        lines += [*block, ""]
    lines += [f"- {note}" for note in notes]
    result = lines if blocks or notes else [NOT_APPLIED, "", NONE_PROPOSED]
    assert result[0] == NOT_APPLIED, f"proposal_lines lost its first line: {result!r}. Rule: the report says nothing is applied."
    return result


def build_audit(root, ceiling=None):
    assert isinstance(root, Path) and root.is_dir(), f"build_audit needs the project folder as a Path, got {root!r}. Fix: pass the folder."
    scan = instruction_scan(root, ceiling)
    sources = sources_of(root, scan)
    audited = audited_rules(root, sources)
    sections = [
        [f"# willitharness audit: {root.name}", "", "A free scan. It reads the folder and writes nothing."],
        ["## What loads", "", *[f"- {line}" for line in build_load_report(root, None, ceiling)]],
        ["## Rules", "", *rule_table(audited)],
        ["## Predictions", "", *prediction_lines(root, ceiling, sources)],
        ["## Proposed changes", "", *proposal_lines(root, scan, audited)],
        ["## Limits", "", *[f"- {limit}" for limit in LIMITS]],
    ]
    report = "\n\n".join("\n".join(section) for section in sections) + "\n"
    assert all(heading in report for heading in SECTION_HEADINGS), f"the report lost a section of {SECTION_HEADINGS!r}: {report!r}"
    return report
