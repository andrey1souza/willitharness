import os
import subprocess
from pathlib import Path

import pytest

import docs_freshness
import repo_checks
from files import copy_tree, write_tree

README_WITHOUT_COUNTS = "# plan\n\n## Size of the plan\n| Item | Count |\n|---|---|\n| Milestones | 8 (M0 to M7) |\n| Total live cost cap | $2.00 |\n"
BACKLOG_WITHOUT_COUNTS = "# 07. Task backlog\n\nTasks in dependency order (contract v0.6).\n\n## M0. Skeleton\n\n### T01. a\nAs a maintainer, I want 3 gates.\n"
GOOD_TREE = {"docs/plan/README.md": README_WITHOUT_COUNTS, "docs/plan/07-task-backlog.md": BACKLOG_WITHOUT_COUNTS}
FORBIDDEN_README_LINES = [
    "| Contract IDs covered | 57 (V1 to V6) |",
    "| Feature files | 15 |",
    "| Scenarios | 167 |",
    "| Backlog tasks | 76 (T01 to T76) |",
    "| Gates | 53, of which 4 are live (G2.3) |",
    "The plan holds 167 scenarios.",
    "It covers 57 contract IDs.",
    "It has 15 feature files and 53 gates.",
    "It lists 76 tasks.",
    "| M0 skeleton | T01 to T03 | 3 |",
    "The plan runs (T01 to T76).",
]
FORBIDDEN_BACKLOG_HEADERS = [
    "76 tasks in dependency order (contract v0.6).\n",
    "Tasks in dependency order.\n\nSummary:\n| Milestone | Tasks | Count |\n|---|---|---|\n| M0 skeleton | T01 to T03 | 3 |\n",
]
REPOSITORY = Path(__file__).resolve().parents[2]
GIT_QUIET = ["git", "-c", "commit.gpgsign=false", "-c", "user.name=t", "-c", "user.email=t@example.com"]


def test_a_plan_without_counts_has_no_errors(tmp_path):
    write_tree(tmp_path, GOOD_TREE)
    errors = repo_checks.hand_count_errors(tmp_path)
    assert errors == [], f"a plan with no count must pass, got {errors}"


@pytest.mark.parametrize("line", FORBIDDEN_README_LINES)
def test_a_count_in_the_plan_readme_is_reported(tmp_path, line):
    write_tree(tmp_path, {**GOOD_TREE, "docs/plan/README.md": README_WITHOUT_COUNTS + line + "\n"})
    errors = repo_checks.hand_count_errors(tmp_path)
    assert len(errors) >= 1 and errors[0].startswith(f"docs/plan/README.md:{README_WITHOUT_COUNTS.count(chr(10)) + 1} states "), f"{line!r} must be reported at its line, got {errors}"
    assert "Rule:" in errors[0] and errors[0].endswith("conflict on it."), f"the error needs a Rule and a Fix, got {errors[0]!r}"


@pytest.mark.parametrize("header", FORBIDDEN_BACKLOG_HEADERS)
def test_a_count_in_the_backlog_header_is_reported(tmp_path, header):
    write_tree(tmp_path, {**GOOD_TREE, "docs/plan/07-task-backlog.md": "# 07. Task backlog\n\n" + header + "\n## M0. Skeleton\n"})
    errors = repo_checks.hand_count_errors(tmp_path)
    assert errors and all(error.startswith("docs/plan/07-task-backlog.md:") for error in errors), f"the header count must be reported, got {errors}"


def test_a_number_below_the_backlog_header_is_not_a_count_statement(tmp_path):
    write_tree(tmp_path, {**GOOD_TREE, "docs/plan/07-task-backlog.md": BACKLOG_WITHOUT_COUNTS + "- the pilot makes 120 runs over 2 tasks\n"})
    errors = repo_checks.hand_count_errors(tmp_path)
    assert errors == [], f"only the header is held to the rule, got {errors}"


def test_the_count_check_is_part_of_the_repository_checks():
    registered = repo_checks.CHECKS.get("no-hand-counts")
    assert registered is repo_checks.hand_count_errors, f"the check must be registered under its name, got {registered}"


def test_the_repository_plan_states_no_count():
    errors = repo_checks.hand_count_errors(REPOSITORY)
    assert errors == [], f"the plan docs must hold no count, got {errors}"


def copy_tracked_tree(destination):
    tracked = subprocess.run(["git", "-C", str(REPOSITORY), "ls-files"], capture_output=True, text=True, check=True).stdout.split()
    for name in tracked:
        source = REPOSITORY / name
        if source.is_file():
            write_tree(destination, {name: source.read_text()})
    return destination


def add_scenario(root, feature_name, title):
    path = root / "features" / feature_name
    path.write_text(path.read_text() + f"\n  Scenario: {title}\n    Given a plan\n")
    assert title in path.read_text(), f"{title} was not added to {path}"


def test_adding_a_scenario_needs_no_edit_to_any_count_line(tmp_path):
    root = copy_tracked_tree(tmp_path / "tree")
    first_feature, second_feature = sorted(path.name for path in (root / "features").glob("*.feature"))[:2]
    add_scenario(root, first_feature, "a new scenario one")
    add_scenario(root, second_feature, "a new scenario two")
    assert docs_freshness.docs_freshness_errors(root) == [], "the docs gate must pass with no doc edit after a scenario is added"
    assert repo_checks.hand_count_errors(root) == [], "the count check must pass with no doc edit after a scenario is added"


def git(repository, arguments):
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.com", "-C", str(repository), *arguments], capture_output=True, text=True)


def commit_on(repository, branch, parents):
    git(repository, ["add", "-A"])
    tree = git(repository, ["write-tree"]).stdout.strip()
    parent_arguments = [argument for parent in parents for argument in ("-p", parent)]
    environment = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.com"}
    commit = subprocess.run(["git", "-C", str(repository), "commit-tree", tree, *parent_arguments, "-m", branch], capture_output=True, text=True, env=environment | {"PATH": os.environ["PATH"]}).stdout.strip()
    assert commit, f"commit-tree made no commit for {branch}"
    git(repository, ["update-ref", f"refs/heads/{branch}", commit])
    return commit


def merge_two_branches(tmp_path, edit_one, edit_two):
    root = copy_tracked_tree(tmp_path / "tree")
    initialised = git(root, ["init", "-q", "-b", "main"])
    assert initialised.returncode == 0, f"git init failed in {root}: {initialised.stderr}"
    base = commit_on(root, "main", [])
    for branch, edit in (("one", edit_one), ("two", edit_two)):
        git(root, ["checkout", "-q", "-b", branch, "main"])
        edit(root)
        commit_on(root, branch, [base])
    return root, git(root, ["merge", "--no-commit", "--no-ff", "one"])


def first_two_features(root):
    return sorted(path.name for path in (root / "features").glob("*.feature"))[:2]


def test_two_branches_that_add_a_scenario_each_merge_without_a_conflict(tmp_path):
    root, merged = merge_two_branches(
        tmp_path,
        lambda tree: add_scenario(tree, first_two_features(tree)[0], "scenario of branch one"),
        lambda tree: add_scenario(tree, first_two_features(tree)[1], "scenario of branch two"),
    )
    assert merged.returncode == 0, f"two scenario PRs must merge cleanly, got {merged.stdout}{merged.stderr}"
    assert docs_freshness.docs_freshness_errors(root) == [], "the merged tree must pass the docs gate"
    assert repo_checks.hand_count_errors(root) == [], "the merged tree must pass the count check"


def test_two_branches_that_edit_the_same_plan_line_do_conflict(tmp_path):
    def edit(text):
        return lambda tree: write_tree(tree, {"docs/plan/README.md": README_WITHOUT_COUNTS.replace("Milestones | 8", text)})
    _, merged = merge_two_branches(tmp_path, edit("Milestones | 9"), edit("Milestones | 10"))
    assert merged.returncode != 0 and "docs/plan/README.md" in merged.stdout, f"the control must conflict on the shared line, got {merged.stdout}{merged.stderr}"
