import argparse
import ast
import json
import re
import subprocess
import sys
import tomllib
from fnmatch import fnmatch
from pathlib import Path

import docs_freshness
import hook_checks
import leak_check
import message_check
import mutant_tables
import pilot_live
import trace_check
import trace_fixtures
import workflow_checks

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
GENERATED_PATHS = (Path("formal") / "tla" / "generated", Path("site") / "data" / "gate_status.json")
FIXTURE_FOLDERS = ("tests", "fixtures", "features")
TOOL_CACHES = ("__pycache__", ".pytest_cache")
MAKEFILE = Path("Makefile")
SOURCE_FOLDER = "src"
DATA_HEADING = "## Data"
DATA_MAX_LINES = 6
DATA_TERMS = ("run records", "transcripts", "calls logs", "reachability", "state", "approvals", "task text", "redacted", "ignores", "rm -r .willitharness", ".willitharness/<plan>")
LIVE_RESULT = Path("fixtures") / "results" / "g4_4.json"
PAID_TARGET = "pilot"
UNPAID_TARGETS = ("check", "live")
PAID_REFERENCE = re.compile(r"\bpilot")
README_FILE = Path("README.md")
ISOLATION_HEADING = "## Limits of isolation"
ISOLATION_MAX_LINES = 6
ISOLATION_PHRASES = (
    "effect runs use claude's own sandbox and have no network",
    "guard runs use macos sandbox-exec and their network is open",
    "the linux sandbox path is untested",
    "run only plans you have read",
    "not a security boundary against a hostile plan",
    "the claude process itself is not confined",
)
DARWIN = "darwin"
DARWIN_SKIP = re.compile(r"^pytestmark\s*=.*sys\.platform\s*!=\s*\"" + DARWIN + r"\"", re.MULTILINE)
PUBLISH_DOCUMENTS = (Path("README.md"), Path("SECURITY.md"), MAKEFILE)
LAND_LOCAL_WORD = re.compile(r"--land-local")
NEGATION_WORD = re.compile(r"\b(?:not|never|no)\b", re.IGNORECASE)
PUBLISH_WORD = re.compile(r"\b(?:publish\w*|push\w*|pull requests?|PRs?)\b")
PARAGRAPH_BREAK = re.compile(r"\n\s*\n")
SENTENCE_BREAK = re.compile(r"(?<=[.!?])\s+")
INTEGRATE_FILE = Path("scripts") / "guards" / "integrate.py"
GIT_HELPERS = ("run_checked", "git_lines")
FORCE_FLAG = re.compile(r"^-[A-Za-z]*[fD][A-Za-z]*$")
PR_TEXT_FILE = Path("scripts") / "guards" / "pr_text.py"
REMOVABLE_SITE_MODULES = ("status",)
FORBIDDEN_ARGUMENTS = ("--force", "--force-with-lease", "--hard", "push", "update-ref")
LEAK_FOLDERS = ("src", "tests", "features", "docs", "fixtures")
CONTRACT_FILE = Path("docs") / "contract.md"
CONTRACT_SENTENCES = ("Ending a plan needs no validated world.", "Each run record carries the hash of the world files at the start of the run (T62, T65).", "Each run record carries the model name (T73).")


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


def isolation_limit_errors(text):
    assert isinstance(text, str), f"isolation_limit_errors needs text, got {type(text).__name__}. Fix: pass the README text."
    assert ISOLATION_PHRASES, "no isolation phrases are required. Rule: the limits are checked word for word. Fix: restore ISOLATION_PHRASES."
    lines = text.splitlines()
    if lines.count(ISOLATION_HEADING) != 1:
        return [f"the README has {lines.count(ISOLATION_HEADING)} {ISOLATION_HEADING!r} headings, not one. Rule: the limits have one home. Fix: restore the heading once."]
    first = lines.index(ISOLATION_HEADING) + 1
    following = [number for number, line in enumerate(lines[first:], start=first) if line.startswith("## ")]
    body = [line for line in lines[first:following[0] if following else len(lines)] if line.strip()]
    normalized = " ".join(" ".join(body).replace("`", "").lower().split())
    errors = [f"the isolation limits lack the phrase {phrase!r}. Rule: the README states each limit. Fix: restore the sentence." for phrase in ISOLATION_PHRASES if phrase not in normalized]
    if len(body) > ISOLATION_MAX_LINES:
        errors.append(f"the isolation limits run {len(body)} lines, over {ISOLATION_MAX_LINES}. Rule: keep the paragraph short. Fix: cut it.")
    assert all(isinstance(error, str) for error in errors), f"errors must be text, got {errors!r}"
    return errors


def readme_isolation_errors(root):
    assert root.is_dir(), f"{root} is not a directory. Fix: pass the repository root."
    assert README_FILE.suffix == ".md", f"{README_FILE} must name a Markdown file"
    return isolation_limit_errors((root / README_FILE).read_text())


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


def generated_errors_among(names):
    assert isinstance(names, list), f"names must be a list of tracked paths, got {type(names).__name__}. Fix: pass the git ls-files output split into lines."
    assert all(isinstance(name, str) for name in names), f"every tracked path must be text, got {names!r}"
    return [
        f"{name} is generated and must not be tracked. Rule: counts are computed in the build, folders by check_models. Fix: git rm --cached it"
        for name in names
        if any(name == generated.as_posix() or name.startswith(f"{generated.as_posix()}/") for generated in GENERATED_PATHS)
    ]


def tracked_generated_errors(root):
    assert root.is_dir(), f"{root} is not a directory. Fix: pass the repository root."
    listed = subprocess.run(["git", "-C", str(root), "ls-files"], capture_output=True, text=True, check=True).stdout.splitlines()
    errors = generated_errors_among(listed)
    assert all(isinstance(error, str) for error in errors), f"errors must be text, got {errors!r}"
    return errors


def ignored_fixture_errors_among(names):
    assert isinstance(names, list), f"names must be a list of ignored paths, got {type(names).__name__}. Fix: pass the git ls-files output split into lines."
    assert all(isinstance(name, str) for name in names), f"every ignored path must be text, got {names!r}"
    return [
        f"{name} is ignored by git, so CI never sees it. Rule: a file under {', '.join(FIXTURE_FOLDERS)} is tracked or not there. Fix: git add -f it, or delete it."
        for name in names
        if not any(part in TOOL_CACHES for part in Path(name).parts)
    ]


def ignored_fixture_errors(root):
    assert root.is_dir(), f"{root} is not a directory. Fix: pass the repository root."
    command = ["git", "-C", str(root), "ls-files", "--others", "--ignored", "--exclude-standard", "--", *FIXTURE_FOLDERS]
    listed = subprocess.run(command, capture_output=True, text=True, check=True).stdout.splitlines()
    errors = ignored_fixture_errors_among(listed)
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


def darwin_only_tests(root, tests):
    assert root.is_dir(), f"{root} is not a directory. Fix: pass the repository root."
    located = [root / path for path in tests]
    files = [file for path in located for file in (path.rglob("test_*.py") if path.is_dir() else [path])]
    assert all(file.is_file() for file in files), f"a test path in {tests!r} does not exist under {root}. Fix: correct the mutant module."
    return [file for file in files if DARWIN_SKIP.search(file.read_text())]


def platform_errors(root, modules, platforms):
    assert root.is_dir(), f"{root} is not a directory. Fix: pass the repository root."
    assert set(modules) == set(platforms), f"modules {sorted(modules)} and platforms {sorted(platforms)} differ. Fix: pass both from mutant_tables."
    errors = []
    for module, (tests, _) in modules.items():
        skipping = bool(darwin_only_tests(root, tests))
        if skipping and platforms[module] != DARWIN:
            errors.append(f"{module}: a test skips off {DARWIN}, so its mutants survive elsewhere. Fix: declare PLATFORM = {DARWIN!r} in the mutant module")
        if platforms[module] == DARWIN and not skipping:
            errors.append(f"{module}: declares PLATFORM = {DARWIN!r} but no test in TESTS skips off {DARWIN}. Fix: remove the declaration")
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


def paid_target_errors(root):
    assert root.is_dir(), f"{root} is not a directory. Fix: pass the repository root."
    blocks = (root / MAKEFILE).read_text().split("\n\n")
    targets = {block.split(":", 1)[0]: block for block in blocks if ":" in block}
    assert targets, f"{MAKEFILE} holds no targets. Rule: the repository has a Makefile. Fix: restore it."
    errors = [f"{MAKEFILE} has no {PAID_TARGET} target. Fix: add it."] if PAID_TARGET not in targets else []
    errors += [
        f"make {name} reaches the paid {PAID_TARGET} gate. Rule: STOP-2 caps its cost, so only make {PAID_TARGET} runs it. Fix: remove it from {name}."
        for name in UNPAID_TARGETS
        if PAID_REFERENCE.search(targets.get(name, ""))
    ]
    assert all(isinstance(error, str) for error in errors), f"errors must be text, got {errors!r}"
    return errors


def data_statement_errors(root):
    assert root.is_dir(), f"{root} is not a directory. Fix: pass the repository root."
    assert DATA_TERMS, "no data terms are required. Rule: a gate with no expectations proves nothing."
    store = docs_freshness.RUNTIME_PATHS[0]
    section = workflow_checks.section_under((root / README_FILE).read_text(), DATA_HEADING)
    if section is None:
        return [f"{README_FILE} has no '{DATA_HEADING}' section, so users cannot tell what {store} stores or how to delete it"]
    errors = [f"{README_FILE} section '{DATA_HEADING}' does not say {term!r}" for term in DATA_TERMS if term not in section]
    lines = [line for line in section.splitlines() if line.strip()]
    if len(lines) > DATA_MAX_LINES:
        errors.append(f"{README_FILE} section '{DATA_HEADING}' has {len(lines)} lines, above {DATA_MAX_LINES}. Fix: shorten it")
    patterns = [line for line in (root / IGNORE_FILE).read_text().splitlines() if line and not line.startswith("#")]
    if not any(fnmatch(f"{store}/", pattern) for pattern in patterns):
        errors.append(f"{IGNORE_FILE} does not ignore {store}/, so the README claim that git ignores it is false. Fix: add the pattern")
    return errors


def result_detector_errors(root):
    assert root.is_dir(), f"{root} is not a directory. Fix: pass the repository root."
    recorded = json.loads((root / LIVE_RESULT).read_text()).get("detector")
    used = list(pilot_live.STOP_SERVER_ACTIONS)
    errors = [] if recorded == used else [f"{LIVE_RESULT} records the detector {recorded!r}, but the pilot gate uses {used!r}. Rule: the result names the detector of its run. Fix: record the gate's actions."]
    assert all(isinstance(error, str) for error in errors), f"errors must be text, got {errors!r}"
    return errors


def contract_sentence_errors(root):
    assert root.is_dir(), f"{root} is not a directory. Fix: pass the repository root."
    text = " ".join((root / CONTRACT_FILE).read_text().split())
    errors = [f"{CONTRACT_FILE} lacks the sentence {sentence!r}. Rule: the contract states what the code does about ending a plan and world hashes. Fix: restore it." for sentence in CONTRACT_SENTENCES if sentence not in text]
    assert all(isinstance(error, str) for error in errors), f"errors must be text, got {errors!r}"
    return errors


def registered_mutant_errors(root):
    assert root.is_dir(), f"{root} is not a directory. Fix: pass the repository root."
    assert mutant_tables.MODULES, "the mutant table lists no modules. Rule: a gate with no mutants proves nothing. Fix: add them."
    return mutant_table_errors(root, mutant_tables.MODULES)


def registered_platform_errors(root):
    assert root.is_dir(), f"{root} is not a directory. Fix: pass the repository root."
    assert mutant_tables.PLATFORMS, "the mutant table lists no platforms. Rule: every module has one. Fix: add mutant modules."
    return platform_errors(root, mutant_tables.MODULES, mutant_tables.PLATFORMS)


def publishing_sentences(text):
    assert isinstance(text, str), f"publishing_sentences needs text, got {type(text).__name__}. Fix: pass the file contents."
    assert PUBLISH_WORD.pattern and LAND_LOCAL_WORD.pattern, "a pattern is empty. Rule: the check needs both words. Fix: restore the patterns."
    sentences = [" ".join(sentence.split()) for paragraph in PARAGRAPH_BREAK.split(text) for sentence in SENTENCE_BREAK.split(paragraph)]
    return [sentence for sentence in sentences if LAND_LOCAL_WORD.search(sentence) and PUBLISH_WORD.search(sentence) and not NEGATION_WORD.search(sentence)]


def publish_documents(root):
    assert root.is_dir(), f"{root} is not a directory. Fix: pass the repository root."
    assert docs_freshness.HISTORICAL_FILES, "no historical files are named. Rule: the frozen contract is exempt by name. Fix: restore HISTORICAL_FILES."
    top_level = sorted(path.relative_to(root) for path in (root / docs_freshness.DOCS_DIRECTORY).glob("*.md"))
    named = [path for path in (*PUBLISH_DOCUMENTS, *top_level) if path not in docs_freshness.HISTORICAL_FILES]
    return [path for path in named if (root / path).is_file()]


def integrate_publishing_errors(root):
    assert root.is_dir(), f"{root} is not a directory. Fix: pass the repository root."
    assert PUBLISH_DOCUMENTS, "PUBLISH_DOCUMENTS is empty. Rule: the check names the documents it reads. Fix: restore it."
    return [
        f"{path} tells the reader to publish with --land-local: {sentence[:80]!r}. Rule: --land-local moves local main only; the publish path is integrate.py (verify), git push origin <branch> and a pull request. Fix: reword as in scripts/guards/pr_text.py."
        for path in publish_documents(root)
        for sentence in publishing_sentences((root / path).read_text())
    ]


def is_git_helper_call(node):
    assert isinstance(node, ast.AST), f"is_git_helper_call needs an ast node, got {type(node).__name__}. Fix: pass a node from ast.walk."
    assert GIT_HELPERS, "GIT_HELPERS is empty. Rule: the check names the helpers it scans. Fix: restore it."
    return isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in GIT_HELPERS


def forbidden_git_arguments(source):
    assert isinstance(source, str), f"forbidden_git_arguments needs source text, got {type(source).__name__}. Fix: pass the file contents."
    assert GIT_HELPERS and FORBIDDEN_ARGUMENTS, "the helper or argument list is empty. Rule: the check names what it scans. Fix: restore the constants."
    calls = [node for node in ast.walk(ast.parse(source)) if is_git_helper_call(node)]
    lists = [argument for call in calls for argument in call.args if isinstance(argument, (ast.List, ast.Tuple))]
    elements = [element for argument in lists for element in argument.elts if isinstance(element, ast.Constant) and isinstance(element.value, str)]
    return [(element.lineno, element.value) for element in elements if FORCE_FLAG.match(element.value) or element.value in FORBIDDEN_ARGUMENTS]


def imported_modules(source):
    assert isinstance(source, str), f"imported_modules needs source text, got {type(source).__name__}. Fix: pass the file contents."
    nodes = list(ast.walk(ast.parse(source)))
    assert all(isinstance(node, ast.AST) for node in nodes), f"ast.walk gave a non-node in {nodes!r}"
    plain = [alias.name for node in nodes if isinstance(node, ast.Import) for alias in node.names]
    sourced = [node.module for node in nodes if isinstance(node, ast.ImportFrom) and node.module]
    return {name.split(".")[0] for name in (*plain, *sourced)}


def pr_text_import_errors(root):
    assert root.is_dir(), f"{root} is not a directory. Fix: pass the repository root."
    assert REMOVABLE_SITE_MODULES, "REMOVABLE_SITE_MODULES is empty. Rule: the check names the modules that may go. Fix: restore it."
    found = imported_modules((root / PR_TEXT_FILE).read_text()) & set(REMOVABLE_SITE_MODULES)
    return [
        f"{PR_TEXT_FILE} imports {name}, a site module another branch deletes. Rule: pr_text.py stays self-contained. Fix: move the code it needs into pr_text.py."
        for name in sorted(found)
    ]


def failure_message_errors(root):
    assert root.is_dir(), f"{root} is not a directory. Fix: pass the repository root."
    assert (root / SOURCE_FOLDER).is_dir(), f"{root} has no {SOURCE_FOLDER} folder. Rule: the gate scans the shipped source. Fix: run it from the repository root."
    return message_check.source_errors(root / SOURCE_FOLDER)


def integrate_source_errors(root):
    assert root.is_dir(), f"{root} is not a directory. Fix: pass the repository root."
    assert INTEGRATE_FILE.name == "integrate.py", f"INTEGRATE_FILE is {INTEGRATE_FILE}. Fix: point it at integrate.py."
    found = forbidden_git_arguments((root / INTEGRATE_FILE).read_text())
    return [
        f"{INTEGRATE_FILE}:{line} passes {argument!r} to git. Rule: integrate never forces, resets, cleans or pushes. Fix: use a safe argument such as -d or --ff-only."
        for line, argument in found
    ]


def home_path_errors(root):
    assert root.is_dir(), f"{root} is not a directory. Fix: pass the repository root."
    assert LEAK_FOLDERS, "no folders are scanned. Rule: the hygiene gate scans the shipped folders. Fix: restore LEAK_FOLDERS."
    present = [root / name for name in LEAK_FOLDERS if (root / name).is_dir()]
    return [
        f"{leak} holds a home-directory path. Rule: no user path reaches the repo. Fix: replace it with a relative path or a placeholder."
        for leak in leak_check.leaks_in(present)
    ] if present else []


CHECKS = {
    "no-home-paths": home_path_errors,
    "mistakes-table": mistakes_table_errors,
    "readme-isolation-limits": readme_isolation_errors,
    "gitignore": gitignore_errors,
    "no-zanity-baseline": baseline_errors,
    "zanity-config": zanity_config_errors,
    "plan-commands": plan_command_errors,
    "mutant-tables": registered_mutant_errors,
    "mutant-platforms": registered_platform_errors,
    "trace-pending": pending_errors,
    "paid-gate-target": paid_target_errors,
    "result-detector": result_detector_errors,
    "no-tracked-generated": tracked_generated_errors,
    "no-ignored-fixtures": ignored_fixture_errors,
    "trace-fixtures": trace_fixtures.stale_fixture_errors,
    "contract-sentences": contract_sentence_errors,
    "docs_freshness": docs_freshness.docs_freshness_errors,
    "readme-data-statement": data_statement_errors,
    "integrate-not-for-publishing": integrate_publishing_errors,
    "integrate-source-never-forces": integrate_source_errors,
    "pr-text-self-contained": pr_text_import_errors,
    "failure-messages": failure_message_errors,
    **workflow_checks.CHECKS,
    **hook_checks.CHECKS,
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
