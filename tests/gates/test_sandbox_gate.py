import sys

import pytest

from files import plant
from willitharness.isolation import run_sandboxed, sandbox_profile
from willitharness.real_runner import writable_extras
from willitharness.stubs import calls_path, stub_folder

pytestmark = pytest.mark.skipif(sys.platform != "darwin", reason="the sandbox profile uses macOS sandbox-exec")
SECRET_TEXT = "private key material"


def build(tmp_path):
    world = tmp_path / "world"
    outside = tmp_path / "outside"
    home = tmp_path / "home"
    for folder in (world, outside, home / ".ssh"):
        folder.mkdir(parents=True)
    plant(home / ".ssh", "id_test", SECRET_TEXT)
    return world, outside, home, sandbox_profile(world, home, ())


def test_a_write_inside_the_world_is_allowed(tmp_path):
    world, _, _, profile = build(tmp_path)
    written = run_sandboxed(["/bin/sh", "-c", "echo ok > inside.txt"], profile, world)
    read_back = run_sandboxed(["/bin/cat", "inside.txt"], profile, world)
    assert written.returncode == 0 and read_back.stdout.strip() == "ok", f"write failed: {written.stderr!r}, read back {read_back.stdout!r}"


def test_a_write_outside_the_world_is_denied(tmp_path):
    world, outside, _, profile = build(tmp_path)
    completed = run_sandboxed(["/bin/sh", "-c", f"echo no > {outside}/escaped.txt"], profile, world)
    assert completed.returncode != 0, f"a write outside the world must fail, got exit {completed.returncode}"
    assert not (outside / "escaped.txt").exists(), "the file outside the world was created despite the sandbox"


def test_a_secret_folder_under_home_cannot_be_read(tmp_path):
    world, _, home, profile = build(tmp_path)
    completed = run_sandboxed(["/bin/cat", str(home / ".ssh" / "id_test")], profile, world)
    assert completed.returncode != 0 and SECRET_TEXT not in completed.stdout, f"the secret was readable: {completed.stdout!r}"


def test_the_run_profile_denies_writes_into_the_wrapper_folder_and_allows_only_the_calls_log(tmp_path):
    run_root = tmp_path / "run"
    home = tmp_path / "home"
    (tmp_path / "run" / "work").mkdir(parents=True)
    (tmp_path / "run" / "bin").mkdir()
    (tmp_path / "run" / "tmp").mkdir()
    home.mkdir()
    profile = sandbox_profile(run_root / "work", home, writable_extras(run_root, {}, home))
    wrapper = run_sandboxed(["/bin/sh", "-c", f"echo x > {stub_folder(run_root)}/cp"], profile, run_root / "work")
    beside = run_sandboxed(["/bin/sh", "-c", f"echo x > {run_root}/planted"], profile, run_root / "work")
    log = run_sandboxed(["/bin/sh", "-c", f"echo x >> {calls_path(run_root)}"], profile, run_root / "work")
    assert wrapper.returncode != 0 and not (tmp_path / "run" / "bin" / "cp").exists(), f"a write into the wrapper folder must fail, got {wrapper}"
    assert beside.returncode != 0 and not (tmp_path / "run" / "planted").exists(), f"a write beside the calls log must fail, got {beside}"
    assert log.returncode == 0 and (tmp_path / "run" / "calls.log").read_text() == "x\n", f"the calls log must stay writable, got {log}"
