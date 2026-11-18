import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import NamedTuple

from willitharness import claude_agent
from willitharness.arms import remove_section
from willitharness.plan import MIN_PROBE_RUNS
from willitharness.probe import DEFAULT_LABEL, PROMPT_TEMPLATE, parse_run, probe

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = REPO_ROOT / "fixtures" / "probe"
DEFAULT_EXPECTED = FIXTURES / "live-expected.json"
COST_CAP_USD = 0.10
EXIT_PASSED = 0
EXIT_FAILED = 1
TARGET_CODE = "ZQ-8841-lumen"
NON_TARGET_CODE = "lagoon-52"
NON_TARGET_LABEL = "Reference code"
CONTROL_CODE = "purple-giraffe-91"
LOO_SECTION = "Working here as an agent"


class Case(NamedTuple):
    name: str
    label: str
    token: str


CASES = (
    Case("ancestor-masks-agents", DEFAULT_LABEL, TARGET_CODE),
    Case("agents-only", DEFAULT_LABEL, TARGET_CODE),
    Case("LOO non-target token", NON_TARGET_LABEL, NON_TARGET_CODE),
)


def prepare_workspace(workspace):
    assert workspace.is_dir(), f"{workspace} is not a directory. Fix: pass the workspace directory."
    shutil.copytree(FIXTURES / "ancestor-masks-agents", workspace / "ancestor-masks-agents")
    shutil.copytree(FIXTURES / "agents-only", workspace / "agents-only")
    loo = workspace / "loo-arm"
    loo.mkdir()
    (loo / "AGENTS.md").write_text(remove_section((FIXTURES / "loo-source" / "AGENTS.md").read_text(), LOO_SECTION))
    assert (loo / "AGENTS.md").is_file() and (workspace / "agents-only" / "AGENTS.md").is_file(), f"the workspace {workspace} is incomplete"
    return {
        "ancestor-masks-agents": workspace / "ancestor-masks-agents" / "child",
        "agents-only": workspace / "agents-only",
        "LOO non-target token": loo,
    }


def run_case(case, directory, runner):
    assert directory.is_dir(), f"{directory} is not a directory. Fix: prepare the workspace first."
    prompt = PROMPT_TEMPLATE.format(label=case.label)
    transcripts = [runner(directory, prompt) for _ in range(MIN_PROBE_RUNS)]
    result = probe([parse_run(lines, case.token, CONTROL_CODE) for lines in transcripts])
    cost = sum(claude_agent.transcript_cost(lines) for lines in transcripts)
    assert cost >= 0, f"cost came out as {cost}. Rule: costs are not negative."
    return result.reach.value, cost


def main(argv, runner):
    assert isinstance(argv, list), f"main needs a list of arguments, got {argv!r}. Fix: pass sys.argv[1:]."
    assert callable(runner), f"runner must be a function that runs the agent, got {runner!r}. Fix: pass one."
    parser = argparse.ArgumentParser(prog="probe_live")
    parser.add_argument("--expected", type=Path, default=DEFAULT_EXPECTED)
    arguments = parser.parse_args(argv)
    expected = json.loads(arguments.expected.read_text())
    total_cost = 0.0
    mismatches = 0
    with tempfile.TemporaryDirectory(prefix="willitharness-live-") as directory:
        directories = prepare_workspace(Path(directory))
        for case in CASES:
            reach, cost = run_case(case, directories[case.name], runner)
            total_cost += cost
            print(f"{case.name}: {reach}")
            if reach != expected[case.name]:
                print(f"MISMATCH {case.name}: expected {expected[case.name]}, got {reach}")
                mismatches += 1
    print(f"cost: ${total_cost:.4f}")
    if total_cost > COST_CAP_USD:
        print(f"COST OVER CAP: ${total_cost:.4f} is above ${COST_CAP_USD:.2f}")
        return EXIT_FAILED
    if mismatches:
        return EXIT_FAILED
    print("GATE G2.3 PASS")
    return EXIT_PASSED


def live_runner(directory, prompt):
    assert directory.is_dir(), f"{directory} is not a directory. Fix: pass the case directory."
    assert prompt, "the live runner needs a prompt. Fix: pass the probe prompt."
    return claude_agent.ask_claude(directory, prompt, claude_agent.DEFAULT_MODEL, claude_agent.DEFAULT_RUN_BUDGET_USD)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:], live_runner))
