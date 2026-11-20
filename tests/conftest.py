import os

import pytest
from git_environment import git_variable_names


@pytest.fixture(autouse=True, scope="session")
def no_inherited_git_environment():
    inherited = {name: os.environ[name] for name in git_variable_names(os.environ)}
    for name in inherited:
        del os.environ[name]
    remaining = git_variable_names(os.environ)
    assert not remaining, f"git variables {remaining} are still set. Rule: a test repository must not see the real repository. Fix: delete every GIT_ variable."
    yield
    os.environ.update(inherited)
