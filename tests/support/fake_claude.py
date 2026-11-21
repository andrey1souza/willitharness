import json
import os
import stat
import sys

FAKE_VERSION = "9.9.9 (Fake Claude)"
FAKE_MODEL = "fake-model-1"
COMMANDS_FILE = "fake-commands.txt"
COMMANDS_VARIABLE = "CLAUDE_CODE_FAKE_COMMANDS"
COST_VARIABLE = "CLAUDE_CODE_FAKE_COST"
DENIED_COMMAND = "rm important.txt"

BEHAVIOR_FILE = "fake-behavior.txt"
PID_FILE = "agent.pid"
ESCAPE_TARGET_FILE = "fake-escape-target.txt"
SECRET_VARIABLE = "FAKE_SECRET_TOKEN"
OVERSPEND_USD = 5.0
NORMAL_USD = 0.01
HANG_SECONDS = 60

SCRIPT = f'''#!{sys.executable}
import json, os, subprocess, sys, time
if sys.argv[1:] == ["--version"]:
    print("{FAKE_VERSION}")
    sys.exit(0)
behaviors = open("{BEHAVIOR_FILE}").read().split() if os.path.exists("{BEHAVIOR_FILE}") else ["ok"]
arguments = sys.argv[1:]
config = os.environ["CLAUDE_CONFIG_DIR"]
if "hang" in behaviors:
    open(os.path.join(config, "{PID_FILE}"), "w").write(str(os.getpid()))
    time.sleep({HANG_SECONDS})
def write_allowed(path):
    try:
        open(path, "w").write("x")
        return True
    except OSError:
        return False
report = {{
    "arguments": arguments,
    "cwd": os.getcwd(),
    "files": sorted(os.listdir(".")),
    "environment": sorted(os.environ),
    "tmpdir": os.environ.get("TMPDIR"),
    "claude_tmpdir": os.environ.get("CLAUDE_CODE_TMPDIR"),
    "wrote_inside": write_allowed("inside.txt"),
    "wrote_outside": write_allowed(open("{ESCAPE_TARGET_FILE}").read().strip() if os.path.exists("{ESCAPE_TARGET_FILE}") else "/nonexistent/none"),
}}
commands = open("{COMMANDS_FILE}").read().splitlines() if "tools" in behaviors and os.path.exists("{COMMANDS_FILE}") else []
commands += [os.environ["{COMMANDS_VARIABLE}"]] if "{COMMANDS_VARIABLE}" in os.environ else []
print(json.dumps({{"type": "system", "subtype": "init", "model": "{FAKE_MODEL}"}}))
outputs = []
for command in commands:
    block = {{"type": "tool_use", "name": "Bash", "input": {{"command": command}}}}
    print(json.dumps({{"type": "assistant", "message": {{"content": [block]}}}}))
    done = subprocess.run(command, shell=True, capture_output=True, text=True)
    outputs.append(done.stdout + done.stderr)
    print(json.dumps({{"type": "user", "message": {{"content": [{{"type": "tool_result", "content": outputs[-1]}}]}}}}))
report["tool_outputs"] = outputs
report["path"] = os.environ.get("PATH")
report["secret_values"] = sorted(value for name, value in os.environ.items() if any(marker in name for marker in ("KEY", "TOKEN", "SECRET")))
denials = [{{"tool_name": "Bash", "tool_input": {{"command": "{DENIED_COMMAND}"}}}}] if "deny" in behaviors else []
cost = {OVERSPEND_USD} if "overspend" in behaviors else float(os.environ.get("{COST_VARIABLE}", {NORMAL_USD}))
print(json.dumps({{"type": "result", "subtype": "success", "is_error": False, "result": json.dumps(report), "total_cost_usd": cost, "permission_denials": denials}}))
'''


def install_fake_claude(bin_dir):
    assert bin_dir.is_absolute(), f"install_fake_claude needs an absolute folder, got {bin_dir!r}. Fix: pass a path under tmp_path."
    bin_dir.mkdir(parents=True, exist_ok=True)
    script = bin_dir / "claude"
    script.write_text(SCRIPT)
    script.chmod(script.stat().st_mode | stat.S_IXUSR)
    assert os.access(script, os.X_OK), f"{script} is not executable"
    return bin_dir


def report_of(transcript):
    assert transcript, "report_of got an empty transcript. Rule: the fake agent always prints its report. Fix: check the run."
    last = json.loads(transcript[-1])
    assert last["type"] == "result", f"the last line is {last!r}, not a result event. Fix: check the fake agent."
    return json.loads(last["result"])
