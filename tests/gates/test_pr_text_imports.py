import pytest

import repo_checks
from files import write_tree


@pytest.mark.parametrize("statement", ["import status", "import status as gates", "from status import gate_rows", "from status.inner import x"])
def test_each_import_form_of_a_removable_site_module_is_found(statement):
    found = repo_checks.imported_modules(statement + "\n")
    assert "status" in found, f"{statement!r} must be found, got {found}. Fix: read both Import and ImportFrom nodes"


def test_other_imports_are_not_removable_site_modules():
    found = repo_checks.imported_modules("import json\nfrom brand_gates import PERCENT\nfrom guards import private_names\n")
    assert found == {"json", "brand_gates", "guards"}, f"top-level names only, got {found}"
    assert not found & set(repo_checks.REMOVABLE_SITE_MODULES), f"none of {found} may be removable"


def test_a_pr_text_that_imports_status_fails_with_rule_and_fix(tmp_path):
    write_tree(tmp_path, {"scripts/guards/pr_text.py": "import status\n"})
    errors = repo_checks.pr_text_import_errors(tmp_path)
    assert len(errors) == 1 and "status" in errors[0], f"the import must be named, got {errors}"
    assert "Rule:" in errors[0] and "Fix:" in errors[0], f"the message needs Rule and Fix, got {errors[0]!r}"


def test_a_self_contained_pr_text_passes(tmp_path):
    write_tree(tmp_path, {"scripts/guards/pr_text.py": "import json\nfrom brand_gates import PERCENT\n"})
    errors = repo_checks.pr_text_import_errors(tmp_path)
    assert errors == [], f"a file without status imports must pass, got {errors}"


def test_the_real_pr_text_is_self_contained_and_the_check_is_registered():
    errors = repo_checks.pr_text_import_errors(repo_checks.REPO_ROOT)
    assert errors == [], f"pr_text.py must not import status, got {errors}"
    assert repo_checks.CHECKS["pr-text-self-contained"] is repo_checks.pr_text_import_errors, "the check runs in make repo"
