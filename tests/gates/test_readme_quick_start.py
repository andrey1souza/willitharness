from pathlib import Path

from files import copy_tree
from willitharness import cli

REPOSITORY = Path(__file__).resolve().parents[2]
README_TEXT = (REPOSITORY / "README.md").read_text()
EXAMPLE = Path("examples") / "offline-demo"
COPY_COMMAND = f"cp -R {EXAMPLE.as_posix()} /tmp/offline-demo"
PLAN_FILE = "plan.json"
WORLD_FOLDER = "world"
WORK_FOLDER = "work"
TARGET = "ZQ-8841-lumen"
CONTROL = "purple-giraffe-91"
SEED = "3"
RUNS = "3"
PROGRAM = "willitharness"
EXIT_OK = 0
EXIT_REFUSED = 1
PLAN_OK_LINE = "plan ok: demo (2 arms, 2 reps)"
WORLD_VALID_PREFIX = "world: valid (hash "
REACHED_LINE = "reachability: Loaded"
TOKEN_LINE = "the target token appeared in 3 of 3 runs"
RECORDED_FIRST = "recorded: arm A is Loaded in plan demo; plan state WorldValidated"
RECORDED_SECOND = "recorded: arm B is Loaded in plan demo; plan state ReachabilityChecked"
RUN_LINE = "plan Complete: 8 runs, spent $0.04"
ANALYZE_REFUSAL = "has no leave_one_out arm or no rule arm to compare"
SHOWN_IN_README = (PLAN_OK_LINE, WORLD_VALID_PREFIX, REACHED_LINE, TOKEN_LINE, RECORDED_FIRST, RUN_LINE)


def probe_arguments_for(arm):
    return [
        "probe", "--agent", "fake", "--directory", WORK_FOLDER, "--boundary", WORK_FOLDER,
        "--runs", RUNS, "--seed", SEED, "--target-token", TARGET, "--control-token", CONTROL,
        "--plan", PLAN_FILE, "--arm", arm,
    ]


STEPS = (
    (["plan", "check", PLAN_FILE], EXIT_OK, [PLAN_OK_LINE]),
    (["world", "check", WORLD_FOLDER], EXIT_OK, [WORLD_VALID_PREFIX]),
    (probe_arguments_for("A"), EXIT_OK, [REACHED_LINE, TOKEN_LINE, RECORDED_FIRST]),
    (probe_arguments_for("B"), EXIT_OK, [REACHED_LINE, TOKEN_LINE, RECORDED_SECOND]),
    (["run", PLAN_FILE, "--agent", "fake"], EXIT_OK, [RUN_LINE]),
    (["analyze", PLAN_FILE], EXIT_REFUSED, [ANALYZE_REFUSAL]),
)


def command_text(arguments):
    return " ".join([PROGRAM, *arguments])


def test_the_readme_lists_the_copy_command_and_every_command_the_test_runs():
    assert COPY_COMMAND in README_TEXT, f"the README lacks {COPY_COMMAND!r}. Rule: the quick start copies the example. Fix: restore the line."
    missing = [command_text(arguments) for arguments, _, _ in STEPS if command_text(arguments) not in README_TEXT]
    assert missing == [], f"the README does not list {missing}. Rule: the test runs only what the README shows. Fix: make both lists match."


def test_the_readme_shows_the_output_lines_the_test_expects():
    missing = [line for line in SHOWN_IN_README if line not in README_TEXT]
    assert missing == [], f"the README does not show {missing}. Rule: shown output is real. Fix: copy it from the run."


def test_the_example_runs_the_quick_start_commands_with_the_listed_results(tmp_path, monkeypatch, capsys):
    copy = copy_tree(REPOSITORY / EXAMPLE, tmp_path / EXAMPLE.name)
    monkeypatch.chdir(copy)
    for arguments, expected_code, expected_lines in STEPS:
        code = cli.main(arguments)
        captured = capsys.readouterr()
        shown = captured.out + captured.err
        assert code == expected_code, f"{command_text(arguments)} exited {code}, expected {expected_code}. Output: {shown}"
        missing = [line for line in expected_lines if line not in shown]
        assert missing == [], f"{command_text(arguments)} did not print {missing}. Output: {shown}"
