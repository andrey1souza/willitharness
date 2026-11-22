import json

import pytest

from files import plant
from lifecycle_site import SiteSpec, make_site
from willitharness import cli
from willitharness.lifecycle import lifecycle_dir, read_reach
from willitharness.vocabulary import Reach

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


TWO_ARMS = SiteSpec(arm_count=2, budget_usd=1.0, run_cap_usd=0.02, reps=2, max_retries=0)


def record_arguments(work, arm):
    return probe_arguments(work, work, RUNS) + ["--plan", "plan.json", "--arm", arm]


def planted_work(tmp_path):
    return plant(tmp_path / "work", "AGENTS.md", TARGET_LINE)


def test_probe_with_a_plan_and_an_arm_records_the_result(tmp_path, monkeypatch, capsys):
    site = make_site(tmp_path, TWO_ARMS)
    monkeypatch.chdir(tmp_path)
    code = cli.main(record_arguments(planted_work(tmp_path), "A"))
    output = capsys.readouterr().out.splitlines()
    assert code == cli.EXIT_OK, f"expected exit 0, got {code}"
    assert output[-1].startswith("recorded: arm A is Loaded in plan"), f"unexpected output {output}"
    assert read_reach(lifecycle_dir(site.root, site.plan)) == {"A": Reach.LOADED}, "only arm A must be recorded as Loaded"


def test_a_masked_probe_is_recorded_as_masked(tmp_path, monkeypatch, capsys):
    site = make_site(tmp_path, TWO_ARMS)
    root = plant(tmp_path / "fixture", "CLAUDE.md", "Parent instructions.\n")
    child = plant(root / "child", "AGENTS.md", TARGET_LINE)
    monkeypatch.chdir(tmp_path)
    arguments = probe_arguments(child, root, RUNS) + ["--plan", "plan.json", "--arm", "B"]
    code = cli.main(arguments)
    capsys.readouterr()
    assert code == cli.EXIT_OK, f"expected exit 0, got {code}"
    assert read_reach(lifecycle_dir(site.root, site.plan)) == {"B": Reach.MASKED}, "the recorded result must be the probe result, not a fixed value"


def test_every_arm_probed_through_the_cli_lets_run_start(tmp_path, monkeypatch, capsys):
    make_site(tmp_path, TWO_ARMS)
    monkeypatch.chdir(tmp_path)
    work = planted_work(tmp_path)
    assert cli.main(["plan", "check", "plan.json"]) == cli.EXIT_OK, "the plan must pass its check"
    assert cli.main(["world", "check", "world"]) == cli.EXIT_OK, "the world must pass its check"
    refused = cli.main(["run", "plan.json", "--agent", "fake"])
    refusal = capsys.readouterr().err
    assert refused == cli.EXIT_DOMAIN_FAILURE and "willitharness probe --plan <plan.json> --arm A" in refusal, f"run before probing must name the command, got {refused} and {refusal!r}"
    for arm in ("A", "B"):
        assert cli.main(record_arguments(work, arm)) == cli.EXIT_OK, f"probing arm {arm} must succeed"
    capsys.readouterr()
    code = cli.main(["run", "plan.json", "--agent", "fake"])
    output = capsys.readouterr().out
    assert code == cli.EXIT_OK, f"after probing every arm run must start and finish, got {code}; {output!r}"
    assert output == "plan Complete: 4 runs, spent $0.04\n", f"2 arms x 2 reps are 4 runs, not 4 runs counted as records, got {output!r}"


def test_an_unknown_arm_is_refused_before_any_probe_runs(tmp_path, monkeypatch, capsys):
    make_site(tmp_path, TWO_ARMS)
    monkeypatch.chdir(tmp_path)

    def must_not_run(arguments, index):
        raise AssertionError("the probe ran for an arm that is not in the plan")

    arguments = record_arguments(planted_work(tmp_path), "Z")[1:]
    code = cli.probe_command(arguments, {"fake": must_not_run})
    errors = capsys.readouterr().err
    assert code == cli.EXIT_DOMAIN_FAILURE, f"expected exit 1, got {code}"
    assert "arm 'Z' is not an arm of plan" in errors and "Fix: use one of A, B." in errors, f"unexpected stderr {errors!r}"


@pytest.mark.parametrize("lone_option", [["--plan", "plan.json"], ["--arm", "A"]])
def test_one_of_the_plan_and_arm_options_alone_exits_two_with_the_fix(tmp_path, monkeypatch, capsys, lone_option):
    make_site(tmp_path, TWO_ARMS)
    monkeypatch.chdir(tmp_path)
    work = planted_work(tmp_path)
    code = cli.main(probe_arguments(work, work, RUNS) + lone_option)
    errors = capsys.readouterr().err
    assert code == cli.EXIT_USAGE, f"expected exit {cli.EXIT_USAGE}, got {code}"
    assert errors.strip() == cli.RECORD_NEEDS_BOTH, f"unexpected stderr {errors!r}"


def test_a_missing_plan_file_is_refused_with_exit_one(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    work = planted_work(tmp_path)
    code = cli.main(probe_arguments(work, work, RUNS) + ["--plan", "missing.json", "--arm", "A"])
    errors = capsys.readouterr().err
    assert code == cli.EXIT_DOMAIN_FAILURE and "missing.json" in errors, f"expected exit 1 naming the plan, got {code} and {errors!r}"


def test_a_plan_that_already_ran_refuses_a_new_result(tmp_path, monkeypatch, capsys):
    make_site(tmp_path, TWO_ARMS)
    monkeypatch.chdir(tmp_path)
    work = planted_work(tmp_path)
    cli.main(["world", "check", "world"])
    for arm in ("A", "B"):
        cli.main(record_arguments(work, arm))
    assert cli.main(["run", "plan.json", "--agent", "fake"]) == cli.EXIT_OK, "the plan must finish first"
    capsys.readouterr()
    code = cli.main(record_arguments(work, "A"))
    errors = capsys.readouterr().err
    assert code == cli.EXIT_DOMAIN_FAILURE, f"expected exit 1, got {code}"
    assert "reachability is recorded before the first run" in errors and "Fix:" in errors, f"unexpected stderr {errors!r}"
