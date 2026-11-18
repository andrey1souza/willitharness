import json

from files import plant
from willitharness import cli

TARGET = "ZQ-8841-lumen"
CONTROL = "purple-giraffe-91"
SEED = 3
RUNS = 3
TARGET_LINE = f"Verification code: {TARGET}\n"


def probe_arguments(directory, boundary, runs):
    return [
        "probe", "--agent", "fake", "--directory", str(directory), "--boundary", str(boundary),
        "--runs", str(runs), "--seed", str(SEED), "--target-token", TARGET, "--control-token", CONTROL,
    ]


def invoke_probe(capsys, directory, boundary, runs):
    code = cli.main(probe_arguments(directory, boundary, runs))
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def test_agents_only_directory_prints_loaded(tmp_path, capsys):
    work = plant(tmp_path / "work", "AGENTS.md", TARGET_LINE)
    code, output, errors = invoke_probe(capsys, work, work, RUNS)
    assert code == cli.EXIT_OK, f"expected exit 0, got {code}; stderr {errors!r}"
    assert output.splitlines()[0] == "reachability: Loaded", f"unexpected output {output!r}"


def test_ancestor_claude_file_prints_masked(tmp_path, capsys):
    root = plant(tmp_path / "fixture", "CLAUDE.md", "Parent instructions.\n")
    child = plant(root / "child", "AGENTS.md", TARGET_LINE)
    code, output, errors = invoke_probe(capsys, child, root, RUNS)
    assert code == cli.EXIT_OK, f"expected exit 0, got {code}; stderr {errors!r}"
    assert output.splitlines()[0] == "reachability: Masked", f"unexpected output {output!r}"


def test_fewer_runs_than_the_minimum_exit_two_with_the_fix(tmp_path, capsys):
    work = plant(tmp_path / "work", "AGENTS.md", TARGET_LINE)
    code, output, errors = invoke_probe(capsys, work, work, RUNS - 1)
    assert code == cli.EXIT_USAGE, f"expected exit {cli.EXIT_USAGE}, got {code}"
    assert errors.strip() == "at least 3 probe runs per arm are needed; use --runs 3 or more", f"unexpected stderr {errors!r}"


def claude_stand_in(arguments, index):
    return [json.dumps({"type": "result", "subtype": "success", "is_error": False, "result": TARGET, "total_cost_usd": 0.01})]


def test_the_claude_agent_path_prints_the_cost_with_an_injected_runner(tmp_path, capsys):
    work = plant(tmp_path / "work", "AGENTS.md", TARGET_LINE)
    arguments = [
        "--agent", "claude", "--directory", str(work), "--runs", str(RUNS),
        "--target-token", TARGET, "--control-token", CONTROL,
    ]
    code = cli.probe_command(arguments, {"claude": claude_stand_in})
    output = capsys.readouterr().out.splitlines()
    assert code == cli.EXIT_OK, f"expected exit 0, got {code}"
    assert output[0] == "reachability: Loaded" and output[-1] == "cost: $0.0300", f"unexpected output {output}"


def test_the_fake_agent_without_a_seed_exits_two_with_the_fix(tmp_path, capsys):
    work = plant(tmp_path / "work", "AGENTS.md", TARGET_LINE)
    arguments = ["--agent", "fake", "--directory", str(work), "--runs", str(RUNS), "--target-token", TARGET, "--control-token", CONTROL]
    code = cli.probe_command(arguments, cli.RUNNERS)
    errors = capsys.readouterr().err
    assert code == cli.EXIT_USAGE, f"expected exit {cli.EXIT_USAGE}, got {code}"
    assert "the fake agent needs --seed and --boundary" in errors, f"unexpected stderr {errors!r}"
