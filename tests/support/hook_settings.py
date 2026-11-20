import json
from guards import install_user_hook as installer

SCRIPT_NAME = "remote_write_guard.py"
BACKUP_NAME = "settings.json.before-willitharness-guard"
KEEP_AWAKE_HOLD = "~/.claude/hooks/keep-awake.sh hold"
KEEP_AWAKE_RELEASE = "~/.claude/hooks/keep-awake.sh release"
MEMORY_COMMAND = "ai-memory capture"
ORIGINAL = (
    "{\n"
    '  "hooks": {\n'
    '    "PreToolUse": [\n'
    "      {\n"
    '        "hooks": [\n'
    "          {\n"
    '            "type": "command",\n'
    f'            "command": "{KEEP_AWAKE_HOLD}"\n'
    "          }\n"
    "        ]\n"
    "      }\n"
    "    ],\n"
    '    "Stop": [\n'
    "      {\n"
    '        "hooks": [\n'
    "          {\n"
    '            "type": "command",\n'
    f'            "command": "{KEEP_AWAKE_RELEASE}"\n'
    "          }\n"
    "        ]\n"
    "      }\n"
    "    ]\n"
    "  },\n"
    '  "theme": "dark"\n'
    "}\n"
)
BARE = '{\n  "theme": "dark"\n}\n'


def expected_after_install(script):
    return (
        ORIGINAL.replace(
            "      }\n    ],\n    \"Stop\"",
            "      },\n"
            "      {\n"
            f'        "matcher": "Bash|Write|Edit|MultiEdit|NotebookEdit",\n'
            '        "hooks": [\n'
            "          {\n"
            '            "type": "command",\n'
            f'            "command": "python3 {script}"\n'
            "          }\n"
            "        ]\n"
            "      }\n"
            "    ],\n"
            '    "Stop"',
        )
    )


def group(command, matcher=None):
    body = {"hooks": [{"type": "command", "command": command}]}
    return {"matcher": matcher, **body} if matcher else body


def settings_text(groups, extra=None):
    document = {"hooks": {"PreToolUse": groups}, **(extra or {})}
    return json.dumps(document, indent=2) + "\n"


def guard_script(tmp_path):
    folder = tmp_path / "main-checkout" / "scripts" / "guards"
    folder.mkdir(parents=True)
    path = folder / SCRIPT_NAME
    path.write_text("print('guard')\n")
    path.chmod(0o755)
    return path


def seeded(tmp_path):
    folder = tmp_path / "config-a"
    folder.mkdir()
    path = folder / "settings.json"
    path.write_text(ORIGINAL)
    return path


def command_of(script):
    return f"python3 {script}"


def invoke(action, script, targets):
    return installer.main([action, "--script", str(script), *map(str, targets)])
