import io
import json
import shlex
from pathlib import Path

import pytest
from guard_site import RULES_FILE
from hook_calls import PKILL_MESSAGE_START, bash_call

from willitharness.guard import load_rules
from willitharness.guard_hook import ALLOW_EXIT_CODE, BLOCK_EXIT_CODE, HOOK_TIMEOUT_SECONDS, hook_command, guard_hook_settings, judge_call, main

def rules():
    return load_rules(RULES_FILE.parent, RULES_FILE.name)


def run_with(rules_path, call_text):
    standard_error = io.StringIO()
    code = main([str(rules_path)], io.StringIO(call_text), standard_error)
    return code, standard_error.getvalue()


def run_main(call_text):
    return run_with(RULES_FILE, call_text)


def test_a_blocked_command_exits_two_and_writes_its_message_to_standard_error():
    code, error = run_main(bash_call("pkill -f vitest"))
    assert code == BLOCK_EXIT_CODE == 2, f"a blocked command must exit 2, got {code}"
    assert error.startswith(PKILL_MESSAGE_START) and "`kill PID...`" in error, f"the message is wrong: {error!r}"


def test_an_allowed_command_exits_zero_and_writes_nothing():
    code, error = run_main(bash_call("ps -axo pid,command | grep '[v]itest'"))
    assert (code, error) == (ALLOW_EXIT_CODE, ""), f"an allowed command must pass silently, got {code} and {error!r}"


def test_a_call_to_another_tool_passes():
    call = json.dumps({"tool_name": "Write", "tool_input": {"file_path": "a.txt", "content": "pkill -f vitest"}})
    assert run_main(call) == (ALLOW_EXIT_CODE, ""), "the hook judges Bash commands only"


@pytest.mark.parametrize("call_text", ["", "not json", "[]", '{"tool_name": "Bash"}', '{"tool_name": "Bash", "tool_input": {"command": 7}}', '{"tool_name": "Bash", "tool_input": {"command": "  "}}'])
def test_a_call_the_hook_cannot_read_is_blocked_with_a_rule_and_a_fix(call_text):
    code, error = run_main(call_text)
    assert code == BLOCK_EXIT_CODE, f"an unreadable call must be blocked, got {code} for {call_text!r}"
    assert "Rule:" in error and error.strip().endswith("."), f"the message needs a rule: {error!r}"
    assert "Fix:" in error, f"the message needs a fix: {error!r}"


@pytest.mark.parametrize("content", [None, "", "not json", "[]"])
def test_a_missing_or_broken_rules_file_blocks_every_call_with_a_rule_and_a_fix(tmp_path, content):
    path = tmp_path / "rules.json"
    if content is not None:
        path.write_text(content)
    code, error = run_with(path, bash_call("ls"))
    assert code == BLOCK_EXIT_CODE, f"a guard without rules must block, got {code}"
    assert "Rule:" in error and "Fix:" in error and str(path) in error, f"the message needs the path, a rule and a fix: {error!r}"


def test_judge_call_agrees_with_the_exit_code_of_the_hook():
    assert judge_call(bash_call("pgrep -f vitest"), rules())[0] == BLOCK_EXIT_CODE, "pgrep -f is blocked"
    assert judge_call(bash_call("pgrep vitest"), rules())[0] == ALLOW_EXIT_CODE, "pgrep without -f is allowed"


def test_the_settings_hold_one_pre_tool_use_hook_for_bash_with_a_timeout(tmp_path):
    path = tmp_path / "rules.json"
    document = json.loads(guard_hook_settings(path, "/venv/bin/python"))
    assert document == {
        "hooks": {
            "PreToolUse": [
                {
                    "matcher": "Bash",
                    "hooks": [{"type": "command", "command": f"/venv/bin/python -I -m willitharness.guard_hook {path}", "timeout": HOOK_TIMEOUT_SECONDS}],
                }
            ]
        }
    }, f"the hook settings differ from the documented shape: {document}"


def test_a_rules_path_with_a_space_stays_one_word_of_the_command(tmp_path):
    path = tmp_path / "a folder" / "rules.json"
    assert shlex.split(hook_command(path))[-1] == str(path), "the quoted command must give back one path"


def test_a_relative_rules_path_is_refused():
    with pytest.raises(AssertionError) as raised:
        hook_command(Path("rules.json"))
    assert "Rule:" in str(raised.value) and "Fix:" in str(raised.value), f"the refusal needs a rule and a fix: {raised.value}"
