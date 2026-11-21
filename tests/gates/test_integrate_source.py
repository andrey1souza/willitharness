import pytest

import repo_checks
from files import write_tree

RULE_TEXT = 'raise Refused(f"do not run git reset --hard or git push or git branch -D")\n'
SAFE_SOURCE = 'run_checked(repo, ["git", "branch", "-d", name])\ngit_lines(repo, ["merge", "--ff-only", "origin/main"])\n' + RULE_TEXT


@pytest.mark.parametrize("argument", ["-D", "-f", "-fd", "-df", "--force", "--force-with-lease", "--hard", "push", "update-ref"])
def test_each_forbidden_argument_is_found_in_a_run_checked_list(argument):
    found = repo_checks.forbidden_git_arguments(f'run_checked(repo, ["git", "x", "{argument}"])\n')
    assert found == [(1, argument)], f"{argument!r} must be found in the list, got {found}; Fix: add it to FORBIDDEN_ARGUMENTS or FORCE_FLAG"


@pytest.mark.parametrize("argument", ["-D", "-f", "--hard", "push", "update-ref"])
def test_each_forbidden_argument_is_found_in_a_git_lines_tuple(argument):
    found = repo_checks.forbidden_git_arguments(f'git_lines(repo, ("x", "{argument}"))\n')
    assert found == [(1, argument)], f"{argument!r} must be found in a tuple, got {found}"


def test_the_two_word_forms_are_found_as_separate_elements():
    found = repo_checks.forbidden_git_arguments('run_checked(repo, ["git", "reset", "--hard"])\nrun_checked(repo, ["git", "clean", "-f"])\n')
    assert [argument for _, argument in found] == ["--hard", "-f"], f"reset --hard and clean -f must be found, got {found}"


def test_safe_arguments_and_rule_text_are_not_found():
    found = repo_checks.forbidden_git_arguments(SAFE_SOURCE)
    assert found == [], f"-d, --ff-only and message text must pass, got {found}"
    assert repo_checks.forbidden_git_arguments('other(repo, ["git", "push"])\n') == [], "only the git helpers are scanned"


def test_the_check_names_the_file_line_and_argument(tmp_path):
    write_tree(tmp_path, {"scripts/guards/integrate.py": 'x = 1\nrun_checked(repo, ["git", "push", "origin"])\n'})
    errors = repo_checks.integrate_source_errors(tmp_path)
    assert len(errors) == 1 and "integrate.py:2" in errors[0] and "'push'" in errors[0], f"got {errors}"
    assert "Rule:" in errors[0] and "Fix:" in errors[0], f"the message needs Rule and Fix, got {errors[0]!r}"


def test_a_safe_file_has_no_errors(tmp_path):
    write_tree(tmp_path, {"scripts/guards/integrate.py": SAFE_SOURCE})
    errors = repo_checks.integrate_source_errors(tmp_path)
    assert errors == [], f"a safe file must pass, got {errors}"


def test_the_real_integrate_script_is_clean_and_the_check_is_registered():
    errors = repo_checks.integrate_source_errors(repo_checks.REPO_ROOT)
    assert errors == [], f"integrate.py must never force, got {errors}"
    assert repo_checks.CHECKS["integrate-source-never-forces"] is repo_checks.integrate_source_errors, "the check runs in make repo"
