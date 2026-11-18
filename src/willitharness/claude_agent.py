import json
import os
import subprocess

from willitharness.isolation import agent_environment
from willitharness.probe import COST_FIELD, RESULT_EVENT

DEFAULT_MODEL = "haiku"
DEFAULT_RUN_BUDGET_USD = 0.03
RUN_TIMEOUT_SECONDS = 120


def build_command(prompt, model, budget):
    assert prompt, "build_command needs a prompt. Fix: pass the probe prompt."
    assert model and budget > 0, f"build_command needs a model and a budget above 0, got {model!r} and {budget!r}. Fix: pass both."
    return [
        "claude", "-p", prompt,
        "--model", model,
        "--setting-sources", "project,local",
        "--strict-mcp-config",
        "--max-budget-usd", str(budget),
        "--tools", "",
        "--disable-slash-commands",
        "--no-session-persistence",
        "--output-format", "stream-json",
        "--verbose",
    ]


def ask_claude(directory, prompt, model, budget):
    assert directory.is_dir(), f"{directory} is not a directory. Rule: the agent starts in the directory under test. Fix: pass an existing directory."
    command = build_command(prompt, model, budget)
    try:
        completed = subprocess.run(
            command, cwd=directory, capture_output=True, text=True, timeout=RUN_TIMEOUT_SECONDS, env=agent_environment(os.environ)
        )
    except subprocess.TimeoutExpired:
        return []
    lines = completed.stdout.splitlines()
    assert isinstance(lines, list), f"stdout split into {lines!r}, not a list"
    return lines


def transcript_cost(transcript):
    assert isinstance(transcript, list), f"transcript_cost needs the list of lines, got {type(transcript).__name__}. Fix: pass the lines."
    cost = 0.0
    for line in transcript:
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict) and event.get("type") == RESULT_EVENT and isinstance(event.get(COST_FIELD), (int, float)):
            cost = float(event[COST_FIELD])
    assert cost >= 0, f"a cost cannot be negative, got {cost}"
    return cost
