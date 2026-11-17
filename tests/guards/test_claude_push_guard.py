import io
import json
from datetime import datetime

import pytest

from guards import claude_push_guard as guard

INSIDE = datetime(2026, 11, 17, 20, 0)
OUTSIDE = datetime(2026, 11, 17, 14, 0)
OUTSIDE_ENVIRONMENT = {"WILLITHARNESS_NOW": "2026-11-17T14:00:00"}


@pytest.mark.parametrize(
    "command",
    [
        "git push origin main",
        "git -C /tmp/work push",
        "git status && git push",
        "cd x; git push --force-with-lease",
    ],
)
def test_push_outside_the_window_is_blocked(command):
    code, message = guard.verdict_for(command, OUTSIDE)
    assert code == guard.BLOCK_EXIT_CODE, "%r at 14:00 must be blocked, got code %r" % (command, code)
    assert "push-window" in message, "the block message must name the rule for %r, got %r" % (command, message)


@pytest.mark.parametrize("command", ["git push origin main", "git -C /tmp/work push"])
def test_push_inside_the_window_is_allowed(command):
    verdict = guard.verdict_for(command, INSIDE)
    assert verdict == (guard.ALLOW_EXIT_CODE, ""), "%r at 20:00 must be allowed, got %r" % (command, verdict)


@pytest.mark.parametrize(
    "command",
    [
        "git status",
        "git commit -m 'push notes'",
        "echo git push",
        "ls -la",
    ],
)
def test_commands_that_only_mention_push_are_not_blocked(command):
    verdict = guard.verdict_for(command, OUTSIDE)
    assert verdict == (guard.ALLOW_EXIT_CODE, ""), "%r is not a push and must pass, got %r" % (command, verdict)


@pytest.mark.parametrize(
    "command",
    [
        "git commit --no-verify -m x",
        "git push --no-verify",
        "git -c core.hooksPath=/dev/null commit -m x",
        "git rebase --no-verify main",
    ],
)
def test_skipping_hooks_is_blocked_inside_the_window(command):
    code, message = guard.verdict_for(command, INSIDE)
    assert code == guard.BLOCK_EXIT_CODE, "%r at 20:00 must still be blocked, got code %r" % (command, code)
    assert "hooks" in message, "the message must name the hooks for %r, got %r" % (command, message)
    assert "Fix:" in message, "the message must end with a fix for %r, got %r" % (command, message)


def test_skipping_hooks_is_blocked_outside_the_window_with_the_hook_message():
    code, message = guard.verdict_for("git commit --no-verify -m x", OUTSIDE)
    assert code == guard.BLOCK_EXIT_CODE, "a hook skip at 14:00 must be blocked, got code %r" % (code,)
    assert message == guard.HOOK_SKIP_MESSAGE, "a hook skip must get the hook message first, got %r" % (message,)


def test_main_ignores_other_tools():
    event = json.dumps({"tool_name": "Edit", "tool_input": {"command": "git push"}})
    code = guard.main(io.StringIO(event), OUTSIDE_ENVIRONMENT)
    assert code == guard.ALLOW_EXIT_CODE, "only the Bash tool is judged, but Edit got code %r" % (code,)


def test_main_blocks_a_bash_push_outside_the_window(capsys):
    event = json.dumps({"tool_name": "Bash", "tool_input": {"command": "git push"}})
    code = guard.main(io.StringIO(event), OUTSIDE_ENVIRONMENT)
    printed = capsys.readouterr().err
    assert code == guard.BLOCK_EXIT_CODE, "a Bash push at 14:00 must be blocked, got code %r" % (code,)
    assert "push-window" in printed, "the hook must print the window message, got %r" % (printed,)
