from pathlib import Path

from files import copy_tree

AUDIT_FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "audit"


def copy_audit_fixture(destination, name):
    assert (AUDIT_FIXTURES / name).is_dir(), f"{name!r} is not an audit fixture under {AUDIT_FIXTURES}. Fix: use a folder name from fixtures/audit."
    copied = copy_tree(AUDIT_FIXTURES / name, destination / name)
    assert copied.is_dir(), f"copy_audit_fixture did not create {destination / name}"
    return copied


def text_of(folder, name):
    assert (folder / name).is_file(), f"{folder / name} is not a file. Fix: name a file of the copy."
    return (folder / name).read_text()


def append_line(folder, name, line):
    assert line.endswith("\n"), f"append_line needs a full line, got {line!r}. Fix: end it with a newline."
    (folder / name).write_text(text_of(folder, name) + line)
    assert text_of(folder, name).endswith(line), f"append_line did not write {line!r} to {folder / name}"
