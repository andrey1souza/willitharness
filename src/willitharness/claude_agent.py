import json
import os
import subprocess
from dataclasses import dataclass, replace

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
SYSTEM_PROMPT_FLAG = "--append-system-prompt-file"
NO_SYSTEM_PROMPT_FILE = ""
SKILL_TOOL = "Skill"
SKILL_ALLOW_PATTERN = "Skill({name})"
SLASH_COMMANDS_OFF_FLAG = "--disable-slash-commands"
INIT_EVENT = "system"
INIT_SUBTYPE = "init"
SKILLS_FIELD = "skills"
PINNED_CLAUDE_VERSION = "2.1.331"
BUILTIN_SKILLS = (
    "batch", "claude-api", "claude-approvals", "code-review", "dataviz", "debug", "deep-research", "design", "design-sync", "doctor",
    "fewer-permission-prompts", "loop", "plugin-authoring", "run", "run-skill-generator", "simplify", "update-config", "verify", "workflow-authoring",
)
assert BUILTIN_SKILLS == tuple(sorted(set(BUILTIN_SKILLS))), f"the pinned built-in skills {BUILTIN_SKILLS!r} are not unique and sorted"


class AgentUnavailable(Exception):
    pass


@dataclass(frozen=True)
class ToolPolicy:
    tools: str
    allowed: tuple
    settings: str = ""
    system_prompt_file: str = ""
    skills: tuple = ()
    skill_plan: bool = False


PROBE_POLICY = ToolPolicy("", ())


def tool_policy(has_guard, commands):
    assert isinstance(commands, (tuple, list)), f"tool_policy needs the commands as a tuple, got {commands!r}. Fix: pass allowed_commands output."
    assert all(commands), f"tool_policy got an empty command in {commands!r}. Fix: pass plain command names."
    policy = ToolPolicy(GUARD_TOOLS if has_guard else EFFECT_TOOLS, tuple(ALLOW_PATTERN.format(command=command) for command in sorted(set(commands))))
    assert policy.tools.startswith(EFFECT_TOOLS), f"the policy {policy!r} lost the Bash tool. Rule: effect and guard runs have Bash."
    return policy


def skill_policy(policy, names):
    assert isinstance(policy, ToolPolicy), f"skill_policy needs a ToolPolicy, got {policy!r}. Fix: use PROBE_POLICY or tool_policy."
    assert isinstance(names, tuple) and all(names), f"skill_policy needs the skill names of the arm as a tuple, got {names!r}. Rule: a skill plan names the skills of each arm, none for an arm without skills. Fix: pass skill_names output."
    tools = f"{policy.tools},{SKILL_TOOL}" if policy.tools else SKILL_TOOL
    allowed = (*policy.allowed, *(SKILL_ALLOW_PATTERN.format(name=name) for name in sorted(set(names))))
    result = replace(policy, tools=tools, allowed=allowed, skills=tuple(sorted(set(names))), skill_plan=True)
    assert SKILL_TOOL in result.tools.split(","), f"the policy {result!r} lost the {SKILL_TOOL} tool. Rule: the skill listing travels with the {SKILL_TOOL} tool."
    return result


def tool_flags(policy):
    assert isinstance(policy, ToolPolicy), f"tool_flags needs a ToolPolicy, got {policy!r}. Fix: use PROBE_POLICY or tool_policy."
    assert not (policy.skills or policy.skill_plan) or SKILL_TOOL in policy.tools.split(","), f"the policy {policy!r} is in a skill plan but has no {SKILL_TOOL} tool. Rule: every arm of a skill plan keeps the {SKILL_TOOL} tool. Fix: build the policy with skill_policy."
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


def system_prompt_flags(policy):
    assert isinstance(policy, ToolPolicy), f"system_prompt_flags needs a ToolPolicy, got {policy!r}. Fix: use PROBE_POLICY or tool_policy."
    flags = [SYSTEM_PROMPT_FLAG, policy.system_prompt_file] if policy.system_prompt_file else []
    assert len(flags) == (2 if policy.system_prompt_file else 0), f"system_prompt_flags built {flags!r}. Rule: the flag and its path go together."
    return flags


def slash_command_flags(policy):
    assert isinstance(policy, ToolPolicy), f"slash_command_flags needs a ToolPolicy, got {policy!r}. Fix: use PROBE_POLICY or tool_policy."
    flags = [] if policy.skill_plan else [SLASH_COMMANDS_OFF_FLAG]
    assert (SLASH_COMMANDS_OFF_FLAG in flags) != policy.skill_plan, f"slash_command_flags built {flags!r} for skill plan {policy.skill_plan!r}. Rule: every arm of a skill plan reaches the {SKILL_TOOL} tool, and no other plan does."
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
        *system_prompt_flags(policy),
        *slash_command_flags(policy),
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


def probe_argv(prompt, model, budget, system_prompt_file):
    assert model, f"probe_argv needs a model, got {model!r}. Fix: pass the model name."
    argv = build_command(prompt, model, budget, replace(PROBE_POLICY, system_prompt_file=system_prompt_file))
    assert argv[argv.index("--tools") + 1] == "", f"a probe run must have no tool, got {argv!r}"
    return argv


def skill_probe_argv(prompt, model, budget, skills):
    assert model, f"skill_probe_argv needs a model, got {model!r}. Fix: pass the model name."
    argv = build_command(prompt, model, budget, skill_policy(PROBE_POLICY, skills))
    assert argv[argv.index("--tools") + 1] == SKILL_TOOL, f"a skill probe run has only the {SKILL_TOOL} tool, got {argv!r}"
    return argv


def ask_claude(directory, prompt, model, budget):
    assert prompt, "ask_claude needs a prompt. Fix: pass the probe prompt."
    assert budget > 0, f"ask_claude needs a budget above 0, got {budget!r}. Rule: every run is capped. Fix: pass the run budget."
    return run_command(directory, probe_argv(prompt, model, budget, NO_SYSTEM_PROMPT_FILE))


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


def listed_skills(transcript):
    assert isinstance(transcript, list), f"listed_skills needs the list of lines, got {type(transcript).__name__}. Fix: pass the lines."
    listed = set()
    for line in transcript:
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict) and event.get("type") == INIT_EVENT and event.get("subtype") == INIT_SUBTYPE:
            listed.update(event.get(SKILLS_FIELD) or ())
    assert all(isinstance(name, str) for name in listed), f"a skill name is not text in {listed!r}"
    return sorted(listed)


def foreign_skills(transcript, names):
    assert isinstance(names, tuple), f"foreign_skills needs the skill names of the arm as a tuple, got {names!r}. Fix: pass skill_names output."
    allowed = {*BUILTIN_SKILLS, *names}
    foreign = [name for name in listed_skills(transcript) if name not in allowed]
    assert not set(foreign) & allowed, f"foreign skills {foreign!r} hold an allowed skill from {sorted(allowed)!r}"
    return foreign
