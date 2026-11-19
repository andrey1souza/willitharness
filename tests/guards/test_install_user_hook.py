import json
import os

import pytest
from hook_settings import (
    SCRIPT_NAME,
    BACKUP_NAME,
    ORIGINAL,
    BARE,
    expected_after_install,
    group,
    settings_text,
    guard_script,
    seeded,
    command_of,
    invoke,
)

from guards import install_user_hook as installer


def test_install_appends_exactly_one_group(tmp_path):
    target = seeded(tmp_path)
    script = guard_script(tmp_path)
    code = invoke("install", script, [target])
    assert code == 0, f"install must exit 0, got {code}"
    assert target.read_text() == expected_after_install(script), f"got {target.read_text()}"


def test_install_twice_gives_identical_bytes(tmp_path):
    target = seeded(tmp_path)
    script = guard_script(tmp_path)
    invoke("install", script, [target])
    first = target.read_bytes()
    assert invoke("install", script, [target]) == 0, "the second install must exit 0"
    assert target.read_bytes() == first, "the second install must change no byte"


def test_foreign_hooks_stay_byte_equal(tmp_path):
    target = seeded(tmp_path)
    script = guard_script(tmp_path)
    before = json.loads(ORIGINAL)
    invoke("install", script, [target])
    after = json.loads(target.read_text())
    assert after["hooks"]["Stop"] == before["hooks"]["Stop"], "the Stop group must not change"
    assert after["hooks"]["PreToolUse"][:1] == before["hooks"]["PreToolUse"], "the foreign PreToolUse group must not change"
    assert after["theme"] == "dark" and len(after["hooks"]["PreToolUse"]) == 2, f"only one group is added, got {after}"


def test_four_space_indent_is_kept(tmp_path):
    script = guard_script(tmp_path)
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"theme": "dark"}, indent=4) + "\n")
    invoke("install", script, [path])
    assert path.read_text().startswith('{\n    "theme": "dark",\n    "hooks": {\n        "PreToolUse"'), f"got {path.read_text()}"
    invoke("remove", script, [path])
    assert path.read_text() == '{\n    "theme": "dark"\n}\n', f"got {path.read_text()}"


@pytest.mark.parametrize(
    "text, fragment",
    [
        ("{not json", "is not valid JSON"),
        ("[]\n", "holds list, not an object"),
        ('{"hooks":{"PreToolUse":[]}}', "formatting is not plain JSON"),
        ('{\n   "theme": "dark"\n}\n', "formatting is not plain JSON"),
        ('{\n  "hooks": []\n}\n', "hooks is list, not an object"),
        ('{\n  "hooks": {\n    "PreToolUse": {}\n  }\n}\n', "not a list of objects"),
    ],
)
def test_a_bad_settings_file_is_refused_and_untouched(tmp_path, capsys, text, fragment):
    script = guard_script(tmp_path)
    path = tmp_path / "settings.json"
    path.write_text(text)
    code = invoke("install", script, [path])
    assert code == 2 and path.read_text() == text, f"a bad file must be refused unchanged, got exit {code}"
    assert fragment in capsys.readouterr().out, f"the refusal must say {fragment!r}"
    assert not (tmp_path / BACKUP_NAME).exists(), "a refused file gets no backup"


def test_a_missing_settings_file_is_refused(tmp_path, capsys):
    script = guard_script(tmp_path)
    code = invoke("install", script, [tmp_path / "settings.json"])
    assert code == 2, f"a missing file must be refused, got exit {code}"
    printed = capsys.readouterr().out
    assert "does not exist" in printed, f"the refusal must say the file is missing, got {printed!r}"
    assert not (tmp_path / "settings.json").exists(), "the installer must not create the file"


def test_a_group_that_mixes_our_script_with_another_handler_is_refused(tmp_path, capsys):
    script = guard_script(tmp_path)
    mixed = {"hooks": [{"type": "command", "command": "other"}, {"type": "command", "command": f"python3 /old/{SCRIPT_NAME}"}]}
    path = tmp_path / "settings.json"
    path.write_text(settings_text([mixed]))
    before = path.read_bytes()
    assert invoke("install", script, [path]) == 2 and path.read_bytes() == before, f"a mixed group must be refused unchanged, got {path.read_text()}"
    printed = capsys.readouterr().out
    assert "mixes remote_write_guard.py with other handlers" in printed, f"the refusal must name the mix, got {printed!r}"


def test_a_relative_script_is_refused(tmp_path, capsys):
    target = seeded(tmp_path)
    script = guard_script(tmp_path)
    relative = os.path.relpath(script, os.getcwd())
    code = installer.main(["install", "--script", relative, str(target)])
    assert code == 2 and target.read_text() == ORIGINAL, f"a relative script must be refused, got exit {code}"
    printed = capsys.readouterr().out
    assert "is not an absolute path" in printed, f"the refusal must say why, got {printed!r}"


def test_a_missing_script_is_refused(tmp_path, capsys):
    target = seeded(tmp_path)
    code = invoke("install", tmp_path / SCRIPT_NAME, [target])
    assert code == 2 and target.read_text() == ORIGINAL, f"a missing script must be refused, got exit {code}"
    printed = capsys.readouterr().out
    assert "is not an existing file" in printed, f"the refusal must say why, got {printed!r}"


def test_a_script_with_another_name_is_refused(tmp_path, capsys):
    target = seeded(tmp_path)
    other = tmp_path / "other.py"
    other.write_text("x\n")
    assert invoke("install", other, [target]) == 2, "another script name must be refused"
    printed = capsys.readouterr().out
    assert "is not remote_write_guard.py" in printed, f"the refusal must name the expected script, got {printed!r}"


def test_a_script_path_that_needs_quoting_is_refused(tmp_path, capsys):
    target = seeded(tmp_path)
    folder = tmp_path / "with space"
    folder.mkdir()
    spaced = folder / SCRIPT_NAME
    spaced.write_text("x\n")
    assert invoke("install", spaced, [target]) == 2 and target.read_text() == ORIGINAL, f"a path with a space must be refused, got {spaced}"
    printed = capsys.readouterr().out
    assert "needs shell quoting" in printed, f"the refusal must say why, got {printed!r}"


def test_a_script_in_a_linked_worktree_is_refused(tmp_path, capsys):
    target = seeded(tmp_path)
    worktree = tmp_path / "worktree"
    (worktree / "scripts").mkdir(parents=True)
    (worktree / ".git").write_text("gitdir: /elsewhere\n")
    inside_worktree = worktree / "scripts" / SCRIPT_NAME
    inside_worktree.write_text("x\n")
    assert invoke("install", inside_worktree, [target]) == 2, "a linked worktree path must be refused"
    printed = capsys.readouterr().out
    assert "lies in a linked worktree" in printed, f"the refusal must say why, got {printed!r}"


def test_drift_is_repaired_in_place(tmp_path):
    script = guard_script(tmp_path)
    drifted = group(f"python3 /old/place/{SCRIPT_NAME}", "Bash")
    path = tmp_path / "settings.json"
    path.write_text(settings_text([group("first"), drifted, group("last")]))
    invoke("install", script, [path])
    groups = json.loads(path.read_text())["hooks"]["PreToolUse"]
    assert [item["hooks"][0]["command"] for item in groups] == ["first", command_of(script), "last"], f"got {groups}"
    assert groups[1]["matcher"] == "Bash|Write|Edit|MultiEdit|NotebookEdit", f"the matcher is repaired, got {groups[1]}"


def test_duplicate_entries_collapse_to_one(tmp_path):
    script = guard_script(tmp_path)
    path = tmp_path / "settings.json"
    path.write_text(settings_text([group(f"python3 /a/{SCRIPT_NAME}"), group("middle"), group(f"python3 /b/{SCRIPT_NAME}")]))
    invoke("install", script, [path])
    commands = [item["hooks"][0]["command"] for item in json.loads(path.read_text())["hooks"]["PreToolUse"]]
    assert commands == [command_of(script), "middle"], f"got {commands}"
    assert invoke("check", script, [path]) == 0, "the collapsed file passes check"


def test_remove_restores_the_original_bytes(tmp_path):
    target = seeded(tmp_path)
    script = guard_script(tmp_path)
    bare = tmp_path / "bare.json"
    bare.write_text(BARE)
    invoke("install", script, [target, bare])
    assert bare.read_text() != BARE, f"install changed the bare file {bare}"
    assert invoke("remove", script, [target, bare]) == 0, "remove must exit 0"
    assert (target.read_text(), bare.read_text()) == (ORIGINAL, BARE), "remove must restore both files byte for byte"


def test_remove_keeps_foreign_groups_and_other_scripts(tmp_path):
    script = guard_script(tmp_path)
    foreign = group(f"python3 /x/other_guard.py", "Bash")
    path = tmp_path / "settings.json"
    path.write_text(settings_text([foreign, group(f"python3 /old/{SCRIPT_NAME}")]))
    invoke("remove", script, [path])
    assert json.loads(path.read_text())["hooks"]["PreToolUse"] == [foreign], f"got {path.read_text()}"
    assert SCRIPT_NAME not in path.read_text(), f"our entry is gone from {path.read_text()}"


def test_remove_without_our_entry_changes_nothing(tmp_path):
    target = seeded(tmp_path)
    script = guard_script(tmp_path)
    code = invoke("remove", script, [target])
    assert code == 0 and target.read_text() == ORIGINAL, f"remove on a clean file is a no-op, got exit {code}"
    assert not (target.parent / BACKUP_NAME).exists(), "remove creates no backup"
