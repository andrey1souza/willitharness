import os

import pytest
from git_environment import git_variable_names

HIDE_GLOBAL_GIT_CONFIG = "GIT_CONFIG_GLOBAL"
HIDE_SYSTEM_GIT_CONFIG = "GIT_CONFIG_NOSYSTEM"


@pytest.fixture(autouse=True, scope="session")
def no_inherited_git_environment():
    inherited = {name: os.environ[name] for name in git_variable_names(os.environ)}
    for name in inherited:
        del os.environ[name]
    remaining = git_variable_names(os.environ)
    assert not remaining, f"git variables {remaining} are still set. Rule: a test repository must not see the real repository. Fix: delete every GIT_ variable."
    os.environ[HIDE_GLOBAL_GIT_CONFIG] = os.devnull
    os.environ[HIDE_SYSTEM_GIT_CONFIG] = "1"
    yield
    del os.environ[HIDE_GLOBAL_GIT_CONFIG]
    del os.environ[HIDE_SYSTEM_GIT_CONFIG]
    os.environ.update(inherited)
