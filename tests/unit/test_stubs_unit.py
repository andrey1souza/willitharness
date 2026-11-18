import subprocess
from pathlib import Path

import pytest
from files import write_tree

from willitharness.stubs import BIN_NAME, CALLS_LOG, copy_without_reserved, wrapper_text, write_stub_wrappers


def run_wrapper(work, command, arguments):
    return subprocess.run([str(work / BIN_NAME / command), *arguments], capture_output=True, text=True, cwd=work)


def test_the_wrapper_text_is_pinned():
    expected = (
        "#!/bin/sh\n"
        "{ printf '%s' pkill; for argument in \"$@\"; do printf ' %s' \"$argument\"; done; printf '\\n'; } >> /w/calls.log\n"
        "printf '%s' 'killed 1'\n"
        "exit 0\n"
    )
    assert wrapper_text("pkill", "killed 1", Path("/w") / CALLS_LOG) == expected, "the wrapper text changed. Rule: the wrapper logs arguments, prints the output and exits 0"


def test_a_wrapper_logs_arguments_with_spaces_prints_the_output_and_exits_zero(tmp_path):
    write_tree(tmp_path / "world", {"stubs/ps/output.txt": "4242 node vitest\n"})
    work = tmp_path / "work"
    work.mkdir()
    write_stub_wrappers(tmp_path / "world", work)
    done = run_wrapper(work, "ps", ["-ef", "a b"])
    assert (done.returncode, done.stdout) == (0, "4242 node vitest\n"), f"the wrapper must print the canned output and exit 0, got {done}"
    assert (work / CALLS_LOG).read_text() == "ps -ef a b\n", f"the log must hold the command and its arguments, got {(work / CALLS_LOG).read_text()!r}"


def test_an_output_with_quotes_and_dollar_signs_is_printed_literally(tmp_path):
    text = "it's $HOME `date` \"x\"\n"
    write_tree(tmp_path / "world", {"stubs/ps/output.txt": text})
    work = tmp_path / "work"
    work.mkdir()
    write_stub_wrappers(tmp_path / "world", work)
    assert run_wrapper(work, "ps", []).stdout == text, "the canned output must be data, never shell code"


def test_a_hostile_argument_is_logged_and_never_run(tmp_path):
    write_tree(tmp_path / "world", {"stubs/ps/output.txt": "x"})
    work = tmp_path / "work"
    work.mkdir()
    write_stub_wrappers(tmp_path / "world", work)
    run_wrapper(work, "ps", ["$(touch proof)"])
    assert not (work / "proof").exists() and (work / CALLS_LOG).read_text() == "ps $(touch proof)\n", "an argument is logged as text, never run"


def test_the_copy_leaves_out_the_reserved_names_at_the_top_only(tmp_path):
    write_tree(tmp_path / "src", {"bin/evil": "x", "calls.log": "planted", "keep.txt": "k", "deep/bin/ok": "o"})
    copy_without_reserved(tmp_path / "src", tmp_path / "dst")
    kept = sorted(path.relative_to(tmp_path / "dst").as_posix() for path in (tmp_path / "dst").rglob("*") if path.is_file())
    assert kept == ["deep/bin/ok", "keep.txt"], f"only the top-level bin and calls.log are reserved, got {kept}"


def test_a_command_name_with_a_slash_is_refused():
    with pytest.raises(AssertionError) as raised:
        wrapper_text("a/b", "x", Path("/w") / CALLS_LOG)
    assert "plain command name" in str(raised.value), f"unexpected message {str(raised.value)!r}"
