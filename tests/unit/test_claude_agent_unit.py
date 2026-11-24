import json
import math
from dataclasses import replace

import pytest

from willitharness.claude_agent import PROBE_POLICY, ToolPolicy, build_command, skill_policy, tool_policy, transcript_cost, unisolated_command

MODEL = "haiku"
BUDGET = 0.03


def test_the_command_isolates_the_run_from_the_users_own_settings():
    command = build_command("hello", MODEL, BUDGET, PROBE_POLICY)
    for flag in ("--strict-mcp-config", "--disable-slash-commands", "--no-session-persistence"):
        assert flag in command, f"{flag} is missing from {command}"
    assert command[command.index("--setting-sources") + 1] == "project,local", f"setting sources wrong in {command}"


def test_the_command_caps_the_budget_and_removes_every_tool():
    command = build_command("hello", MODEL, BUDGET, PROBE_POLICY)
    assert command[command.index("--max-budget-usd") + 1] == str(BUDGET), f"budget wrong in {command}"
    assert command[command.index("--tools") + 1] == "", f"tools must be empty in {command}"


def test_the_command_streams_json_with_the_model_and_the_prompt():
    command = build_command("hello", MODEL, BUDGET, PROBE_POLICY)
    assert command[:3] == ["claude", "-p", "hello"], f"unexpected start {command[:3]}"
    assert command[command.index("--output-format") + 1] == "stream-json" and "--verbose" in command, f"got {command}"
    assert command[command.index("--model") + 1] == MODEL, f"model wrong in {command}"


def test_a_zero_budget_is_rejected():
    with pytest.raises(AssertionError) as raised:
        build_command("hello", MODEL, 0, PROBE_POLICY)
    assert "budget above 0" in str(raised.value), f"unexpected message {str(raised.value)!r}"


def test_the_cost_comes_from_the_result_event():
    lines = [json.dumps({"type": "system"}), json.dumps({"type": "result", "total_cost_usd": 0.0123})]
    assert math.isclose(transcript_cost(lines), 0.0123), f"unexpected cost from {lines}"


def test_a_transcript_without_a_cost_costs_nothing():
    assert transcript_cost([json.dumps({"type": "system"}), "not json"]) == 0.0, "no cost field must give 0"


def test_the_unisolated_control_command_drops_the_isolation_flags_only():
    command = unisolated_command("hello", MODEL, BUDGET)
    for flag in ("--setting-sources", "--strict-mcp-config", "--disable-slash-commands"):
        assert flag not in command, f"{flag} must not be in the control command {command}"
    assert command[command.index("--tools") + 1] == "" and command[command.index("--max-budget-usd") + 1] == str(BUDGET), f"got {command}"


def test_a_probe_command_has_no_tool_no_allowlist_and_no_permission_mode():
    command = build_command("hello", MODEL, BUDGET, PROBE_POLICY)
    assert "--allowedTools" not in command and "--permission-mode" not in command, f"a probe run must not get tool flags, got {command}"
    assert command[command.index("--tools") + 1] == "", f"a probe run must keep an empty tool list, got {command}"


def test_an_effect_policy_has_bash_and_one_pattern_per_command_sorted():
    assert tool_policy(False, ["pkill", "ls", "pkill"]) == ToolPolicy("Bash", ("Bash(ls:*)", "Bash(pkill:*)")), "an effect policy is Bash with sorted unique patterns"


def test_a_guard_policy_adds_write_and_edit_but_no_pattern_for_them():
    assert tool_policy(True, ["ls"]) == ToolPolicy("Bash,Write,Edit", ("Bash(ls:*)",)), "a guard policy adds Write and Edit to the tools only"


def test_a_policy_command_sets_tools_allowlist_and_the_default_permission_mode_beside_the_isolation_flags():
    command = build_command("hello", MODEL, BUDGET, tool_policy(False, ["ls", "pkill"]))
    assert command[command.index("--tools") + 1] == "Bash", f"tools wrong in {command}"
    assert command[command.index("--allowedTools") + 1] == "Bash(ls:*),Bash(pkill:*)", f"allowlist wrong in {command}"
    assert command[command.index("--permission-mode") + 1] == "default", f"permission mode wrong in {command}"
    assert all(flag in command for flag in ("--strict-mcp-config", "--disable-slash-commands", "--no-session-persistence")), f"isolation flag lost in {command}"


def test_a_policy_without_commands_passes_no_empty_allowlist():
    command = build_command("hello", MODEL, BUDGET, tool_policy(False, []))
    assert "--allowedTools" not in command and command[command.index("--permission-mode") + 1] == "default", f"got {command}"


def test_a_policy_with_settings_passes_them_once_after_the_allowlist():
    settings = '{"sandbox": {"enabled": true}}'
    policy = ToolPolicy("Bash", ("Bash(ls:*)",), settings)
    command = build_command("hello", MODEL, BUDGET, policy)
    assert command.count("--settings") == 1 and command[command.index("--settings") + 1] == settings, f"settings wrong in {command}"
    assert command.index("--settings") > command.index("--allowedTools"), f"settings must follow the allowlist, got {command}"


def test_a_policy_without_settings_and_a_probe_get_no_settings_flag():
    plain = build_command("hello", MODEL, BUDGET, tool_policy(False, ["ls"]))
    assert "--settings" not in plain, f"a policy built without settings must not pass the flag, got {plain}"
    probe = build_command("hello", MODEL, BUDGET, PROBE_POLICY)
    assert "--settings" not in probe, f"a probe run keeps sandbox-exec and gets no Claude sandbox, got {probe}"


def test_a_probe_with_settings_is_refused():
    with pytest.raises(AssertionError) as raised:
        build_command("hello", MODEL, BUDGET, ToolPolicy("", (), "{}"))
    assert "Rule:" in str(raised.value) and "--settings" in str(raised.value), f"unexpected message {str(raised.value)!r}"


def test_a_policy_with_a_system_prompt_file_adds_the_append_flag_and_its_path():
    command = build_command("hello", MODEL, BUDGET, replace(PROBE_POLICY, system_prompt_file="/rules/system-prompt.txt"))
    assert command[command.index("--append-system-prompt-file") + 1] == "/rules/system-prompt.txt", f"flag missing in {command}"


def test_a_policy_without_a_system_prompt_file_adds_no_append_flag():
    assert "--append-system-prompt-file" not in build_command("hello", MODEL, BUDGET, PROBE_POLICY), f"the default command must not carry the flag, got {build_command('hello', MODEL, BUDGET, PROBE_POLICY)}"


def test_a_command_without_a_skill_plan_is_exactly_the_command_from_before_T77():
    policy = replace(tool_policy(False, ["pkill"]), settings="{}", system_prompt_file="/rule.txt")
    assert build_command("hello", MODEL, BUDGET, policy) == [
        "claude", "-p", "hello", "--model", "haiku", "--setting-sources", "project,local", "--strict-mcp-config",
        "--max-budget-usd", "0.03", "--tools", "Bash", "--permission-mode", "default", "--allowedTools", "Bash(pkill:*)",
        "--settings", "{}", "--append-system-prompt-file", "/rule.txt", "--disable-slash-commands", "--no-session-persistence",
        "--output-format", "stream-json", "--verbose",
    ], "the command of a plan with no skill arm changed. Rule: T82 touches skill plans only."


def test_a_skill_policy_adds_the_skill_tool_and_drops_the_slash_command_flag():
    command = build_command("hello", MODEL, BUDGET, skill_policy(tool_policy(True, ["pkill"]), ("b", "a", "a")))
    assert command[command.index("--tools") + 1] == "Bash,Write,Edit,Skill", f"got {command}"
    assert command[command.index("--allowedTools") + 1] == "Bash(pkill:*),Skill(a),Skill(b)", f"got {command}"
    assert "--disable-slash-commands" not in command, f"got {command}"


def test_skill_names_without_the_skill_tool_are_refused():
    with pytest.raises(AssertionError) as raised:
        build_command("hello", MODEL, BUDGET, replace(PROBE_POLICY, skills=("a",)))
    assert "Rule: every arm of a skill plan keeps the Skill tool" in str(raised.value), f"got {raised.value}"


def test_a_skill_policy_of_an_arm_without_skills_adds_the_skill_tool_and_no_allow_rule():
    command = build_command("hello", MODEL, BUDGET, skill_policy(tool_policy(False, ["pkill"]), ()))
    assert command[command.index("--tools") + 1] == "Bash,Skill", f"got {command}"
    assert command[command.index("--allowedTools") + 1] == "Bash(pkill:*)", f"got {command}"
    assert "--disable-slash-commands" not in command, f"got {command}"


def test_a_skill_policy_needs_the_names_as_a_tuple():
    with pytest.raises(AssertionError) as raised:
        skill_policy(PROBE_POLICY, "abc")
    assert "Rule: a skill plan names the skills of each arm" in str(raised.value), f"got {raised.value}"
