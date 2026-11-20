import os

from git_environment import git_variable_names


def test_no_git_variable_reaches_a_test():
    assert git_variable_names(os.environ) == [], f"the session fixture must clear GIT_ variables, found {git_variable_names(os.environ)}"


def test_git_variables_are_found_by_prefix_only():
    environ = {"GIT_DIR": "/real", "GIT_INDEX_FILE": "i", "PATH": "/bin", "MY_GIT_DIR": "x"}
    assert git_variable_names(environ) == ["GIT_DIR", "GIT_INDEX_FILE"], f"got {git_variable_names(environ)}"
