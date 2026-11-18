import argparse
import os
import sys
import tempfile
import uuid
from pathlib import Path

from willitharness import claude_agent
from willitharness.paths import inside
from willitharness.plan import MIN_PROBE_RUNS
from willitharness.probe import PROMPT_TEMPLATE, parse_run, probe
from willitharness.vocabulary import Reach

MARKER_LABEL = "Isolation marker"
MARKER_HEX_LENGTH = 12
MEMORY_FILE_NAME = "CLAUDE.md"
COST_CAP_USD = 0.20
ISOLATED_BUDGET_USD = claude_agent.DEFAULT_RUN_BUDGET_USD
UNISOLATED_BUDGET_USD = 0.05
CONTROL_CODE = "purple-giraffe-91"
EXIT_PASSED = 0
EXIT_NOT_PROVEN = 1
NOT_PROVEN_MESSAGE = "isolation not proven"
UNREACHED = "absent"
REACHED = "present"


def new_marker():
    marker = f"isolation-{uuid.uuid4().hex[:MARKER_HEX_LENGTH]}"
    assert marker.startswith("isolation-") and len(marker) == len("isolation-") + MARKER_HEX_LENGTH, f"unexpected marker {marker!r}"
    assert marker not in (CONTROL_CODE, MARKER_LABEL), f"the marker {marker!r} equals a fixed probe text. Rule: it must be unique. Fix: generate a new one."
    return marker


def config_directory(environ):
    assert hasattr(environ, "get"), f"config_directory needs a mapping of variables, got {type(environ).__name__}. Fix: pass os.environ."
    configured = environ.get("CLAUDE_CONFIG_DIR")
    assert configured, "CLAUDE_CONFIG_DIR is not set. Rule: the check plants its marker in the user-level memory file there. Fix: export CLAUDE_CONFIG_DIR."
    return Path(configured)


def run_with_marker(config_dir, marker, action):
    assert marker and callable(action), f"run_with_marker needs a marker and an action, got {marker!r} and {action!r}. Fix: pass both."
    assert config_dir.is_dir(), f"{config_dir} is not a directory. Rule: the config folder exists. Fix: check CLAUDE_CONFIG_DIR."
    memory_file = inside(config_dir, MEMORY_FILE_NAME)
    existed = memory_file.exists()
    original = memory_file.read_bytes() if existed else b""
    memory_file.write_bytes(original + f"\n{MARKER_LABEL}: {marker}\n".encode())
    try:
        return action()
    finally:
        if existed:
            memory_file.write_bytes(original)
        else:
            memory_file.unlink()


def measure(runner, directory, marker):
    assert directory.is_dir(), f"{directory} is not a directory. Fix: pass the neutral working folder."
    prompt = PROMPT_TEMPLATE.format(label=MARKER_LABEL)
    transcripts = [runner(directory, prompt) for _ in range(MIN_PROBE_RUNS)]
    result = probe([parse_run(lines, marker, CONTROL_CODE) for lines in transcripts])
    cost = sum(claude_agent.transcript_cost(lines) for lines in transcripts)
    assert cost >= 0, f"cost came out as {cost}. Rule: costs are not negative."
    return result.reach, cost


def main(argv, runners, marker):
    assert isinstance(argv, list), f"main needs a list of arguments, got {argv!r}. Fix: pass sys.argv[1:]."
    assert len(runners) == 2 and marker, f"main needs the isolated and unisolated runners and a marker, got {runners!r} and {marker!r}. Fix: pass both."
    parser = argparse.ArgumentParser(prog="isolation_live")
    parser.add_argument("--config-dir", type=Path)
    arguments = parser.parse_args(argv)
    config_dir = arguments.config_dir if arguments.config_dir else config_directory(os.environ)
    isolated_runner, unisolated_runner = runners
    with tempfile.TemporaryDirectory(prefix="willitharness-isolation-") as directory:
        work = Path(directory)
        (isolated, isolated_cost), (unisolated, unisolated_cost) = run_with_marker(
            config_dir, marker, lambda: (measure(isolated_runner, work, marker), measure(unisolated_runner, work, marker))
        )
    print(f"isolated: marker {UNREACHED if isolated is Reach.MASKED else REACHED} ({isolated.value})")
    print(f"unisolated: marker {REACHED if unisolated is Reach.LOADED else UNREACHED} ({unisolated.value})")
    total = isolated_cost + unisolated_cost
    print(f"cost: ${total:.4f}")
    if isolated is not Reach.MASKED or unisolated is not Reach.LOADED or total > COST_CAP_USD:
        print(NOT_PROVEN_MESSAGE)
        return EXIT_NOT_PROVEN
    print("marker absent with flags; present without flags")
    print("GATE G3.8 PASS")
    return EXIT_PASSED


def isolated_runner(directory, prompt):
    assert directory.is_dir(), f"{directory} is not a directory. Fix: pass the neutral working folder."
    assert prompt, "the isolated runner needs a prompt. Fix: pass the probe prompt."
    return claude_agent.ask_claude(directory, prompt, claude_agent.DEFAULT_MODEL, ISOLATED_BUDGET_USD)


def unisolated_runner(directory, prompt):
    assert directory.is_dir(), f"{directory} is not a directory. Fix: pass the neutral working folder."
    assert prompt, "the unisolated runner needs a prompt. Fix: pass the probe prompt."
    command = claude_agent.unisolated_command(prompt, claude_agent.DEFAULT_MODEL, UNISOLATED_BUDGET_USD)
    return claude_agent.run_command(directory, command)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:], (isolated_runner, unisolated_runner), new_marker()))
