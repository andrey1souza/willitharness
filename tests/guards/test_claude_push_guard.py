import io
import json

import pytest

from guards import claude_push_guard as guard


@pytest.mark.parametrize(
    "command",
    [
        "git commit --no-verify -m x",
        "git push --no-verify",
        "git -c core.hooksPath=/dev/null commit -m x",
        "git rebase --no-verify main",
    ],
)
def test_skipping_hooks_is_blocked(command):
    code, message = guard.verdict_for(command)
    assert code == guard.BLOCK_EXIT_CODE, "%r must be blocked, got code %r" % (command, code)
    assert message == guard.HOOK_SKIP_MESSAGE, "a hook skip must get the hook message, got %r" % (message,)
    assert "Fix:" in message, "the message must end with a fix for %r, got %r" % (command, message)


@pytest.mark.parametrize(
    "command",
    [
        "git status",
        "git push origin main",
        "git -C /tmp/work push",
        "git commit -m 'skip nothing'",
        "echo git commit --no-verify",
        "ls -la",
    ],
)
def test_commands_that_do_not_skip_hooks_pass(command):
    verdict = guard.verdict_for(command)
    assert verdict == (guard.ALLOW_EXIT_CODE, ""), "%r does not skip hooks and must pass, got %r" % (command, verdict)


def test_main_ignores_other_tools():
    event = json.dumps({"tool_name": "Edit", "tool_input": {"command": "git commit --no-verify"}})
    code = guard.main(io.StringIO(event))
    assert code == guard.ALLOW_EXIT_CODE, "only the Bash tool is judged, but Edit got code %r" % (code,)


def test_main_blocks_a_bash_hook_skip(capsys):
    event = json.dumps({"tool_name": "Bash", "tool_input": {"command": "git commit --no-verify -m x"}})
    code = guard.main(io.StringIO(event))
    printed = capsys.readouterr().err
    assert code == guard.BLOCK_EXIT_CODE, "a Bash hook skip must be blocked, got code %r" % (code,)
    assert "hooks" in printed, "the hook must print the hook message, got %r" % (printed,)
