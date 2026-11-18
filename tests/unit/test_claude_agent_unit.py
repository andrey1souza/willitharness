import json
import math

import pytest

from willitharness.claude_agent import PROBE_POLICY, ToolPolicy, build_command, tool_policy, transcript_cost, unisolated_command

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
