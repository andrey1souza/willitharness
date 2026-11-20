import pytest
from hook_settings import (
    SCRIPT_NAME,
    BACKUP_NAME,
    KEEP_AWAKE_RELEASE,
    MEMORY_COMMAND,
    ORIGINAL,
    BARE,
    group,
    settings_text,
    guard_script,
    seeded,
    command_of,
    invoke,
)

from guards import install_user_hook as installer


def test_a_main_checkout_with_a_git_folder_is_accepted(tmp_path):
    target = seeded(tmp_path)
    checkout = tmp_path / "checkout"
    (checkout / "scripts").mkdir(parents=True)
    (checkout / ".git").mkdir()
    guard = checkout / "scripts" / SCRIPT_NAME
    guard.write_text("x\n")
    assert invoke("install", guard, [target]) == 0, "a .git folder marks the main checkout, which is allowed"
    assert command_of(guard) in target.read_text(), f"the command names {guard}"


def test_the_backup_is_made_once_with_the_original_bytes(tmp_path):
    target = seeded(tmp_path)
    script = guard_script(tmp_path)
    backup = target.parent / BACKUP_NAME
    invoke("install", script, [target])
    assert backup.read_text() == ORIGINAL, "the backup holds the pre-install bytes"
    invoke("remove", script, [target])
    target.write_text(BARE)
    invoke("install", script, [target])
    assert backup.read_text() == ORIGINAL, "a later install must not overwrite the backup"


def test_an_existing_backup_is_never_overwritten(tmp_path):
    target = seeded(tmp_path)
    script = guard_script(tmp_path)
    backup = target.parent / BACKUP_NAME
    backup.write_text("sentinel")
    invoke("install", script, [target])
    assert backup.read_text() == "sentinel", "a present backup stays as it is"
    assert command_of(script) in target.read_text(), f"the install still happens, got {target.read_text()}"


def test_a_noop_install_creates_no_backup(tmp_path):
    target = seeded(tmp_path)
    script = guard_script(tmp_path)
    invoke("install", script, [target])
    (target.parent / BACKUP_NAME).unlink()
    invoke("install", script, [target])
    assert not (target.parent / BACKUP_NAME).exists(), "an install that changes nothing writes no backup"
    assert command_of(script) in target.read_text(), f"the entry is still there, got {target.read_text()}"


def test_check_passes_after_install_and_is_read_only(tmp_path, capsys):
    target = seeded(tmp_path)
    script = guard_script(tmp_path)
    invoke("install", script, [target])
    before = target.read_bytes()
    code = invoke("check", script, [target])
    assert code == 0 and target.read_bytes() == before, f"a good install passes check unchanged, got exit {code}"
    printed = capsys.readouterr().out
    assert "check ok for 1 target(s)" in printed, f"check prints its verdict, got {printed!r}"


def test_check_fails_when_the_entry_is_absent_and_writes_nothing(tmp_path, capsys):
    target = seeded(tmp_path)
    script = guard_script(tmp_path)
    code = invoke("check", script, [target])
    assert code == 1 and target.read_text() == ORIGINAL, f"a missing entry fails check, got exit {code}"
    printed = capsys.readouterr().out
    assert "holds 0 guard entries" in printed, f"check says what is wrong, got {printed!r}"
    assert not (target.parent / BACKUP_NAME).exists(), "check never creates the backup"


def test_check_fails_on_a_drifted_command(tmp_path, capsys):
    script = guard_script(tmp_path)
    path = tmp_path / "settings.json"
    path.write_text(settings_text([group(f"python3 /old/{SCRIPT_NAME}", "Bash|Write|Edit|MultiEdit|NotebookEdit")]))
    assert invoke("check", script, [path]) == 1, "a drifted command fails check"
    printed = capsys.readouterr().out
    assert "differs from the expected command" in printed, f"check names the drift, got {printed!r}"


def test_check_fails_on_a_wrong_matcher(tmp_path, capsys):
    script = guard_script(tmp_path)
    path = tmp_path / "settings.json"
    path.write_text(settings_text([group(command_of(script), "Bash")]))
    assert invoke("check", script, [path]) == 1, "a wrong matcher fails check"
    printed = capsys.readouterr().out
    assert "differs from the expected command" in printed, f"check names the drift, got {printed!r}"


def test_check_fails_on_two_entries(tmp_path, capsys):
    script = guard_script(tmp_path)
    canonical = group(command_of(script), "Bash|Write|Edit|MultiEdit|NotebookEdit")
    path = tmp_path / "settings.json"
    path.write_text(settings_text([canonical, canonical]))
    assert invoke("check", script, [path]) == 1, "two entries fail check"
    printed = capsys.readouterr().out
    assert "holds 2 guard entries" in printed, f"check counts them, got {printed!r}"


def test_check_fails_when_the_script_is_not_executable(tmp_path, capsys):
    target = seeded(tmp_path)
    script = guard_script(tmp_path)
    invoke("install", script, [target])
    script.chmod(0o644)
    assert invoke("check", script, [target]) == 1, "a script without the execute bit fails check"
    printed = capsys.readouterr().out
    assert "is not executable" in printed, f"check says so, got {printed!r}"


def test_check_fails_on_invalid_json(tmp_path, capsys):
    script = guard_script(tmp_path)
    path = tmp_path / "settings.json"
    path.write_text("{")
    assert invoke("check", script, [path]) == 1, "invalid JSON fails check"
    printed = capsys.readouterr().out
    assert "is not valid JSON" in printed, f"check says so, got {printed!r}"


def test_check_fails_when_another_group_differs_from_the_backup(tmp_path, capsys):
    target = seeded(tmp_path)
    script = guard_script(tmp_path)
    invoke("install", script, [target])
    tampered = target.read_text().replace(KEEP_AWAKE_RELEASE, MEMORY_COMMAND)
    target.write_text(tampered)
    assert invoke("check", script, [target]) == 1, "a changed foreign group fails check"
    printed = capsys.readouterr().out
    assert "differ from settings.json.before-willitharness-guard" in printed, f"check names the backup, got {printed!r}"


def test_check_ignores_a_missing_backup(tmp_path):
    target = seeded(tmp_path)
    script = guard_script(tmp_path)
    invoke("install", script, [target])
    (target.parent / BACKUP_NAME).unlink()
    assert invoke("check", script, [target]) == 0, "without a backup there is nothing to compare"
    assert command_of(script) in target.read_text(), f"the entry is there, got {target.read_text()}"


def test_check_covers_every_target(tmp_path, capsys):
    target = seeded(tmp_path)
    script = guard_script(tmp_path)
    clean = tmp_path / "clean.json"
    clean.write_text(BARE)
    invoke("install", script, [target])
    assert invoke("check", script, [target, clean]) == 1, "one failing target fails the run"
    printed = capsys.readouterr().out
    assert "clean.json holds 0 guard entries" in printed, f"the failing target is named, got {printed!r}"


def test_an_invalid_second_target_leaves_the_first_unchanged(tmp_path):
    target = seeded(tmp_path)
    script = guard_script(tmp_path)
    broken = tmp_path / "broken.json"
    broken.write_text("{")
    assert invoke("install", script, [target, broken]) == 2, "an invalid target refuses the whole run"
    assert target.read_text() == ORIGINAL, "the first target must not change"
    assert not (target.parent / BACKUP_NAME).exists(), "the first target gets no backup"


def test_a_failed_write_restores_the_first_target(tmp_path, capsys):
    target = seeded(tmp_path)
    script = guard_script(tmp_path)
    locked_folder = tmp_path / "locked"
    locked_folder.mkdir()
    second = locked_folder / "settings.json"
    second.write_text(BARE)
    locked_folder.chmod(0o500)
    try:
        code = invoke("install", script, [target, second])
    finally:
        locked_folder.chmod(0o700)
    assert code == 2 and target.read_text() == ORIGINAL, f"a failed write must roll the first target back, got exit {code}"
    assert not (target.parent / BACKUP_NAME).exists(), "the rolled back target keeps no new backup"
    printed = capsys.readouterr().out
    assert "every earlier target was restored" in printed, f"the refusal says what happened, got {printed!r}"


def test_the_write_replaces_the_file_and_leaves_no_temp_file(tmp_path):
    target = seeded(tmp_path)
    script = guard_script(tmp_path)
    before = target.stat().st_ino
    invoke("install", script, [target])
    assert target.stat().st_ino != before, f"a temp file renamed over the target gives a new inode, still {before}"
    assert sorted(path.name for path in target.parent.iterdir()) == ["settings.json", BACKUP_NAME], "no temp file may remain"


def test_the_temp_file_lives_in_the_target_folder(tmp_path):
    target = seeded(tmp_path)
    assert installer.temp_directory(target) == target.parent, "a rename is atomic only inside one folder"
    assert installer.temp_directory(target).is_dir(), "the folder exists"


def test_the_file_mode_is_kept(tmp_path):
    target = seeded(tmp_path)
    script = guard_script(tmp_path)
    target.chmod(0o640)
    invoke("install", script, [target])
    assert target.stat().st_mode & 0o777 == 0o640, "the new file keeps the old permissions"
    assert command_of(script) in target.read_text(), f"the entry was written, got {target.read_text()}"


def test_a_symlinked_settings_file_stays_a_link(tmp_path):
    script = guard_script(tmp_path)
    real = tmp_path / "dotfiles" / "settings.json"
    real.parent.mkdir()
    real.write_text(ORIGINAL)
    link = tmp_path / "config" / "settings.json"
    link.parent.mkdir()
    link.symlink_to(real)
    invoke("install", script, [link])
    assert link.is_symlink(), "the link must survive"
    assert command_of(script) in real.read_text(), f"the real file holds the entry, got {real.read_text()}"


def test_the_usage_text_says_where_to_point_the_script():
    text = installer.build_parser().format_help()
    assert "MAIN checkout" in text and "never at a linked worktree" in text, f"got {text}"
    assert "/.claude/settings.json" in text and "/.claude-thoughtworks/settings.json" in text, "the usage names the default targets"


def test_the_command_is_python3_and_the_absolute_path(tmp_path):
    script = guard_script(tmp_path)
    assert installer.guard_command(script) == f"python3 {script}", "the command string is fixed"
    assert installer.canonical_group(installer.guard_command(script))["matcher"] == "Bash|Write|Edit|MultiEdit|NotebookEdit", "the matcher is fixed"


def test_remove_creates_no_backup(tmp_path):
    script = guard_script(tmp_path)
    target = seeded(tmp_path)
    invoke("install", script, [target])
    (target.parent / BACKUP_NAME).unlink()
    assert invoke("remove", script, [target]) == 0, "remove must exit 0"
    assert sorted(path.name for path in target.parent.iterdir()) == ["settings.json"], f"remove writes no backup, got {sorted(target.parent.iterdir())}"


def test_a_failed_write_leaves_no_temp_file_and_the_old_text(tmp_path):
    target = seeded(tmp_path)
    with pytest.raises(UnicodeEncodeError, match="surrogate") as raised:
        installer.atomic_write(target, "\ud800")
    assert target.read_text() == ORIGINAL, f"the old text must stay, got {target.read_text()}"
    assert sorted(path.name for path in target.parent.iterdir()) == ["settings.json"], f"no temp file may remain after {raised.value}"
