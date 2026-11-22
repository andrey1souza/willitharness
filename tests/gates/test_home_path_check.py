import repo_checks
from files import write_tree

HOME_PREFIX = "/" + "Users" + "/"


def test_a_home_path_is_reported_with_file_and_line(tmp_path):
    write_tree(tmp_path, {"docs/note.txt": f"fine\npath {HOME_PREFIX}someone/work\n", "src/ok.txt": "clean\n"})
    errors = repo_checks.home_path_errors(tmp_path)
    assert len(errors) == 1, f"expected one leak, got {errors}"
    assert "note.txt:2" in errors[0], f"the error must name file and line, got {errors[0]!r}"
    assert "Fix:" in errors[0], f"the error must end with a fix, got {errors[0]!r}"


def test_a_clean_tree_and_missing_folders_have_no_home_path_errors(tmp_path):
    write_tree(tmp_path, {"docs/note.txt": "relative/path\n"})
    assert repo_checks.home_path_errors(tmp_path) == [], "a clean tree with missing folders must pass"
    assert "no-home-paths" in repo_checks.CHECKS, "the check is registered"
