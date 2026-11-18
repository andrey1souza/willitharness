import sys

import pytest

from files import plant
from willitharness.isolation import run_sandboxed, sandbox_profile

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
