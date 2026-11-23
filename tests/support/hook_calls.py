import json
import subprocess

PKILL_MESSAGE_START = "Blocked by guard (pkill)"


def bash_call(command):
    assert command.strip(), f"bash_call needs a command, got {command!r}. Fix: pass a command line."
    text = json.dumps({"tool_name": "Bash", "tool_input": {"command": command}})
    assert json.loads(text)["tool_input"]["command"] == command, f"the call lost its command: {text!r}"
    return text


def run_hook_command(command, call_text, directory):
    assert command, "run_hook_command needs the hook command. Fix: read it from the settings."
    return subprocess.run(command, shell=True, input=call_text, capture_output=True, text=True, cwd=directory)
