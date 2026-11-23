import subprocess

import repo_checks
from files import write_tree

IGNORE_RULES = ".willitharness/\n__pycache__/\nbuild/\n"
FIXTURE_FILE = "tests/golden/demo/.willitharness/demo/runs.jsonl"
SCANNED_FOLDERS = ("tests", "fixtures", "features")


def start_repository(tmp_path, tree):
    write_tree(tmp_path, {".gitignore": IGNORE_RULES, **tree})
    subprocess.run(["git", "-C", str(tmp_path), "init", "-q"], check=True)
    return tmp_path


def force_add(repository, name):
    subprocess.run(["git", "-C", str(repository), "add", "-f", name], check=True)


def test_an_ignored_fixture_file_is_reported_with_its_path_a_rule_and_a_fix(tmp_path):
    repository = start_repository(tmp_path, {FIXTURE_FILE: "{}\n"})
    errors = repo_checks.ignored_fixture_errors(repository)
    assert len(errors) == 1, f"expected one ignored fixture, got {errors}"
    assert FIXTURE_FILE in errors[0], f"the error must name the file, got {errors[0]!r}"
    assert "Rule:" in errors[0] and "Fix:" in errors[0], f"the error must state a rule and a fix, got {errors[0]!r}"


def test_a_force_added_fixture_file_has_no_error(tmp_path):
    repository = start_repository(tmp_path, {FIXTURE_FILE: "{}\n"})
    force_add(repository, FIXTURE_FILE)
    assert repo_checks.ignored_fixture_errors(repository) == [], "a tracked fixture is seen by CI and must pass"


def test_tool_caches_and_files_outside_the_fixture_folders_have_no_error(tmp_path):
    repository = start_repository(tmp_path, {"tests/unit/__pycache__/x.pyc": "x", "build/out.txt": "x", "tests/unit/test_a.py": "x\n"})
    assert repo_checks.ignored_fixture_errors(repository) == [], "caches and files outside tests, fixtures and features must pass"


def test_every_fixture_folder_is_scanned(tmp_path):
    tree = {f"{folder}/a/.willitharness/x.json": "{}\n" for folder in SCANNED_FOLDERS}
    errors = repo_checks.ignored_fixture_errors(start_repository(tmp_path, tree))
    assert len(errors) == len(SCANNED_FOLDERS), f"one error per folder expected, got {errors}"


def test_the_check_is_registered():
    assert "no-ignored-fixtures" in repo_checks.CHECKS, "the check must run with the other repo checks"
