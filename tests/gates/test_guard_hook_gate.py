import json
import sys

from guard_site import RULES_FILE
from hook_calls import PKILL_MESSAGE_START, bash_call, run_hook_command

from willitharness.guard_hook import ALLOW_EXIT_CODE, BLOCK_EXIT_CODE, hook_settings


def test_the_command_from_the_settings_blocks_a_violation_when_the_shell_runs_it(tmp_path):
    command = json.loads(hook_settings(RULES_FILE))["hooks"]["PreToolUse"][0]["hooks"][0]["command"]
    blocked = run_hook_command(command, bash_call("pkill -f vitest"), tmp_path)
    allowed = run_hook_command(command, bash_call("ls"), tmp_path)
    assert (blocked.returncode, allowed.returncode) == (BLOCK_EXIT_CODE, ALLOW_EXIT_CODE), f"the shell run gave {blocked} and {allowed}"
    assert blocked.stderr.startswith(PKILL_MESSAGE_START), f"the block message did not reach standard error: {blocked.stderr!r}"
    assert sys.executable in command, f"the hook must run with the python of the runner, got {command!r}"
