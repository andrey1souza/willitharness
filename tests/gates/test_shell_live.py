import json

import shell_live

CLEAN_REPLY = "cp is /bin/cp"
ALIAS_REPLY = "cp is an alias for cp -i"
EXPENSIVE = 0.06


def shell_transcript(reply, cost):
    return [json.dumps({"type": "result", "subtype": "success", "is_error": False, "result": reply, "total_cost_usd": cost})]


def clean_runner(directory, command):
    return shell_transcript(CLEAN_REPLY, 0.001)


def alias_runner(directory, command):
    return shell_transcript(ALIAS_REPLY, 0.001)


def over_cap_runner(directory, command):
    return shell_transcript(CLEAN_REPLY, EXPENSIVE)


def silent_runner(directory, command):
    return []


def test_a_clean_reply_passes_and_an_alias_reply_fails():
    assert shell_live.shell_is_clean(CLEAN_REPLY) is True, f"a plain /bin/cp must count as clean, got {CLEAN_REPLY!r}"
    assert shell_live.shell_is_clean(ALIAS_REPLY) is False, f"an alias must count as a leak, got {ALIAS_REPLY!r}"
    assert shell_live.shell_is_clean("") is False, "an empty reply proves nothing"
    assert shell_live.shell_is_clean("type: cp: not found") is False, "a reply without the real path proves nothing"
    assert shell_live.shell_is_clean("cp is /bin/cp with an ALIAS") is False, "the alias word is matched in any case"


def test_the_gate_passes_on_a_clean_shell(capsys):
    assert shell_live.main(clean_runner) == 0, "a clean reply within the cost cap must pass"
    output = capsys.readouterr().out
    assert "GATE SHELL PASS" in output, f"the pass line must print, got {output!r}"


def test_the_gate_fails_on_an_alias_a_silent_agent_and_an_overspend(capsys):
    assert shell_live.main(alias_runner) == 1, "an alias leak must fail the gate"
    assert shell_live.main(silent_runner) == 1, "a run with no reply must fail the gate"
    assert shell_live.main(over_cap_runner) == 1, "a run above the cost cap must fail the gate"
    output = capsys.readouterr().out
    assert output.count("shell not clean") == 3, f"each failure must print the message, got {output!r}"


def test_the_command_gives_the_agent_the_bash_tool_and_only_the_type_command():
    command = shell_live.shell_command(shell_live.PROMPT, "haiku", 0.03)
    assert command[command.index("--tools") + 1] == "Bash", f"the shell check needs the Bash tool, got {command}"
    assert command[command.index("--allowedTools") + 1] == "Bash(type:*)", f"only the type command may run, got {command}"
