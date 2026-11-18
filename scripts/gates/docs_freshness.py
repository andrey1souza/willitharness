import ast
import re
from pathlib import Path

import trace_check

CONTRACT_FILE = Path("docs") / "contract.md"
BACKLOG_FILE = Path("docs") / "plan" / "07-task-backlog.md"
MILESTONES_FILE = Path("docs") / "plan" / "03-milestones-and-checkpoints.md"
ISSUES_FILE = Path("docs") / "plan" / "contract-issues.md"
CLI_FILE = Path("src") / "willitharness" / "cli.py"
MAKEFILE = Path("Makefile")
FEATURES_DIRECTORY = Path("features")
MUTANT_DIRECTORY = Path("scripts") / "gates" / "mutant_modules"
PACKAGE_DIRECTORY = Path("src") / "willitharness"
README_FILE = Path("README.md")
DOCS_DIRECTORY = Path("docs")
PLAN_DIRECTORY = DOCS_DIRECTORY / "plan"
HISTORICAL_DIRECTORY = DOCS_DIRECTORY / "research"
HISTORICAL_FILES = (DOCS_DIRECTORY / "contract-v0.1.md",)
HISTORICAL_REASON = "these files record the past (spike findings, the frozen v0.1 contract) and are not edited to match today"
SOURCE_FILES = (CONTRACT_FILE,)
PLANNED_COMMANDS = ("report",)
PLANNED_DOCUMENTS = (MILESTONES_FILE, BACKLOG_FILE)
PLANNED_REASON = "the backlog and the gate table specify commands before they exist; every other document describes what is built"
SOURCE_REASON = "the contract is the source of the facts, so it cannot be checked against them"
WORLD_PREFIX = "W"
TASK_HEADING = re.compile(r"^### T\d+\.", re.MULTILINE)
TASK_HEADER = re.compile(r"^(\d+) tasks in dependency order", re.MULTILINE)
MILESTONE_HEADING = re.compile(r"^## M\d+\.", re.MULTILINE)
GATE_ROW = re.compile(r"^\| (G\d+\.\d+)( \(@live\))? \|", re.MULTILINE)
SCENARIO_LINE = re.compile(r"^\s*Scenario(?: Outline)?:", re.MULTILINE)
CONTRACT_VERSION = re.compile(r"^# .*\(v(\d+\.\d+)\)")
SUMMARY_ROW = re.compile(r"^\| [^|]+ \| T(\d+)(?: to T(\d+))? \| (\d+) \|$", re.MULTILINE)
ISSUE_NUMBER = re.compile(r"CI-(\d+)")
ISSUE_TABLE_ROW = re.compile(r"^\| CI-(\d+) \|", re.MULTILINE)
MAKE_TARGET = re.compile(r"^([\w-]+):", re.MULTILINE)
CHECK_RECIPE = re.compile(r"^check:(.*)$", re.MULTILINE)
CHECK_TARGET = "check"
CHECK_PHRASES = {
    "test": "tests",
    "zanity": "zanity",
    "mutants": "mutation module",
    "trace": "trace gate",
    "repo": "repo checks",
    "simulate": "simulation",
}
CHECK_CLAIM = re.compile(r"`make check` runs the ([^.]*)\.")
ID_LIST = re.compile(r"Contract IDs covered \| (\d+) \(([^)]+)\)")
SIMPLE_STATEMENTS = (
    ("contract-version", re.compile(r"Contract: v(\d+\.\d+)"), "contract_version"),
    ("contract-version", re.compile(r"\(contract v(\d+\.\d+)\)"), "contract_version"),
    ("contract-version", re.compile(r"updated to v(\d+\.\d+)"), "contract_version"),
    ("id-count", re.compile(r"(\d+) (?:contract )?IDs\b"), "id_count"),
    ("task-count", re.compile(r"Backlog tasks \| (\d+)"), "task_count"),
    ("task-last", re.compile(r"\(T01 to T(\d+)\)"), "task_count"),
    ("feature-files", re.compile(r"Feature files \| (\d+)"), "feature_count"),
    ("scenarios", re.compile(r"Scenarios \| (\d+)"), "scenario_count"),
    ("milestones", re.compile(r"Milestones \| (\d+)"), "milestone_count"),
    ("gates", re.compile(r"Gates \| (\d+)"), "gate_count"),
    ("live-gates", re.compile(r"of which (\d+) are live"), "live_gate_count"),
    ("mutant-modules", re.compile(r"(\d+) (?:mutant|mutation) modules"), "mutant_module_count"),
    ("world-rules", re.compile(rf"{WORLD_PREFIX}1 to {WORLD_PREFIX}(\d+)"), "world_rule_count"),
    ("issue-last", re.compile(r"CI-01 to CI-(\d+), all resolved"), "issue_count"),
)
OPEN_ISSUE_STATEMENTS = (
    re.compile(r"CI-(\d+) \(open\)"),
    re.compile(r"open CI-(\d+)"),
    re.compile(r"open \(CI-(\d+)"),
)
NOT_YET_PHRASES = (
    re.compile(r"No code exists yet"),
    re.compile(r"No code is written"),
    re.compile(r"\(not created\)"),
    re.compile(r"Every gate here is a promise"),
    re.compile(r"\(future repo\)"),
)
COMMAND_STATEMENT = re.compile(r"`willitharness ([a-z][^`]*)`")
COMMAND_WORDS = re.compile(r"^[a-z]+(?: check)?")
FLAG = re.compile(r"--[a-z][a-z-]*")
MAKE_STATEMENT = re.compile(r"(?:`|^)make ([a-z][\w-]*)", re.MULTILINE)
FILE_REFERENCE = re.compile(r"`([\w.][\w.-]*(?:/[\w.*-]+)+\.(?:md|py|sh|json|feature|toml|yml|lean|tla))(?=[ `])")
USAGE_SEPARATOR = " | "
USAGE_PREFIX = "usage: "
PROGRAM = "willitharness "
PLACEHOLDER_STARTS = ("<", "-", "[")


def matches_with_lines(text, pattern):
    assert isinstance(text, str), f"matches_with_lines needs text, got {type(text).__name__}. Fix: pass the file contents."
    assert hasattr(pattern, "finditer"), f"matches_with_lines needs a compiled pattern, got {pattern!r}. Fix: compile it."
    return [(text.count("\n", 0, found.start()) + 1, found) for found in pattern.finditer(text)]


def usage_text(cli_source):
    assert "USAGE" in cli_source, f"{CLI_FILE} has no USAGE. Rule: the CLI usage text is the source of the documented commands. Fix: restore the USAGE constant."
    for node in ast.parse(cli_source).body:
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "USAGE" for target in node.targets):
            usage = ast.literal_eval(node.value)
            assert isinstance(usage, str), f"USAGE in {CLI_FILE} must be a string literal, got {usage!r}. Fix: restore the literal."
            return usage
    raise AssertionError(f"{CLI_FILE} assigns no USAGE constant. Rule: the CLI usage text is a literal string. Fix: restore it.")


def command_name(words):
    assert isinstance(words, str), f"command_name needs text, got {type(words).__name__}. Fix: pass the text after the program name."
    matched = COMMAND_WORDS.match(words)
    name = matched.group(0) if matched else ""
    assert words.startswith(name), f"command name {name!r} must open {words!r}. Fix: correct COMMAND_WORDS."
    return name


def usage_commands(usage):
    assert usage.startswith(USAGE_PREFIX), f"the usage text starts with {USAGE_PREFIX!r}, got {usage[:20]!r}. Fix: restore the prefix."
    segments = usage[len(USAGE_PREFIX):].split(USAGE_SEPARATOR)
    commands = {}
    for segment in segments:
        assert segment.startswith(PROGRAM), f"usage segment {segment[:30]!r} does not start with {PROGRAM!r}. Fix: restore the usage format."
        body = segment[len(PROGRAM):]
        commands[command_name(body)] = set(FLAG.findall(body))
    return commands


def contract_facts(contract_text):
    assert isinstance(contract_text, str), f"contract_facts needs text, got {type(contract_text).__name__}. Fix: pass the contract."
    version = CONTRACT_VERSION.match(contract_text.splitlines()[0])
    assert version, f"the first line of {CONTRACT_FILE} has no (vN.N) version. Rule: the title carries the version. Fix: restore it."
    identifiers = set(trace_check.required_places(contract_text))
    world_numbers = [int(name[len(WORLD_PREFIX):]) for name in identifiers if re.fullmatch(rf"{WORLD_PREFIX}\d+", name)]
    return {
        "contract_version": version.group(1),
        "id_count": len(identifiers),
        "ids": identifiers,
        "world_rule_count": max(world_numbers),
        "resolved_issues": {int(number) for number in ISSUE_NUMBER.findall(contract_text)},
    }


def count_facts(root):
    assert root.is_dir(), f"{root} is not a directory. Fix: pass the repository root."
    backlog = (root / BACKLOG_FILE).read_text()
    header = TASK_HEADER.search(backlog)
    assert header, f"{BACKLOG_FILE} has no 'N tasks in dependency order' header. Rule: the header states the task count. Fix: restore it."
    gates = GATE_ROW.findall((root / MILESTONES_FILE).read_text())
    features = sorted((root / FEATURES_DIRECTORY).glob("*.feature"))
    issue_rows = ISSUE_TABLE_ROW.findall((root / ISSUES_FILE).read_text())
    return {
        "task_count": int(header.group(1)),
        "task_heading_count": len(TASK_HEADING.findall(backlog)),
        "milestone_count": len(MILESTONE_HEADING.findall(backlog)),
        "gate_count": len(gates),
        "live_gate_count": sum(1 for _, live in gates if live),
        "feature_count": len(features),
        "scenario_count": sum(len(SCENARIO_LINE.findall(path.read_text())) for path in features),
        "mutant_module_count": len(list((root / MUTANT_DIRECTORY).glob("*.py"))),
        "issue_count": max(int(number) for number in issue_rows),
    }


def tool_facts(root):
    assert root.is_dir(), f"{root} is not a directory. Fix: pass the repository root."
    makefile = (root / MAKEFILE).read_text()
    recipe = CHECK_RECIPE.search(makefile)
    assert recipe, f"{MAKEFILE} has no {CHECK_TARGET} target. Rule: make check is the entry gate. Fix: restore it."
    return {
        "make_targets": set(MAKE_TARGET.findall(makefile)),
        "check_dependencies": recipe.group(1).split(),
        "commands": usage_commands(usage_text((root / CLI_FILE).read_text())),
        "has_code": any((root / PACKAGE_DIRECTORY).glob("*.py")),
    }


def read_facts(root):
    assert root.is_dir(), f"{root} is not a directory. Fix: pass the repository root."
    facts = {**contract_facts((root / CONTRACT_FILE).read_text()), **count_facts(root), **tool_facts(root)}
    assert facts["task_count"] == facts["task_heading_count"], (
        f"{BACKLOG_FILE} says {facts['task_count']} tasks but holds {facts['task_heading_count']} task headings. "
        "Rule: the header count equals the headings. Fix: correct the header."
    )
    return facts


def checked_documents(root):
    assert root.is_dir(), f"{root} is not a directory. Fix: pass the repository root."
    assert HISTORICAL_REASON and SOURCE_REASON, "the exemptions must say why. Fix: restore the reasons."
    paths = [README_FILE, *sorted(path.relative_to(root) for path in (root / DOCS_DIRECTORY).rglob("*.md"))]
    skipped = (*HISTORICAL_FILES, *SOURCE_FILES)
    return [
        path for path in paths
        if path not in skipped and HISTORICAL_DIRECTORY not in path.parents
    ]


def simple_errors(path, text, facts):
    assert isinstance(text, str), f"simple_errors needs text, got {type(text).__name__}. Fix: pass the file contents."
    assert "contract_version" in facts, f"facts lack the contract version, got {sorted(facts)}. Fix: pass read_facts output."
    errors = []
    for name, pattern, key in SIMPLE_STATEMENTS:
        for line, found in matches_with_lines(text, pattern):
            if found.group(1) != str(facts[key]):
                errors.append(f"{path}:{line} says {found.group(0)!r} but the source says {key} = {facts[key]}. Rule: a stated {name} equals its source. Fix: correct the number or delete the statement.")
    return errors


def id_list_errors(path, text, facts):
    assert isinstance(text, str), f"id_list_errors needs text, got {type(text).__name__}. Fix: pass the file contents."
    assert "ids" in facts, f"facts lack the contract IDs, got {sorted(facts)}. Fix: pass read_facts output."
    errors = []
    for line, found in matches_with_lines(text, ID_LIST):
        listed = set(trace_check.expand_group(found.group(2)))
        if listed != facts["ids"]:
            gap = sorted(facts["ids"] ^ listed)
            errors.append(f"{path}:{line} lists IDs that differ from the contract by {gap}. Rule: a list of all contract IDs equals the contract. Fix: regenerate the list.")
    return errors


def open_issue_errors(path, text, facts):
    assert isinstance(text, str), f"open_issue_errors needs text, got {type(text).__name__}. Fix: pass the file contents."
    assert "resolved_issues" in facts, f"facts lack the resolved issues, got {sorted(facts)}. Fix: pass read_facts output."
    errors = []
    for pattern in OPEN_ISSUE_STATEMENTS:
        for line, found in matches_with_lines(text, pattern):
            if int(found.group(1)) in facts["resolved_issues"]:
                errors.append(f"{path}:{line} calls CI-{found.group(1)} open, but the contract resolves it. Rule: an issue the contract resolves is not open. Fix: say it is resolved.")
    return errors


def not_yet_errors(path, text, facts):
    assert isinstance(text, str), f"not_yet_errors needs text, got {type(text).__name__}. Fix: pass the file contents."
    assert "has_code" in facts, f"facts lack has_code, got {sorted(facts)}. Fix: pass read_facts output."
    if not facts["has_code"]:
        return []
    return [
        f"{path}:{line} says {found.group(0)!r} but {PACKAGE_DIRECTORY} holds code. Rule: no document says the code is missing while it exists. Fix: delete the statement."
        for pattern in NOT_YET_PHRASES
        for line, found in matches_with_lines(text, pattern)
    ]


def command_errors(path, text, facts):
    assert isinstance(text, str), f"command_errors needs text, got {type(text).__name__}. Fix: pass the file contents."
    assert "commands" in facts, f"facts lack the commands, got {sorted(facts)}. Fix: pass read_facts output."
    errors = []
    for line, found in matches_with_lines(text, COMMAND_STATEMENT):
        statement = found.group(1)
        name = command_name(statement)
        known = facts["commands"].get(name)
        if known is not None and name in PLANNED_COMMANDS:
            errors.append(f"{path}:{line} documents `willitharness {name}` as planned, but USAGE lists it. Rule: {PLANNED_REASON}. Fix: remove {name!r} from PLANNED_COMMANDS.")
        if known is None and name in PLANNED_COMMANDS and path in PLANNED_DOCUMENTS:
            continue
        if known is None:
            errors.append(f"{path}:{line} documents `willitharness {name}`, which USAGE in {CLI_FILE} does not list. Rule: a documented command exists. Fix: delete the statement or build the command.")
            continue
        unknown = sorted(set(FLAG.findall(statement)) - known)
        if unknown:
            errors.append(f"{path}:{line} documents flags {unknown} for `willitharness {name}`, which USAGE does not list. Rule: a documented flag exists. Fix: correct the flags.")
    return errors


def make_errors(path, text, facts):
    assert isinstance(text, str), f"make_errors needs text, got {type(text).__name__}. Fix: pass the file contents."
    assert "make_targets" in facts, f"facts lack the make targets, got {sorted(facts)}. Fix: pass read_facts output."
    named = [(line, found.group(1)) for line, found in matches_with_lines(text, MAKE_STATEMENT)]
    errors = [
        f"{path}:{line} names `make {target}`, which the {MAKEFILE} does not define. Rule: a documented target exists. Fix: correct the name."
        for line, target in named
        if target not in facts["make_targets"]
    ]
    unnamed = [target for target in facts["check_dependencies"] if target not in CHECK_PHRASES]
    assert not unnamed, f"{MAKEFILE} adds {unnamed} to {CHECK_TARGET} but CHECK_PHRASES has no phrase for them. Rule: every dependency has a documented phrase. Fix: add the phrase."
    for line, found in matches_with_lines(text, CHECK_CLAIM):
        missing = [target for target in facts["check_dependencies"] if CHECK_PHRASES[target] not in found.group(1)]
        if missing:
            errors.append(f"{path}:{line} says what `make {CHECK_TARGET}` runs but leaves out {missing}. Rule: the sentence names every dependency of the target. Fix: name them or delete the sentence.")
    return errors


def reference_errors(path, text, root):
    assert isinstance(text, str), f"reference_errors needs text, got {type(text).__name__}. Fix: pass the file contents."
    assert root.is_dir(), f"{root} is not a directory. Fix: pass the repository root."
    errors = []
    if path in PLANNED_DOCUMENTS:
        return errors
    for line, found in matches_with_lines(text, FILE_REFERENCE):
        reference = found.group(1)
        if "*" in reference:
            continue
        beside = (root / path).parent / reference
        if not beside.is_file() and not (root / reference).is_file():
            errors.append(f"{path}:{line} points at {reference}, which does not exist. Rule: a referenced file exists. Fix: correct the path.")
    return errors


def summary_errors(backlog_text, facts):
    assert isinstance(backlog_text, str), f"summary_errors needs text, got {type(backlog_text).__name__}. Fix: pass the backlog."
    assert "task_count" in facts, f"facts lack the task count, got {sorted(facts)}. Fix: pass read_facts output."
    rows = SUMMARY_ROW.findall(backlog_text)
    errors = []
    for first, last, count in rows:
        expected = int(last or first) - int(first) + 1
        if int(count) != expected:
            errors.append(f"{BACKLOG_FILE}: the summary row T{first} to T{last or first} says {count} tasks but spans {expected}. Rule: a row count equals its task range. Fix: correct the count.")
    total = sum(int(count) for _, _, count in rows)
    if total != facts["task_count"]:
        errors.append(f"{BACKLOG_FILE}: the summary rows add up to {total} tasks but the header says {facts['task_count']}. Rule: the summary covers every task. Fix: add the missing row.")
    return errors


def docs_freshness_errors(root):
    assert root.is_dir(), f"{root} is not a directory. Fix: pass the repository root."
    facts = read_facts(root)
    errors = summary_errors((root / BACKLOG_FILE).read_text(), facts)
    for path in checked_documents(root):
        text = (root / path).read_text()
        errors += simple_errors(path, text, facts)
        errors += id_list_errors(path, text, facts)
        errors += open_issue_errors(path, text, facts)
        errors += not_yet_errors(path, text, facts)
        errors += command_errors(path, text, facts)
        errors += make_errors(path, text, facts)
        errors += reference_errors(path, text, root)
    assert all(isinstance(error, str) for error in errors), f"errors must be text, got {errors!r}"
    return errors
