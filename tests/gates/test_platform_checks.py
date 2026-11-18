import repo_checks
from files import write_tree


SKIPPING_TEST = 'import sys\nimport pytest\n\npytestmark = pytest.mark.skipif(sys.platform != "darwin", reason="x")\n'
PORTABLE_TEST = "def test_x():\n    assert True\n"


def platform_tree(tmp_path, test_text):
    write_tree(tmp_path, {"tests/test_a.py": test_text})
    return {"demo": (("tests",), ())}


def test_a_darwin_skipping_test_without_the_declaration_is_reported(tmp_path):
    modules = platform_tree(tmp_path, SKIPPING_TEST)
    errors = repo_checks.platform_errors(tmp_path, modules, {"demo": None})
    assert len(errors) == 1 and errors[0].startswith("demo: a test skips off darwin"), f"got {errors}"


def test_a_declaration_without_a_skipping_test_is_reported(tmp_path):
    modules = platform_tree(tmp_path, PORTABLE_TEST)
    errors = repo_checks.platform_errors(tmp_path, modules, {"demo": "darwin"})
    assert len(errors) == 1 and "no test in TESTS skips off darwin" in errors[0], f"got {errors}"


def test_matching_declarations_have_no_platform_errors(tmp_path):
    modules = platform_tree(tmp_path, SKIPPING_TEST)
    assert repo_checks.platform_errors(tmp_path, modules, {"demo": "darwin"}) == [], "a declared darwin module with a skipping test must pass"
    write_tree(tmp_path, {"tests/test_a.py": PORTABLE_TEST})
    assert repo_checks.platform_errors(tmp_path, modules, {"demo": None}) == [], "a portable module with no declaration must pass"


def test_the_platform_check_is_registered():
    assert "mutant-platforms" in repo_checks.CHECKS, f"the platform check must run with the others, got {sorted(repo_checks.CHECKS)}"
    assert repo_checks.CHECKS["mutant-platforms"] is repo_checks.registered_platform_errors, "the registered check must be the table-backed one"
