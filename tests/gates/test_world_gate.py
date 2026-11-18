import shutil
from pathlib import Path

from files import plant, write_tree

from cli_runner import run_cli
from willitharness import cli

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_WORLDS = REPO_ROOT / "fixtures" / "worlds"
GOOD_TREE = {"tasks.txt": "stop: pkill\n", "stubs/pkill/output.txt": "killed\n"}


def copy_fixture(tmp_path, name):
    shutil.copytree(FIXTURE_WORLDS / name, tmp_path / name)
    return tmp_path


def test_the_good_fixture_prints_the_valid_line_with_eight_hex_digits(tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(copy_fixture(tmp_path, "good"))
    code, output, errors = run_cli(capsys, ["world", "check", "good"])
    assert code == 0, f"expected exit 0, got {code}; stderr {errors!r}"
    assert output.startswith("world: valid (hash ") and len(output.strip()) == len("world: valid (hash a1b2c3d4)"), f"output {output!r} is not the valid line. Fix: print world: valid (hash <8 hex digits>)"


def test_the_no_stub_fixture_exits_one_naming_pkill(tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(copy_fixture(tmp_path, "no-stub"))
    code, output, errors = run_cli(capsys, ["world", "check", "no-stub"])
    assert code == 1, f"expected exit 1, got {code}"
    assert "task names pkill but the world has no stub or declaration for it" in errors, f"stderr {errors!r}"
    assert "Fix:" in errors and output == "", f"stdout {output!r} stderr {errors!r}"


def test_the_ps_foreign_fixture_exits_one_with_the_path_message(tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(copy_fixture(tmp_path, "ps-foreign"))
    code, output, errors = run_cli(capsys, ["world", "check", "ps-foreign"])
    assert code == 1, f"expected exit 1, got {code}"
    assert "world invalid: stub output refers to a path outside the world" in errors, f"stderr {errors!r}"
    assert "Fix:" in errors and output == "", f"stdout {output!r} stderr {errors!r}"


def test_a_valid_check_stores_the_hash_under_the_working_directory(tmp_path, capsys, monkeypatch):
    write_tree(tmp_path / "w", GOOD_TREE)
    monkeypatch.chdir(tmp_path)
    run_cli(capsys, ["world", "check", "w"])
    record = tmp_path / ".willitharness" / "w" / "world.json"
    assert record.is_file(), f"no record at {record}"
    assert '"validated": true' in record.read_text(), f"record {record.read_text()!r} is not validated. Fix: store the record after the checks pass"


def test_an_invalid_check_stores_nothing(tmp_path, capsys, monkeypatch):
    write_tree(tmp_path / "w", {"tasks.txt": "stop: pkill\n"})
    monkeypatch.chdir(tmp_path)
    code, _, _ = run_cli(capsys, ["world", "check", "w"])
    assert code == 1, f"expected exit 1, got {code}"
    assert not (tmp_path / ".willitharness").exists(), "an invalid world must leave no record"


def test_a_missing_world_directory_exits_one_with_a_fix(tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(tmp_path)
    code, _, errors = run_cli(capsys, ["world", "check", "nowhere"])
    assert code == 1, f"expected exit 1, got {code}"
    assert "nowhere" in errors and "Rule:" in errors and "Fix:" in errors, f"stderr {errors!r}"


def test_a_world_outside_the_working_directory_exits_one(tmp_path, capsys, monkeypatch):
    write_tree(tmp_path / "work" / "w", GOOD_TREE)
    write_tree(tmp_path / "other", GOOD_TREE)
    monkeypatch.chdir(tmp_path / "work")
    code, _, errors = run_cli(capsys, ["world", "check", "../other"])
    assert code == 1, f"expected exit 1, got {code}"
    assert "outside" in errors and "Fix:" in errors, f"stderr {errors!r}"


def test_the_check_never_executes_a_file_from_the_world(tmp_path, capsys, monkeypatch):
    write_tree(tmp_path / "w", GOOD_TREE)
    plant(tmp_path / "w" / "stubs" / "pkill", "run.py", f"open({str(tmp_path / 'proof')!r}, 'w').write('ran')\n")
    monkeypatch.chdir(tmp_path)
    code, _, errors = run_cli(capsys, ["world", "check", "w"])
    assert code == 0, f"expected exit 0, got {code}; stderr {errors!r}"
    assert not (tmp_path / "proof").exists(), "world check must treat world files as data"


def test_an_edit_after_the_check_changes_the_next_hash(tmp_path, capsys, monkeypatch):
    write_tree(tmp_path / "w", GOOD_TREE)
    monkeypatch.chdir(tmp_path)
    _, first, _ = run_cli(capsys, ["world", "check", "w"])
    plant(tmp_path / "w" / "stubs" / "pkill", "output.txt", "edited\n")
    _, second, _ = run_cli(capsys, ["world", "check", "w"])
    assert first != second, f"hash stayed the same after an edit: {first!r}"
