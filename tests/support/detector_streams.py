import json

CLEAN_RESULT = {"type": "result", "subtype": "success", "is_error": False, "num_turns": 2, "total_cost_usd": 0.01, "permission_denials": [], "result": "done"}


def tool_line(tool, tool_input, call_id="t1"):
    assert tool, "tool_line needs a tool name. Fix: pass Bash, Edit or Write."
    block = {"type": "tool_use", "id": call_id, "name": tool, "input": tool_input}
    line = json.dumps({"type": "assistant", "message": {"content": [block]}})
    assert json.loads(line)["message"]["content"][0]["name"] == tool, f"tool_line lost the tool name in {line}"
    return line


def bash_call_line(command, call_id="t1"):
    return tool_line("Bash", {"command": command}, call_id)


def tool_result_line(call_id, content):
    assert call_id, "tool_result_line needs the id of the call. Fix: pass the id given to bash_call_line."
    return json.dumps({"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": call_id, "content": content}]}})


def edit_call_line(path):
    return tool_line("Edit", {"file_path": path})


def final_result_line():
    return json.dumps(CLEAN_RESULT)
