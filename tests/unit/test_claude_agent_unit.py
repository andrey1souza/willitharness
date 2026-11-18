import json
import math

import pytest

from willitharness.claude_agent import build_command, transcript_cost, unisolated_command

MODEL = "haiku"
BUDGET = 0.03


def test_the_command_isolates_the_run_from_the_users_own_settings():
    command = build_command("hello", MODEL, BUDGET)
    for flag in ("--strict-mcp-config", "--disable-slash-commands", "--no-session-persistence"):
        assert flag in command, f"{flag} is missing from {command}"
    assert command[command.index("--setting-sources") + 1] == "project,local", f"setting sources wrong in {command}"


def test_the_command_caps_the_budget_and_removes_every_tool():
    command = build_command("hello", MODEL, BUDGET)
    assert command[command.index("--max-budget-usd") + 1] == str(BUDGET), f"budget wrong in {command}"
    assert command[command.index("--tools") + 1] == "", f"tools must be empty in {command}"


def test_the_command_streams_json_with_the_model_and_the_prompt():
    command = build_command("hello", MODEL, BUDGET)
    assert command[:3] == ["claude", "-p", "hello"], f"unexpected start {command[:3]}"
    assert command[command.index("--output-format") + 1] == "stream-json" and "--verbose" in command, f"got {command}"
    assert command[command.index("--model") + 1] == MODEL, f"model wrong in {command}"


def test_a_zero_budget_is_rejected():
    with pytest.raises(AssertionError) as raised:
        build_command("hello", MODEL, 0)
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
