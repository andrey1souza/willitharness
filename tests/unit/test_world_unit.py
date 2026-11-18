import json
import re

import pytest
from files import plant, write_tree

from willitharness.world import (
    WorldError,
    check_commands,
    check_stub_paths,
    declared_real,
    path_tokens,
    stored_hash,
    store_path,
    store_validation,
    stub_outputs,
    task_commands,
    validate_world,
    world_changed,
    world_hash,
)

PKILL_TREE = {"tasks.txt": "stop: pkill\n", "stubs/pkill/output.txt": "killed\n"}


def test_the_hash_of_a_known_tree_is_pinned(tmp_path):
    write_tree(tmp_path, {"a.txt": "one", "stubs/ps/output.txt": "two"})
    assert world_hash(tmp_path) == "91a34192", f"hash is {world_hash(tmp_path)!r}"


def test_the_hash_is_eight_hex_digits(tmp_path):
    write_tree(tmp_path, PKILL_TREE)
    assert re.fullmatch("[0-9a-f]{8}", world_hash(tmp_path)), f"hash is {world_hash(tmp_path)!r}"


def test_the_hash_changes_when_a_file_changes(tmp_path):
    write_tree(tmp_path, PKILL_TREE)
    before = world_hash(tmp_path)
    plant(tmp_path / "stubs" / "pkill", "output.txt", "killed twice\n")
    assert world_hash(tmp_path) != before, f"hash stayed {before!r} after an edit"


def test_the_hash_changes_when_a_file_is_renamed(tmp_path):
    write_tree(tmp_path, {"one.txt": "same"})
    before = world_hash(tmp_path)
    (tmp_path / "one.txt").rename(tmp_path / "two.txt")
    assert world_hash(tmp_path) != before, f"hash stayed {before!r} after a rename"


def test_the_hash_changes_when_a_file_is_added(tmp_path):
    write_tree(tmp_path, PKILL_TREE)
    before = world_hash(tmp_path)
    plant(tmp_path, "extra.txt", "")
    assert world_hash(tmp_path) != before, f"hash stayed {before!r} after adding a file"


def test_the_hash_is_equal_for_equal_trees_in_two_places(tmp_path):
    write_tree(tmp_path / "left", PKILL_TREE)
    write_tree(tmp_path / "right", PKILL_TREE)
    assert world_hash(tmp_path / "left") == world_hash(tmp_path / "right"), "equal trees must hash equal"


def test_declared_real_reads_one_command_per_line(tmp_path):
    plant(tmp_path, "real.txt", "git\n\n  ls  \n")
    assert declared_real(tmp_path) == frozenset({"git", "ls"}), f"got {declared_real(tmp_path)!r}"


def test_declared_real_is_empty_without_a_file(tmp_path):
    assert declared_real(tmp_path) == frozenset(), f"got {declared_real(tmp_path)!r}"


def test_stub_outputs_maps_each_command_to_its_text(tmp_path):
    write_tree(tmp_path, {"stubs/ps/output.txt": "p1", "stubs/rm/output.txt": "r1", "stubs/rm/other.txt": "ignored"})
    assert stub_outputs(tmp_path) == {"ps": "p1", "rm": "r1"}, f"got {stub_outputs(tmp_path)!r}"


def test_task_commands_splits_tasks_and_commands(tmp_path):
    plant(tmp_path, "tasks.txt", "stop: pkill\ncheck: git ps\n")
    assert task_commands(tmp_path) == {"stop": ("pkill",), "check": ("git", "ps")}, f"got {task_commands(tmp_path)!r}"


def test_a_task_line_without_a_separator_is_refused_with_the_fix(tmp_path):
    plant(tmp_path, "tasks.txt", "pkill\n")
    with pytest.raises(WorldError) as raised:
        task_commands(tmp_path)
    assert "'pkill'" in str(raised.value) and "Rule:" in str(raised.value) and "Fix:" in str(raised.value), f"message {str(raised.value)!r}"


def test_W1_a_command_with_a_stub_passes(tmp_path):
    write_tree(tmp_path, PKILL_TREE)
    assert check_commands(tmp_path) is None, f"a stubbed command must pass W1 in {tmp_path}"


def test_W1_a_command_declared_real_passes(tmp_path):
    write_tree(tmp_path, {"tasks.txt": "status: git\n", "real.txt": "git\n"})
    assert check_commands(tmp_path) is None, f"a command declared real must pass W1 in {tmp_path}"


def test_W1_a_command_with_neither_fails_with_name_rule_and_fix(tmp_path):
    write_tree(tmp_path, {"tasks.txt": "stop: pkill\n", "stubs/ps/output.txt": "x"})
    with pytest.raises(WorldError) as raised:
        check_commands(tmp_path)
    message = str(raised.value)
    assert message.startswith("task names pkill but the world has no stub or declaration for it."), f"W1 text is missing, message is {message!r}. Fix: name the command first"
    assert "Rule: W1" in message and message.endswith("Fix: add stubs/pkill/output.txt or add pkill to real.txt."), f"W1 rule or fix is missing, message is {message!r}. Fix: end with the fix"


def test_the_second_unknown_command_of_a_task_is_named(tmp_path):
    write_tree(tmp_path, {"tasks.txt": "stop: ps pkill\n", "stubs/ps/output.txt": "x"})
    with pytest.raises(WorldError) as raised:
        check_commands(tmp_path)
    assert "task names pkill but" in str(raised.value), f"message {str(raised.value)!r}"


def test_path_tokens_keeps_absolute_and_parent_paths_only(tmp_path):
    tokens = path_tokens("12 node /usr/bin/x src/a.js ../up/b.js a..b")
    assert tokens == ["/usr/bin/x", "../up/b.js"], f"expected only the absolute and parent paths, got {tokens!r}. Fix: keep plain names out"


def test_W2_stub_output_inside_the_world_passes(tmp_path):
    root = tmp_path / "world"
    write_tree(root, {"stubs/ps/output.txt": f"1 node {root}/src/a.js\n2 node src/b.js\n"})
    assert check_stub_paths(root) is None, f"paths inside {root} must pass W2"


def test_W2_an_absolute_path_outside_the_world_fails(tmp_path):
    write_tree(tmp_path, {"stubs/ps/output.txt": "999991 node /usr/local/bin/other-project/vitest\n"})
    with pytest.raises(WorldError) as raised:
        check_stub_paths(tmp_path)
    message = str(raised.value)
    assert message.startswith("world invalid: stub output refers to a path outside the world."), f"W2 text is missing, message is {message!r}. Fix: lead with the world invalid line"
    assert "Stub ps prints /usr/local/bin/other-project/vitest" in message, f"stub name or path is missing, message is {message!r}. Fix: name the stub and the path"
    assert "Rule: W2" in message and "Fix: list only paths under the world root" in message, f"W2 rule or fix is missing, message is {message!r}. Fix: state the rule and end with the fix"


def test_W2_a_parent_traversal_out_of_the_world_fails(tmp_path):
    write_tree(tmp_path / "world", {"stubs/ls/output.txt": "../secret.txt\n"})
    with pytest.raises(WorldError) as raised:
        check_stub_paths(tmp_path / "world")
    assert "Stub ls prints ../secret.txt" in str(raised.value), f"message {str(raised.value)!r}"


def test_validate_world_returns_the_hash_of_a_good_world(tmp_path):
    write_tree(tmp_path, PKILL_TREE)
    assert validate_world(tmp_path) == world_hash(tmp_path), "the validated hash must be the world hash"


def test_validate_world_fails_w1_before_it_returns(tmp_path):
    write_tree(tmp_path, {"tasks.txt": "stop: pkill\n"})
    with pytest.raises(WorldError) as raised:
        validate_world(tmp_path)
    assert "Rule: W1" in str(raised.value), f"expected W1 to stop validation, got {str(raised.value)!r}"


def test_validate_world_fails_w2_before_it_returns(tmp_path):
    write_tree(tmp_path, {"tasks.txt": "list: ps\n", "stubs/ps/output.txt": "/etc/passwd\n"})
    with pytest.raises(WorldError) as raised:
        validate_world(tmp_path)
    assert "Rule: W2" in str(raised.value), f"expected W2 to stop validation, got {str(raised.value)!r}"


def test_store_path_sits_under_the_root_by_world_name(tmp_path):
    expected = tmp_path.resolve() / ".willitharness" / "w1" / "world.json"
    assert store_path(tmp_path, tmp_path / "w1") == expected, f"got {store_path(tmp_path, tmp_path / 'w1')}, expected {expected}"


def test_store_validation_writes_the_hash_record(tmp_path):
    store_validation(tmp_path, tmp_path / "w", "a1b2c3d4")
    record = tmp_path / ".willitharness" / "w" / "world.json"
    assert json.loads(record.read_text()) == {"hash": "a1b2c3d4", "validated": True}, f"record {record.read_text()!r} must hold the hash and validated true. Fix: write both keys"


def test_stored_hash_is_none_without_a_record(tmp_path):
    assert stored_hash(tmp_path, tmp_path / "w") is None, f"got {stored_hash(tmp_path, tmp_path / 'w')!r} with no record under {tmp_path}"


def test_stored_hash_is_none_when_the_record_is_not_validated(tmp_path):
    plant(tmp_path / ".willitharness" / "w", "world.json", json.dumps({"hash": "a1b2c3d4", "validated": False}))
    assert stored_hash(tmp_path, tmp_path / "w") is None, f"got {stored_hash(tmp_path, tmp_path / 'w')!r} for an unvalidated record"


def test_stored_hash_returns_what_was_stored(tmp_path):
    store_validation(tmp_path, tmp_path / "w", "deadbeef")
    assert stored_hash(tmp_path, tmp_path / "w") == "deadbeef", f"got {stored_hash(tmp_path, tmp_path / 'w')!r}"


def test_W3_an_unchanged_world_is_not_changed(tmp_path):
    write_tree(tmp_path / "w", PKILL_TREE)
    store_validation(tmp_path, tmp_path / "w", validate_world(tmp_path / "w"))
    assert world_changed(tmp_path, tmp_path / "w") is False, f"no edit was made under {tmp_path / 'w'}"


def test_W3_an_edited_world_is_changed(tmp_path):
    write_tree(tmp_path / "w", PKILL_TREE)
    store_validation(tmp_path, tmp_path / "w", validate_world(tmp_path / "w"))
    plant(tmp_path / "w" / "stubs" / "pkill", "output.txt", "other\n")
    assert world_changed(tmp_path, tmp_path / "w") is True, f"a stub edit under {tmp_path / 'w'} must change the world"


def test_W3_a_world_never_validated_is_not_reported_as_changed(tmp_path):
    write_tree(tmp_path / "w", PKILL_TREE)
    assert world_changed(tmp_path, tmp_path / "w") is False, f"no record under {tmp_path} means not validated, not changed"
