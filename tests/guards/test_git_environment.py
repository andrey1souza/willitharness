import os

from git_environment import git_variable_names


HIDING_VARIABLES = ["GIT_CONFIG_GLOBAL", "GIT_CONFIG_NOSYSTEM"]


def test_no_git_variable_reaches_a_test_except_the_two_that_hide_the_git_config():
    found = sorted(git_variable_names(os.environ))
    assert found == HIDING_VARIABLES, f"the session fixture must clear every inherited GIT_ variable and set only {HIDING_VARIABLES}, found {found}"


def test_git_variables_are_found_by_prefix_only():
    environ = {"GIT_DIR": "/real", "GIT_INDEX_FILE": "i", "PATH": "/bin", "MY_GIT_DIR": "x"}
    assert git_variable_names(environ) == ["GIT_DIR", "GIT_INDEX_FILE"], f"got {git_variable_names(environ)}"
