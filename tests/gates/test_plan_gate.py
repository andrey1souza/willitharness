from pathlib import Path

from willitharness import cli

REPO_ROOT = Path(__file__).resolve().parents[2]
GOOD_PLAN = "fixtures/plans/good.json"
BAD_PLAN = "fixtures/plans/bad-noise-pair.json"
BAD_PLAN_MESSAGE = "noise pair must repeat the LOO arm C; B2 repeats B"


def run_cli(capsys, arguments):
    code = cli.main(arguments)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def test_a_good_plan_passes_the_check(capsys, monkeypatch):
    monkeypatch.chdir(REPO_ROOT)
    code, output, errors = run_cli(capsys, ["plan", "check", GOOD_PLAN])
    assert code == cli.EXIT_OK, f"expected exit {cli.EXIT_OK}, got {code}; stderr {errors!r}"
    assert output.startswith("plan ok: pilot-no-pkill"), f"unexpected output {output!r}"


def test_G1_8_the_bad_noise_pair_plan_exits_one_with_the_named_arms(capsys, monkeypatch):
    monkeypatch.chdir(REPO_ROOT)
    code, output, errors = run_cli(capsys, ["plan", "check", BAD_PLAN])
    assert code == cli.EXIT_DOMAIN_FAILURE, f"expected exit {cli.EXIT_DOMAIN_FAILURE}, got {code}"
    assert BAD_PLAN_MESSAGE in errors, f"stderr must hold {BAD_PLAN_MESSAGE!r}, got {errors!r}"


def test_a_missing_plan_file_exits_one_with_a_fix(capsys, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    code, output, errors = run_cli(capsys, ["plan", "check", "nothing.json"])
    assert code == cli.EXIT_DOMAIN_FAILURE, f"expected exit {cli.EXIT_DOMAIN_FAILURE}, got {code}"
    assert "Fix:" in errors, f"stderr must end with a fix, got {errors!r}"


def test_a_plan_that_is_not_json_exits_one(capsys, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "broken.json").write_text("{not json")
    code, output, errors = run_cli(capsys, ["plan", "check", "broken.json"])
    assert code == cli.EXIT_DOMAIN_FAILURE, f"expected exit {cli.EXIT_DOMAIN_FAILURE}, got {code}"
    assert "not valid JSON" in errors, f"unexpected stderr {errors!r}"


def test_an_unknown_command_exits_two_with_the_usage(capsys):
    code, output, errors = run_cli(capsys, ["banana"])
    assert code == cli.EXIT_USAGE, f"expected exit {cli.EXIT_USAGE}, got {code}"
    assert cli.USAGE in errors, f"stderr must show the usage {cli.USAGE!r}, got {errors!r}"


def test_a_plan_outside_the_working_directory_exits_one_with_the_fix(capsys, tmp_path, monkeypatch):
    project = tmp_path / "project"
    project.mkdir()
    (tmp_path / "plan.json").write_text("{}")
    monkeypatch.chdir(project)
    code, output, errors = run_cli(capsys, ["plan", "check", "../plan.json"])
    assert code == cli.EXIT_DOMAIN_FAILURE, f"expected exit {cli.EXIT_DOMAIN_FAILURE}, got {code}"
    assert "outside" in errors and "Fix:" in errors, f"stderr must say the path is outside and give a fix, got {errors!r}"
