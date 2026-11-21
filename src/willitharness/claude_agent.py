import json
import os
import subprocess
from dataclasses import dataclass

from willitharness.isolation import agent_environment
from willitharness.probe import COST_FIELD, RESULT_EVENT

DEFAULT_MODEL = "haiku"
DEFAULT_RUN_BUDGET_USD = 0.03
RUN_TIMEOUT_SECONDS = 120
VERSION_TIMEOUT_SECONDS = 30
CLAUDE_BINARY = "claude"
EFFECT_TOOLS = "Bash"
GUARD_TOOLS = "Bash,Write,Edit"
PERMISSION_MODE = "default"
ALLOW_PATTERN = "Bash({command}:*)"
SETTINGS_FLAG = "--settings"


class AgentUnavailable(Exception):
    pass


@dataclass(frozen=True)
class ToolPolicy:
    tools: str
    allowed: tuple
    settings: str = ""


PROBE_POLICY = ToolPolicy("", ())


def tool_policy(has_guard, commands):
    assert isinstance(commands, (tuple, list)), f"tool_policy needs the commands as a tuple, got {commands!r}. Fix: pass allowed_commands output."
    assert all(commands), f"tool_policy got an empty command in {commands!r}. Fix: pass plain command names."
    policy = ToolPolicy(GUARD_TOOLS if has_guard else EFFECT_TOOLS, tuple(ALLOW_PATTERN.format(command=command) for command in sorted(set(commands))))
    assert policy.tools.startswith(EFFECT_TOOLS), f"the policy {policy!r} lost the Bash tool. Rule: effect and guard runs have Bash."
    return policy


def tool_flags(policy):
    assert isinstance(policy, ToolPolicy), f"tool_flags needs a ToolPolicy, got {policy!r}. Fix: use PROBE_POLICY or tool_policy."
    flags = ["--tools", policy.tools]
    if policy.tools:
        flags += ["--permission-mode", PERMISSION_MODE]
    if policy.tools and policy.allowed:
        flags += ["--allowedTools", ",".join(policy.allowed)]
    if policy.settings:
        flags += [SETTINGS_FLAG, policy.settings]
    assert flags[:2] == ["--tools", policy.tools], f"tool_flags changed the tools flag: {flags!r}"
    assert policy.tools or SETTINGS_FLAG not in flags, f"a run without tools got {SETTINGS_FLAG}: {flags!r}. Rule: only a tool-using run gets the Claude sandbox."
    return flags


def build_command(prompt, model, budget, policy):
    assert prompt, "build_command needs a prompt. Fix: pass the probe prompt."
    assert model and budget > 0, f"build_command needs a model and a budget above 0, got {model!r} and {budget!r}. Fix: pass both."
    return [
        CLAUDE_BINARY, "-p", prompt,
        "--model", model,
        "--setting-sources", "project,local",
        "--strict-mcp-config",
        "--max-budget-usd", str(budget),
        *tool_flags(policy),
        "--disable-slash-commands",
        "--no-session-persistence",
        "--output-format", "stream-json",
        "--verbose",
    ]


def unisolated_command(prompt, model, budget):
    assert prompt, "unisolated_command needs a prompt. Fix: pass the probe prompt."
    assert model and budget > 0, f"unisolated_command needs a model and a budget above 0, got {model!r} and {budget!r}. Fix: pass both."
    return [
        CLAUDE_BINARY, "-p", prompt,
        "--model", model,
        "--max-budget-usd", str(budget),
        "--tools", "",
        "--no-session-persistence",
        "--output-format", "stream-json",
        "--verbose",
    ]


def ask_claude(directory, prompt, model, budget):
    assert prompt, "ask_claude needs a prompt. Fix: pass the probe prompt."
    assert budget > 0, f"ask_claude needs a budget above 0, got {budget!r}. Rule: every run is capped. Fix: pass the run budget."
    return run_command(directory, build_command(prompt, model, budget, PROBE_POLICY))


def run_command(directory, command):
    assert directory.is_dir(), f"{directory} is not a directory. Rule: the agent starts in the directory under test. Fix: pass an existing directory."
    assert command and command[0] == CLAUDE_BINARY, f"run_command runs the claude CLI, got {command[:1]!r}. Fix: build the command with build_command."
    try:
        completed = subprocess.run(
            command, cwd=directory, capture_output=True, text=True, timeout=RUN_TIMEOUT_SECONDS, env=agent_environment(os.environ)
        )
    except subprocess.TimeoutExpired:
        return []
    lines = completed.stdout.splitlines()
    assert isinstance(lines, list), f"stdout split into {lines!r}, not a list"
    return lines


def claude_version():
    assert VERSION_TIMEOUT_SECONDS > 0, f"the version timeout is {VERSION_TIMEOUT_SECONDS}. Rule: every call has a wall-clock limit above 0. Fix: restore the constant."
    try:
        completed = subprocess.run([CLAUDE_BINARY, "--version"], capture_output=True, text=True, timeout=VERSION_TIMEOUT_SECONDS, env=agent_environment(os.environ))
    except (OSError, subprocess.TimeoutExpired) as error:
        raise AgentUnavailable(version_refusal(f"it could not start ({error})")) from error
    version = completed.stdout.strip()
    if completed.returncode != 0 or not version:
        raise AgentUnavailable(version_refusal(f"it exited {completed.returncode} and printed {version!r}"))
    assert version, "claude_version returned an empty version"
    return version


def version_refusal(reason):
    assert reason, "version_refusal needs a reason. Fix: say what happened."
    message = f"claude --version failed: {reason}. Rule: a run needs the claude CLI on PATH. Fix: install Claude Code so that claude --version prints a version."
    assert "Rule:" in message and "Fix:" in message, f"version_refusal lost its rule or fix: {message!r}"
    return message


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
