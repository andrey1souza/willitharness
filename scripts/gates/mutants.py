import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from mutant_tables import ANY_PLATFORM, MODULES, PLATFORMS

REPO_ROOT = Path(__file__).resolve().parents[2]
EXIT_ALL_KILLED = 0
EXIT_SURVIVED = 1
EXIT_BASELINE_BROKEN = 2
ALL_MODULES = "all"
PYTEST_PASSED = 0
PYTEST_TESTS_FAILED = 1
PYTEST_NO_TESTS = 5
COPIED_DIRECTORIES = ("src", "scripts", "fixtures")
IMPORT_PATHS = ("src", "scripts", "scripts/gates", "scripts/site")
GOLDEN_RELATIVE = Path("formal") / "lean"
SUPPORT_DIRECTORY = Path("tests") / "support"


def mutated_text(text, old, new):
    assert old, "mutated_text got an empty target. Rule: an empty target matches everywhere. Fix: name the text to replace."
    assert text.count(old) == 1, (
        "target %r occurs %d times, not once. Rule: a mutant changes one place. "
        "Fix: lengthen the target until it is unique." % (old, text.count(old))
    )
    return text.replace(old, new)


def copy_sources(destination):
    assert not any(destination.iterdir()), f"{destination} is not empty. Rule: each mutant gets a clean copy. Fix: pass a new directory."
    for name in COPIED_DIRECTORIES:
        shutil.copytree(REPO_ROOT / name, destination / name, ignore=shutil.ignore_patterns("__pycache__"))
    golden = destination / GOLDEN_RELATIVE
    golden.mkdir(parents=True)
    for table in (REPO_ROOT / GOLDEN_RELATIVE).glob("*.json"):
        shutil.copy2(table, golden / table.name)
    assert (destination / "src" / "willitharness").is_dir(), f"the copy in {destination} has no willitharness package"
    assert any(golden.iterdir()), f"the copy in {destination} has no golden tables. Rule: conformance tests read them. Fix: check {REPO_ROOT / GOLDEN_RELATIVE}."


def run_tests(source_root, tests):
    assert tests, "run_tests got no test paths. Rule: a run needs tests. Fix: name at least one path."
    assert source_root.is_dir(), f"{source_root} is not a directory. Fix: pass the copied source root."
    paths = os.pathsep.join([*(str(source_root / name) for name in IMPORT_PATHS), str(REPO_ROOT / SUPPORT_DIRECTORY)])
    command = [
        sys.executable, "-m", "pytest", *tests, "-x", "-q", "-p", "no:cacheprovider",
        "-o", "pythonpath=" + paths.replace(os.pathsep, " "),
    ]
    return subprocess.run(command, cwd=REPO_ROOT, capture_output=True, text=True).returncode


def is_killed(source_root, tests, mutant):
    name, relative_path, old, new = mutant
    target = source_root / relative_path
    assert target.is_file(), f"mutant {name} names {relative_path}, which is not in the copy. Fix: correct the path in the table."
    assert old != new, f"mutant {name} replaces the text with itself. Rule: a mutant changes behaviour. Fix: correct the table."
    target.write_text(mutated_text(target.read_text(), old, new))
    code = run_tests(source_root, tests)
    assert code in (PYTEST_PASSED, PYTEST_TESTS_FAILED, PYTEST_NO_TESTS), (
        f"pytest exited {code} on mutant {name}. Rule: only a test failure kills a mutant; any other code means the mutant "
        "broke the import or the run. Fix: change the mutant so the code still imports."
    )
    return code == PYTEST_TESTS_FAILED


def run_module(module, tests_override):
    assert module in MODULES, f"unknown module {module!r}. Fix: use one of {sorted(MODULES)}."
    default_tests, mutants = MODULES[module]
    tests = tests_override or list(default_tests)
    missing = [path for path in tests if not (REPO_ROOT / path).exists()]
    assert not missing, f"test paths {missing} do not exist. Rule: a gate runs real tests. Fix: pass existing paths."
    assert mutants, f"module {module} has no mutants. Rule: a gate with no mutants proves nothing. Fix: add them to the table."
    with tempfile.TemporaryDirectory(prefix="mutants-baseline-") as directory:
        baseline = Path(directory)
        copy_sources(baseline)
        baseline_code = run_tests(baseline, tests)
    if baseline_code == PYTEST_TESTS_FAILED:
        print("baseline: the tests fail on unmutated code. Rule: a mutant is killed only by a test that passes without it. Fix: make the tests pass first.")
        return EXIT_BASELINE_BROKEN
    killed = 0
    for mutant in mutants:
        with tempfile.TemporaryDirectory(prefix="mutants-") as directory:
            workspace = Path(directory)
            copy_sources(workspace)
            survived = not is_killed(workspace, tests, mutant)
        print(("SURVIVED " if survived else "killed   ") + mutant[0])
        killed += 0 if survived else 1
    print("mutants killed: %d/%d" % (killed, len(mutants)))
    return EXIT_ALL_KILLED if killed == len(mutants) else EXIT_SURVIVED


def skipped_modules(names, platform):
    assert isinstance(names, list), f"names must be a list, got {names!r}. Fix: pass module names."
    assert all(name in PLATFORMS for name in names), f"unknown module in {names!r}. Fix: use one of {sorted(PLATFORMS)}."
    return [name for name in names if PLATFORMS[name] not in (ANY_PLATFORM, platform)]


def skipped_line(skipped):
    assert isinstance(skipped, list), f"skipped must be a list, got {skipped!r}. Fix: pass module names."
    assert all(isinstance(name, str) for name in skipped), f"every skipped name must be text, got {skipped!r}"
    return "skipped modules: " + ", ".join(skipped)


def main(argv, platform=sys.platform):
    assert isinstance(argv, list), f"main needs a list of arguments, got {argv!r}. Fix: pass sys.argv[1:]."
    assert all(isinstance(item, str) for item in argv), f"every argument must be text, got {argv!r}"
    parser = argparse.ArgumentParser(prog="mutants")
    parser.add_argument("module", choices=[*sorted(MODULES), ALL_MODULES])
    parser.add_argument("--tests", nargs="+")
    arguments = parser.parse_args(argv)
    names = sorted(MODULES) if arguments.module == ALL_MODULES else [arguments.module]
    skipped = skipped_modules(names, platform)
    codes = []
    for name in names:
        if arguments.module == ALL_MODULES:
            print(f"== {name}")
        if name in skipped:
            print(f"skipped {name}: needs {PLATFORMS[name]}")
        else:
            codes.append(run_module(name, arguments.tests))
    if arguments.module == ALL_MODULES and skipped:
        print(skipped_line(skipped))
    return max(codes, default=EXIT_ALL_KILLED)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
