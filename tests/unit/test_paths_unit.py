import pytest

from willitharness.paths import PathOutsideRoot, inside


def test_a_relative_path_inside_the_root_resolves_under_it(tmp_path):
    (tmp_path / "plans").mkdir()
    resolved = inside(tmp_path, "plans/a.json")
    assert resolved == tmp_path.resolve() / "plans" / "a.json", f"unexpected path {resolved}"


def test_an_absolute_path_inside_the_root_is_accepted(tmp_path):
    target = tmp_path / "a.json"
    resolved = inside(tmp_path, str(target))
    assert resolved == target.resolve(), f"unexpected path {resolved}"


def test_a_parent_traversal_is_rejected_with_the_fix(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    with pytest.raises(PathOutsideRoot) as raised:
        inside(root, "../other.json")
    assert "outside" in str(raised.value) and "Fix:" in str(raised.value), f"unexpected message {str(raised.value)!r}"


def test_an_absolute_path_outside_the_root_is_rejected(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    with pytest.raises(PathOutsideRoot) as raised:
        inside(root, str(tmp_path / "other.json"))
    assert "outside" in str(raised.value), f"unexpected message {str(raised.value)!r}"


def test_a_symlink_that_leaves_the_root_is_rejected(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (root / "link").symlink_to(outside)
    with pytest.raises(PathOutsideRoot) as raised:
        inside(root, "link/a.json")
    assert "outside" in str(raised.value), f"unexpected message {str(raised.value)!r}"


def test_a_root_that_is_not_a_directory_is_an_error(tmp_path):
    with pytest.raises(AssertionError) as raised:
        inside(tmp_path / "missing", "a.json")
    assert "is not a directory" in str(raised.value), f"unexpected message {str(raised.value)!r}"
