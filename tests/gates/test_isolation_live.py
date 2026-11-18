import json

import pytest

import isolation_live
from files import plant

MARKER = "isolation-test-marker"
CONFIG_FILE = "CLAUDE.md"
ORIGINAL = "my own rules\n"
EXPENSIVE_RUN = 0.2


def transcript(text, cost):
    return [json.dumps({"type": "result", "subtype": "success", "is_error": False, "result": text, "total_cost_usd": cost})]


def quiet_runner(directory, prompt):
    return transcript("NONE", 0.0)


def leaking_runner(directory, prompt):
    return transcript(MARKER, 0.0)


def expensive_quiet_runner(directory, prompt):
    return transcript("NONE", EXPENSIVE_RUN)


def failing_runner(directory, prompt):
    raise RuntimeError("the agent crashed")


def config_dir(tmp_path):
    return plant(tmp_path / "config", CONFIG_FILE, ORIGINAL)


def reading_runner(folder):
    def runner(directory, prompt):
        planted = MARKER.encode() in (folder / CONFIG_FILE).read_bytes()
        return transcript(MARKER if planted else "NONE", 0.0)

    return runner


def run_check(tmp_path, runners):
    return isolation_live.main(["--config-dir", str(config_dir(tmp_path))], runners, MARKER)


def test_a_marker_absent_when_isolated_and_present_when_not_passes(tmp_path, capsys):
    folder = config_dir(tmp_path)
    code = isolation_live.main(["--config-dir", str(folder)], (quiet_runner, reading_runner(folder)), MARKER)
    output = capsys.readouterr().out
    assert code == isolation_live.EXIT_PASSED, f"expected exit 0, got {code}; output {output!r}"
    assert "marker absent with flags; present without flags" in output, f"unexpected output {output!r}"


def test_a_marker_that_reaches_the_isolated_run_is_not_proven(tmp_path, capsys):
    code = run_check(tmp_path, (leaking_runner, leaking_runner))
    output = capsys.readouterr().out
    assert code == isolation_live.EXIT_NOT_PROVEN, f"expected exit 1, got {code}"
    assert "isolation not proven" in output and "GATE G3.8 PASS" not in output, f"unexpected output {output!r}"


def test_a_control_run_that_never_sees_the_marker_proves_nothing(tmp_path, capsys):
    code = run_check(tmp_path, (quiet_runner, quiet_runner))
    output = capsys.readouterr().out
    assert code == isolation_live.EXIT_NOT_PROVEN, f"expected exit 1, got {code}"
    assert "isolation not proven" in output, f"unexpected output {output!r}"


def test_a_cost_above_the_cap_is_not_proven(tmp_path, capsys):
    code = run_check(tmp_path, (expensive_quiet_runner, leaking_runner))
    output = capsys.readouterr().out
    assert code == isolation_live.EXIT_NOT_PROVEN, f"expected exit 1, got {code}; output {output!r}"


def test_the_users_memory_file_is_restored_after_the_check(tmp_path):
    folder = config_dir(tmp_path)
    isolation_live.main(["--config-dir", str(folder)], (quiet_runner, leaking_runner), MARKER)
    assert (folder / CONFIG_FILE).read_bytes() == ORIGINAL.encode(), "the memory file must hold exactly its original text after the check"


def test_a_memory_file_that_did_not_exist_is_removed_again(tmp_path):
    folder = tmp_path / "config"
    folder.mkdir()
    isolation_live.main(["--config-dir", str(folder)], (quiet_runner, leaking_runner), MARKER)
    assert not (folder / CONFIG_FILE).exists(), "a memory file the check created must be deleted again"


def test_the_memory_file_is_restored_even_when_a_run_crashes(tmp_path):
    folder = config_dir(tmp_path)
    with pytest.raises(RuntimeError):
        isolation_live.main(["--config-dir", str(folder)], (failing_runner, leaking_runner), MARKER)
    assert (folder / CONFIG_FILE).read_bytes() == ORIGINAL.encode(), "a crash must not leave the marker in the memory file"
