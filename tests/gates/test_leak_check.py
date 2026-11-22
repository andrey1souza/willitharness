import leak_check

HOME_PREFIX = "/" + "Users" + "/"
LINUX_PREFIX = "/" + "home" + "/"


def folder_with(tmp_path, name, text):
    folder = tmp_path / name
    folder.mkdir()
    (folder / "note.txt").write_text(text)
    return folder


def test_a_home_directory_path_exits_1_and_reports_one(tmp_path, capsys):
    folder = folder_with(tmp_path, "dirty", f"path={HOME_PREFIX}someone/work\n")
    code = leak_check.main([str(folder)])
    output = capsys.readouterr().out
    assert code == leak_check.EXIT_LEAK, f"a home path must fail, got code {code!r}"
    assert "leak-check: found 1" in output, f"summary missing from {output!r}"
    assert "note.txt:1" in output, f"location missing from {output!r}"


def test_a_linux_home_path_is_found(tmp_path):
    folder = folder_with(tmp_path, "linux", f"{LINUX_PREFIX}someone/work\n")
    assert leak_check.main([str(folder)]) == leak_check.EXIT_LEAK, "a linux home path must fail"


def test_clean_folders_print_clean_and_exit_0(tmp_path, capsys):
    first = folder_with(tmp_path, "first", "nothing here\n")
    second = folder_with(tmp_path, "second", "relative/path only\n")
    code = leak_check.main([str(first), str(second)])
    output = capsys.readouterr().out
    assert code == leak_check.EXIT_CLEAN, f"clean folders must pass, got code {code!r}"
    assert output.strip() == leak_check.SUMMARY_CLEAN, f"expected the clean line, got {output!r}"


def test_a_leak_in_the_second_folder_is_found(tmp_path):
    first = folder_with(tmp_path, "first", "nothing here\n")
    second = folder_with(tmp_path, "second", f"{HOME_PREFIX}someone/x\n")
    assert leak_check.main([str(first), str(second)]) == leak_check.EXIT_LEAK, "every folder must be scanned"


def test_binary_files_are_skipped(tmp_path):
    folder = tmp_path / "binary"
    folder.mkdir()
    (folder / "blob.bin").write_bytes(b"\xff\xfe\x00" + HOME_PREFIX.encode() + b"someone/\n")
    assert leak_check.main([str(folder)]) == leak_check.EXIT_CLEAN, "undecodable files are not text"


def test_no_folder_is_a_usage_error(capsys):
    code = leak_check.main([])
    assert code == leak_check.EXIT_USAGE, f"no folders must be a usage error, got {code!r}"
    error = capsys.readouterr().err
    assert "Fix:" in error, f"the usage message must end with a fix, got {error!r}"


def test_the_summary_counts_every_leak(tmp_path, capsys):
    folder = folder_with(tmp_path, "many", f"{HOME_PREFIX}a/x\nclean\n{HOME_PREFIX}b/y\n")
    leak_check.main([str(folder)])
    output = capsys.readouterr().out
    assert "leak-check: found 2" in output, f"two leaking lines must be counted as two, got {output!r}"
