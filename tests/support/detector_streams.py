import json

CLEAN_RESULT = {"type": "result", "subtype": "success", "is_error": False, "num_turns": 2, "total_cost_usd": 0.01, "permission_denials": [], "result": "done"}


def tool_line(tool, tool_input):
    assert tool, "tool_line needs a tool name. Fix: pass Bash, Edit or Write."
    block = {"type": "tool_use", "id": "t1", "name": tool, "input": tool_input}
    line = json.dumps({"type": "assistant", "message": {"content": [block]}})
    assert json.loads(line)["message"]["content"][0]["name"] == tool, f"tool_line lost the tool name in {line}"
    return line


def bash_call_line(command):
    return tool_line("Bash", {"command": command})


def edit_call_line(path):
    return tool_line("Edit", {"file_path": path})


def final_result_line():
    return json.dumps(CLEAN_RESULT)
