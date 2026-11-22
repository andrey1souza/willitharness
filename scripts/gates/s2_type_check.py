import inspect
import sys

from willitharness.decision import decide

EXIT_PASSED = 0
EXIT_FAILED = 1
EXPECTED_PARAMETERS = ("reach", "effect", "guard")
PARAMETER_SEPARATOR = ", "


def parameters_of(function):
    assert callable(function), f"parameters_of needs a function, got {function!r}. Fix: pass decision.decide."
    result = tuple(inspect.signature(function).parameters)
    assert all(isinstance(name, str) for name in result), f"parameters_of built a non-text name from {function!r}"
    return result


def verdict_line(parameters):
    assert isinstance(parameters, tuple), f"verdict_line needs a tuple of names, got {parameters!r}. Fix: build it with parameters_of."
    expected = PARAMETER_SEPARATOR.join(EXPECTED_PARAMETERS)
    if parameters == EXPECTED_PARAMETERS:
        result = f"decision parameters are exactly: {expected}"
    else:
        found = PARAMETER_SEPARATOR.join(parameters)
        result = (
            f"decision parameters are {found}, not exactly: {expected}. "
            "Rule: S2, the decision takes no side-effect input. Fix: remove the extra parameter from decide."
        )
    assert expected in result, f"verdict_line lost the expected names {expected!r} in {result!r}"
    return result


def exit_code_of(function):
    assert callable(function), f"exit_code_of needs a function, got {function!r}. Fix: pass decision.decide."
    parameters = parameters_of(function)
    line = verdict_line(parameters)
    passed = parameters == EXPECTED_PARAMETERS
    print(line)
    assert passed == line.startswith("decision parameters are exactly"), f"the verdict line disagrees with the check: {line!r}"
    result = EXIT_PASSED if passed else EXIT_FAILED
    assert result in (EXIT_PASSED, EXIT_FAILED), f"exit_code_of built the unknown code {result!r}"
    return result


def main():
    assert decide is not None, "main needs decision.decide. Fix: restore the import."
    result = exit_code_of(decide)
    assert result in (EXIT_PASSED, EXIT_FAILED), f"main built the unknown code {result!r}"
    return result


if __name__ == "__main__":
    sys.exit(main())
