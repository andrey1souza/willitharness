import shutil
from pathlib import Path

from willitharness import cli

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "probe"
TARGET = "ZQ-8841-lumen"
CONTROL = "purple-giraffe-91"
SEED = 3
RUNS = 3


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
    shutil.copytree(FIXTURES / "agents-only", tmp_path / "work")
    code, output, errors = invoke_probe(capsys, tmp_path / "work", tmp_path / "work", RUNS)
    assert code == cli.EXIT_OK, f"expected exit 0, got {code}; stderr {errors!r}"
    assert output.splitlines()[0] == "reachability: Loaded", f"unexpected output {output!r}"


def test_ancestor_claude_file_prints_masked(tmp_path, capsys):
    shutil.copytree(FIXTURES / "ancestor-masks-agents", tmp_path / "fixture")
    root = tmp_path / "fixture"
    code, output, errors = invoke_probe(capsys, root / "child", root, RUNS)
    assert code == cli.EXIT_OK, f"expected exit 0, got {code}; stderr {errors!r}"
    assert output.splitlines()[0] == "reachability: Masked", f"unexpected output {output!r}"


def test_fewer_runs_than_the_minimum_exit_two_with_the_fix(tmp_path, capsys):
    shutil.copytree(FIXTURES / "agents-only", tmp_path / "work")
    code, output, errors = invoke_probe(capsys, tmp_path / "work", tmp_path / "work", RUNS - 1)
    assert code == cli.EXIT_USAGE, f"expected exit {cli.EXIT_USAGE}, got {code}"
    assert errors.strip() == "at least 3 probe runs per arm are needed; use --runs 3 or more", f"unexpected stderr {errors!r}"
