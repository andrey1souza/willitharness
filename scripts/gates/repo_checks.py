import argparse
import json
import re
import sys
import tomllib
from fnmatch import fnmatch
from pathlib import Path

import mutant_tables
import trace_check

REPO_ROOT = Path(__file__).resolve().parents[2]
EXIT_PASSED = 0
EXIT_FAILED = 1
MISTAKES_FILE = Path("docs") / "mistakes-to-rules.md"
CAUGHT_SECTION = "## Mistakes caught by a rule"
NEXT_SECTION = "## Mistakes with no rule yet"
TEST_REFERENCE = re.compile(r"`(tests/[\w/]+\.py)::(\w+)`")
IGNORE_FILE = Path(".gitignore")
WATCHER_FILES = (".testmondata", ".testmondata-shm", ".testmondata-wal")
BASELINE_FILE = Path("zanity-baseline.json")
ZANITY_CONFIG = Path("zanity.toml")
PLAN_DIRECTORY = Path("docs") / "plan"
RETIRED_COMMAND = "behave features/"
PENDING_FILE = Path("scripts") / "gates" / "trace_pending.json"


def mistakes_table_errors(root):
    assert root.is_dir(), f"{root} is not a directory. Fix: pass the repository root."
    text = (root / MISTAKES_FILE).read_text()
    assert CAUGHT_SECTION in text and NEXT_SECTION in text, f"{MISTAKES_FILE} lost a section heading. Fix: restore {CAUGHT_SECTION!r} and {NEXT_SECTION!r}."
    section = text[text.index(CAUGHT_SECTION):text.index(NEXT_SECTION)]
    rows = [line for line in section.splitlines() if line.startswith("| ") and "---" not in line][1:]
    errors = []
    if not rows:
        errors.append("the caught-mistakes table has no rows")
    for row in rows:
        references = TEST_REFERENCE.findall(row)
        if not references:
            errors.append(f"row has no test reference: {row[:80]}")
        for relative_path, test_name in references:
            test_file = root / relative_path
            if not test_file.is_file():
                errors.append(f"row names {relative_path}, which does not exist")
            elif f"def {test_name}(" not in test_file.read_text():
                errors.append(f"row names {relative_path}::{test_name}, which is not in the file")
    return errors


def gitignore_errors(root):
    assert root.is_dir(), f"{root} is not a directory. Fix: pass the repository root."
    patterns = [line for line in (root / IGNORE_FILE).read_text().splitlines() if line and not line.startswith("#")]
    errors = [
        f"{name} is written by the overwatch pytest watcher and is not ignored; patterns are {patterns}"
        for name in WATCHER_FILES
        if not any(fnmatch(name, pattern) for pattern in patterns)
    ]
    assert all(isinstance(error, str) for error in errors), f"errors must be text, got {errors!r}"
    return errors


def baseline_errors(root):
    assert root.is_dir(), f"{root} is not a directory. Fix: pass the repository root."
    assert BASELINE_FILE.suffix == ".json", f"{BASELINE_FILE} must name a JSON file"
    if (root / BASELINE_FILE).exists():
        return [f"{BASELINE_FILE} exists; the repository has no inherited findings, so fix new ones instead of recording them"]
    return []


def zanity_config_errors(root):
    assert root.is_dir(), f"{root} is not a directory. Fix: pass the repository root."
    config = tomllib.loads((root / ZANITY_CONFIG).read_text())
    assert isinstance(config, dict), f"{ZANITY_CONFIG} must be a TOML table, got {type(config).__name__}"
    disabled = {"everywhere": config.get("rules", {}).get("disable", [])}
    disabled.update({f"in {pattern}": table.get("disable", []) for pattern, table in config.get("paths", {}).items()})
    return [
        f"{ZANITY_CONFIG} disables {rules} {where}; never disable a zanity rule, fix what it finds"
        for where, rules in disabled.items()
        if rules
    ]


def plan_command_errors(root):
    assert root.is_dir(), f"{root} is not a directory. Fix: pass the repository root."
    files = sorted((root / PLAN_DIRECTORY).glob("*.md"))
    if not files:
        return [f"{PLAN_DIRECTORY} holds no plan files, so the retired-command check could not run"]
    errors = [f"{path.name} still names {RETIRED_COMMAND!r}; BDD gates run with pytest-bdd" for path in files if RETIRED_COMMAND in path.read_text()]
    assert all(isinstance(error, str) for error in errors), f"errors must be text, got {errors!r}"
    return errors


def mutant_table_errors(root, modules):
    assert root.is_dir(), f"{root} is not a directory. Fix: pass the repository root."
    assert isinstance(modules, dict), f"modules must map names to (tests, mutants), got {type(modules).__name__}. Fix: pass the mutant table."
    errors = []
    for module, (_, module_mutants) in modules.items():
        for name, relative_path, old, new in module_mutants:
            text = (root / relative_path).read_text()
            if text.count(old) != 1:
                errors.append(f"{module}/{name}: target occurs {text.count(old)} times in {relative_path}")
            if old == new:
                errors.append(f"{module}/{name}: the replacement equals the target")
    assert all(isinstance(error, str) for error in errors), f"errors must be text, got {errors!r}"
    return errors


def pending_errors(root):
    assert root.is_dir(), f"{root} is not a directory. Fix: pass the repository root."
    entries = trace_check.parse_pending((root / PENDING_FILE).read_text())
    errors = []
    for entry in entries:
        if not isinstance(entry, dict) or not {"id", "place", "reason"} <= entry.keys():
            errors.append(f"pending entry {entry!r} needs id, place and reason")
        elif entry["place"] not in trace_check.PLACE_KEYWORDS or not entry["reason"]:
            errors.append(f"pending entry {entry['id']} has place {entry['place']!r} and reason {entry['reason']!r}; use a known place and say why")
    assert all(isinstance(error, str) for error in errors), f"errors must be text, got {errors!r}"
    return errors


def registered_mutant_errors(root):
    assert root.is_dir(), f"{root} is not a directory. Fix: pass the repository root."
    assert mutant_tables.MODULES, "the mutant table lists no modules. Rule: a gate with no mutants proves nothing. Fix: add them."
    return mutant_table_errors(root, mutant_tables.MODULES)


CHECKS = {
    "mistakes-table": mistakes_table_errors,
    "gitignore": gitignore_errors,
    "no-zanity-baseline": baseline_errors,
    "zanity-config": zanity_config_errors,
    "plan-commands": plan_command_errors,
    "mutant-tables": registered_mutant_errors,
    "trace-pending": pending_errors,
}


def run_checks(root, checks):
    assert checks, "run_checks got no checks. Rule: a gate with no checks proves nothing. Fix: pass the check table."
    assert root.is_dir(), f"{root} is not a directory. Fix: pass the repository root."
    return [f"{name}: {error}" for name, check in checks.items() for error in check(root)]


def main(argv):
    assert isinstance(argv, list), f"main needs a list of arguments, got {argv!r}. Fix: pass sys.argv[1:]."
    assert all(isinstance(item, str) for item in argv), f"every argument must be text, got {argv!r}"
    parser = argparse.ArgumentParser(prog="repo_checks")
    parser.add_argument("--root", type=Path, default=REPO_ROOT)
    arguments = parser.parse_args(argv)
    failures = run_checks(arguments.root, CHECKS)
    for failure in failures:
        print(f"repo-checks: {failure}")
    if failures:
        return EXIT_FAILED
    print(f"repo-checks: {len(CHECKS)} checks passed")
    return EXIT_PASSED


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
