import pytest

import repo_checks
from files import write_tree

GOOD_DATA = "# tool\n\n## Data\n`.willitharness/` stores run records, transcripts, calls logs, reachability, state and approvals.\nTranscripts can hold your task text. Secret values are redacted.\nGit ignores the folder.\nDelete all with `rm -r .willitharness`. One plan: `rm -r .willitharness/<plan>`.\n\n## Checks\nx\n"
DATA_FILES = {"README.md": GOOD_DATA, ".gitignore": ".willitharness/\n"}
def test_a_readme_with_the_data_section_and_an_ignored_store_passes(tmp_path):
    write_tree(tmp_path, DATA_FILES)
    assert repo_checks.data_statement_errors(tmp_path) == [], "a complete data section must pass"
    assert "readme-data-statement" in repo_checks.CHECKS, "the data check must be registered"


def test_a_readme_without_the_data_heading_is_reported(tmp_path):
    write_tree(tmp_path, {**DATA_FILES, "README.md": GOOD_DATA.replace("## Data", "## Storage")})
    errors = repo_checks.data_statement_errors(tmp_path)
    assert errors == ["README.md has no '## Data' section, so users cannot tell what .willitharness stores or how to delete it"], f"got {errors}"


@pytest.mark.parametrize("term", ["run records", "transcripts", "calls logs", "reachability", "state", "approvals", "task text", "redacted", "ignores", "rm -r .willitharness", ".willitharness/<plan>"])
def test_a_data_section_missing_a_term_is_reported(tmp_path, term):
    write_tree(tmp_path, {**DATA_FILES, "README.md": GOOD_DATA.replace(term, "other")})
    errors = repo_checks.data_statement_errors(tmp_path)
    assert f"README.md section '## Data' does not say {term!r}" in errors, f"got {errors}"


def test_a_data_section_above_six_lines_is_reported(tmp_path):
    write_tree(tmp_path, {**DATA_FILES, "README.md": GOOD_DATA.replace("Git ignores the folder.\n", "Git ignores the folder.\nx\ny\nz\n")})
    errors = repo_checks.data_statement_errors(tmp_path)
    assert errors == ["README.md section '## Data' has 7 lines, above 6. Fix: shorten it"], f"got {errors}"


def test_a_gitignore_that_does_not_ignore_the_store_is_reported(tmp_path):
    write_tree(tmp_path, {**DATA_FILES, ".gitignore": "build/\n"})
    errors = repo_checks.data_statement_errors(tmp_path)
    assert errors == [".gitignore does not ignore .willitharness/, so the README claim that git ignores it is false. Fix: add the pattern"], f"got {errors}"
