from pathlib import Path

from willitharness import cli

REPO_ROOT = Path(__file__).resolve().parents[2]
GOOD_PLAN = REPO_ROOT / "fixtures" / "plans" / "good.json"
BAD_PLAN = REPO_ROOT / "fixtures" / "plans" / "bad-noise-pair.json"
BAD_PLAN_MESSAGE = "noise pair must repeat the LOO arm C; B2 repeats B"


def run_cli(capsys, arguments):
    code = cli.main(arguments)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def test_a_good_plan_passes_the_check(capsys):
    code, output, errors = run_cli(capsys, ["plan", "check", str(GOOD_PLAN)])
    assert code == cli.EXIT_OK, f"expected exit {cli.EXIT_OK}, got {code}; stderr {errors!r}"
    assert output.startswith("plan ok: pilot-no-pkill"), f"unexpected output {output!r}"


def test_G1_8_the_bad_noise_pair_plan_exits_one_with_the_named_arms(capsys):
    code, output, errors = run_cli(capsys, ["plan", "check", str(BAD_PLAN)])
    assert code == cli.EXIT_DOMAIN_FAILURE, f"expected exit {cli.EXIT_DOMAIN_FAILURE}, got {code}"
    assert BAD_PLAN_MESSAGE in errors, f"stderr must hold {BAD_PLAN_MESSAGE!r}, got {errors!r}"


def test_a_missing_plan_file_exits_one_with_a_fix(capsys, tmp_path):
    code, output, errors = run_cli(capsys, ["plan", "check", str(tmp_path / "nothing.json")])
    assert code == cli.EXIT_DOMAIN_FAILURE, f"expected exit {cli.EXIT_DOMAIN_FAILURE}, got {code}"
    assert "Fix:" in errors, f"stderr must end with a fix, got {errors!r}"


def test_a_plan_that_is_not_json_exits_one(capsys, tmp_path):
    broken = tmp_path / "broken.json"
    broken.write_text("{not json")
    code, output, errors = run_cli(capsys, ["plan", "check", str(broken)])
    assert code == cli.EXIT_DOMAIN_FAILURE, f"expected exit {cli.EXIT_DOMAIN_FAILURE}, got {code}"
    assert "not valid JSON" in errors, f"unexpected stderr {errors!r}"


def test_an_unknown_command_exits_two_with_the_usage(capsys):
    code, output, errors = run_cli(capsys, ["banana"])
    assert code == cli.EXIT_USAGE, f"expected exit {cli.EXIT_USAGE}, got {code}"
    assert cli.USAGE in errors, f"stderr must show the usage {cli.USAGE!r}, got {errors!r}"
