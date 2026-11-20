INHERITED_PREFIX = "GIT_"


def git_variable_names(environ):
    assert hasattr(environ, "keys"), f"git_variable_names needs a mapping of variables, got {type(environ).__name__}. Fix: pass os.environ."
    names = [name for name in environ if name.startswith(INHERITED_PREFIX)]
    assert all(name in environ for name in names), f"a listed name is missing from the environment: {names}"
    return names
