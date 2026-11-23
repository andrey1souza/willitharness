import json
import shlex
import sys
from pathlib import Path

from willitharness.guard import decide_command, load_rules
from willitharness.stream import BASH_TOOL

HOOK_EVENT = "PreToolUse"
HOOK_TYPE = "command"
HOOK_TIMEOUT_SECONDS = 10
HOOK_MODULE = "willitharness.guard_hook"
ISOLATED_MODE_FLAG = "-I"
UNREADABLE = object()
NOT_BASH = object()
ALLOW_EXIT_CODE = 0
BLOCK_EXIT_CODE = 2
UNREADABLE_CALL = (
    "guard hook could not read the tool call {call!r}. "
    "Rule: a guard that cannot read a call blocks it, so a broken hook never lets a violation through. "
    "Fix: send the tool call as one JSON object with tool_name and tool_input on standard input."
)
UNREADABLE_RULES = (
    "guard hook could not load the rules {path}. "
    "Rule: a guard that cannot load its rules blocks every call. "
    "Fix: write the rules file in the format of fixtures/guard/rules.json."
)


def hook_command(rules_path, python=sys.executable):
    assert rules_path.is_absolute(), f"{rules_path} is not absolute. Rule: the hook runs in the agent workspace, so it names its rules by absolute path. Fix: pass the run folder copy."
    assert python, "hook_command needs a python path. Fix: pass sys.executable."
    command = shlex.join([python, ISOLATED_MODE_FLAG, "-m", HOOK_MODULE, str(rules_path)])
    assert shlex.split(command)[-1] == str(rules_path), f"the command {command!r} lost the rules path"
    return command


def guard_hook_settings(rules_path, python=sys.executable):
    document = {
        "hooks": {
            HOOK_EVENT: [{"matcher": BASH_TOOL, "hooks": [{"type": HOOK_TYPE, "command": hook_command(rules_path, python), "timeout": HOOK_TIMEOUT_SECONDS}]}]
        }
    }
    text = json.dumps(document)
    assert json.loads(text) == document, f"the hook settings did not survive JSON: {text!r}"
    assert BASH_TOOL in text, f"the hook settings lost the {BASH_TOOL} matcher: {text!r}"
    return text


def call_command(call_text):
    assert isinstance(call_text, str), f"call_command needs the text of the call, got {call_text!r}. Fix: pass standard input."
    try:
        call = json.loads(call_text)
    except json.JSONDecodeError:
        return UNREADABLE
    if not isinstance(call, dict) or not isinstance(call.get("tool_name"), str):
        return UNREADABLE
    if call["tool_name"] != BASH_TOOL:
        return NOT_BASH
    command = call.get("tool_input", {}).get("command") if isinstance(call.get("tool_input"), dict) else None
    result = command if isinstance(command, str) and command.strip() else UNREADABLE
    assert result is UNREADABLE or isinstance(result, str), f"call_command returned {result!r}. Rule: a command is text, or a marker for a call it cannot judge."
    return result


def judge_call(call_text, rules):
    assert rules, "judge_call needs rules. Fix: load them with load_rules."
    command = call_command(call_text)
    if command is UNREADABLE:
        return BLOCK_EXIT_CODE, UNREADABLE_CALL.format(call=call_text)
    if command is NOT_BASH:
        return ALLOW_EXIT_CODE, ""
    decision = decide_command(command, rules)
    code = BLOCK_EXIT_CODE if decision.blocked else ALLOW_EXIT_CODE
    assert (code == BLOCK_EXIT_CODE) == bool(decision.message), f"exit code {code} disagrees with the message {decision.message!r}"
    return code, decision.message


def main(arguments, standard_input, standard_error):
    assert isinstance(arguments, list), f"main needs a list of arguments, got {arguments!r}. Fix: pass sys.argv[1:]."
    assert len(arguments) == 1, f"the hook takes one argument, the rules file, got {arguments!r}. Fix: build the command with hook_command."
    path = Path(arguments[0])
    try:
        rules = load_rules(path.parent, path.name)
    except (AssertionError, OSError, ValueError):
        standard_error.write(UNREADABLE_RULES.format(path=path) + "\n")
        return BLOCK_EXIT_CODE
    code, message = judge_call(standard_input.read(), rules)
    if message:
        standard_error.write(message + "\n")
    assert code in (ALLOW_EXIT_CODE, BLOCK_EXIT_CODE), f"the hook returned {code}. Rule: a hook allows with 0 or blocks with 2."
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:], sys.stdin, sys.stderr))
