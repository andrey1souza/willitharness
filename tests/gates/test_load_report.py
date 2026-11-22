import json

from cli_runner import run_cli

from willitharness.load_report import build_load_report

EXIT_OK = 0
EXIT_REFUSED = 1
LOAD_REPORT = "load-report"
RUN_HOOKS = "--run-hooks"
RULE_MARKER = "Rule:"
FIX_MARKER = "Fix:"
MARKER_FILE = "hook-ran.marker"
CLAUDE_TEXT = "Use small functions.\nSee @docs/style.md for style.\n"
STYLE_TEXT = "No comments."
AGENTS_TEXT = "Agents file."
SKILL_BODY = "Step one.\nStep two."
FULL_SKILL = f"---\nname: backup\ndescription: Back up files\n---\n{SKILL_BODY}\n"
BARE_SKILL = f"---\nname: bare\n---\n{SKILL_BODY}\n"
CONTEXT_HOOK = "printf 'twelve chars'"
JSON_CONTEXT_HOOK = 'printf \'{"hookSpecificOutput": {"additionalContext": "abcde"}}\''
FAILING_HOOK = "exit 3"
SLOW_HOOK = "sleep 5"
SHORT_TIMEOUT_SECONDS = 1
SETTINGS = "settings.json"
LOCAL_SETTINGS = "settings.local.json"
HOOKS_NOT_MEASURED = (("SessionStart", "a", FAILING_HOOK), ("UserPromptSubmit", "b", SLOW_HOOK), ("PreToolUse", "c", CONTEXT_HOOK))


def write(root, relative, text):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    assert path.read_text(encoding="utf-8") == text, f"{path} did not keep its text"
    return path


def settings_with(root, name, hook):
    event, matcher, command = hook
    group = {"hooks": [{"type": "command", "command": command}]}
    if matcher is not None:
        group["matcher"] = matcher
    return write(root, f".claude/{name}", json.dumps({"hooks": {event: [group]}}))


def full_project(root):
    write(root, "CLAUDE.md", CLAUDE_TEXT)
    write(root, "docs/style.md", STYLE_TEXT)
    write(root, "AGENTS.md", AGENTS_TEXT)
    write(root, ".claude/skills/backup/SKILL.md", FULL_SKILL)
    write(root, ".claude/skills/bare/SKILL.md", BARE_SKILL)
    settings_with(root, SETTINGS, ("SessionStart", None, CONTEXT_HOOK))
    return root


def test_G7_1_the_report_lists_instruction_files_skills_and_hooks_with_character_counts(tmp_path, capsys):
    full_project(tmp_path)
    code, out, err = run_cli(capsys, [LOAD_REPORT, str(tmp_path)])
    lines = out.splitlines()
    assert code == EXIT_OK and err == "", f"got {code} {out!r} {err!r}"
    assert f"instruction AGENTS.md: {len(AGENTS_TEXT)} characters" in lines, f"got {lines!r}"
    assert f"instruction CLAUDE.md: {len(CLAUDE_TEXT)} characters" in lines, f"got {lines!r}"
    assert f"instruction docs/style.md: {len(STYLE_TEXT)} characters" in lines, f"an imported file must be listed, got {lines!r}"
    assert f"skill backup: name and description {len('backup') + len('Back up files')} characters (always loaded), body {len(SKILL_BODY)} characters (loaded after the Skill tool call)" in lines, f"got {lines!r}"


def test_G7_1_a_skill_without_a_description_counts_only_its_name(tmp_path, capsys):
    full_project(tmp_path)
    code, out, err = run_cli(capsys, [LOAD_REPORT, str(tmp_path)])
    assert code == EXIT_OK, f"got {code} {out!r} {err!r}"
    assert f"skill bare: name and description {len('bare')} characters (always loaded), body {len(SKILL_BODY)} characters" in out, f"got {out!r}"


def test_G7_1_a_hook_is_not_measured_and_never_runs_by_default(tmp_path, capsys):
    marker = tmp_path / MARKER_FILE
    settings_with(tmp_path, SETTINGS, ("SessionStart", None, f"touch {marker}; printf context"))
    code, out, err = run_cli(capsys, [LOAD_REPORT, str(tmp_path)])
    assert code == EXIT_OK, f"got {code} {out!r} {err!r}"
    assert "hook SessionStart matcher (any) (settings.json): context not measured" in out, f"got {out!r}"
    assert not marker.exists(), "Rule: a hook is arbitrary code and the default report never runs it. The marker file shows the hook ran."


def test_G7_1_run_hooks_runs_the_hook_and_gives_the_size_of_its_context(tmp_path, capsys):
    marker = tmp_path / MARKER_FILE
    settings_with(tmp_path, SETTINGS, ("SessionStart", None, f"touch {marker}; printf twelve-chars"))
    code, out, err = run_cli(capsys, [LOAD_REPORT, str(tmp_path), RUN_HOOKS])
    assert code == EXIT_OK, f"got {code} {out!r} {err!r}"
    assert marker.exists(), "--run-hooks must run the hook, but the marker file is missing"
    assert "context 12 characters" in out, f"got {out!r}"


def test_G7_1_run_hooks_reads_additional_context_from_a_json_answer(tmp_path, capsys):
    settings_with(tmp_path, SETTINGS, ("UserPromptSubmit", "Bash", JSON_CONTEXT_HOOK))
    code, out, err = run_cli(capsys, [LOAD_REPORT, str(tmp_path), RUN_HOOKS])
    assert code == EXIT_OK and "hook UserPromptSubmit matcher Bash (settings.json): context 5 characters" in out, f"got {code} {out!r} {err!r}"


def test_G7_1_a_failing_slow_or_live_session_hook_stays_not_measured(tmp_path):
    hooks = {event: [{"matcher": matcher, "hooks": [{"type": "command", "command": command}]}] for event, matcher, command in HOOKS_NOT_MEASURED}
    write(tmp_path, ".claude/settings.json", json.dumps({"hooks": hooks}))
    out = "\n".join(build_load_report(tmp_path, SHORT_TIMEOUT_SECONDS))
    assert "characters" not in out, f"got {out!r}"
    assert out.count("context not measured") == 3, f"every hook must say not measured, got {out!r}"


def test_G7_1_the_same_project_gives_the_same_report_twice(tmp_path, capsys):
    full_project(tmp_path)
    settings_with(tmp_path, LOCAL_SETTINGS, ("PreToolUse", "Bash", CONTEXT_HOOK))
    first = run_cli(capsys, [LOAD_REPORT, str(tmp_path)])
    second = run_cli(capsys, [LOAD_REPORT, str(tmp_path)])
    assert first == second and first[1], f"two runs differ: {first!r} and {second!r}"


def test_G7_1_a_file_that_cannot_be_read_exits_one_and_names_the_file(tmp_path, capsys):
    full_project(tmp_path)
    (tmp_path / "docs" / "style.md").write_bytes(b"\xff\xfe\x00bad")
    code, out, err = run_cli(capsys, [LOAD_REPORT, str(tmp_path)])
    assert code == EXIT_REFUSED and out == "", f"got {code} {out!r} {err!r}"
    assert "style.md" in err and RULE_MARKER in err and FIX_MARKER in err, f"got {err!r}"


def test_G7_1_a_settings_file_that_is_not_json_exits_one_and_names_the_file(tmp_path, capsys):
    write(tmp_path, ".claude/settings.json", "{not json")
    code, out, err = run_cli(capsys, [LOAD_REPORT, str(tmp_path)])
    assert code == EXIT_REFUSED and out == "", f"got {code} {out!r} {err!r}"
    assert "settings.json" in err and RULE_MARKER in err and FIX_MARKER in err, f"got {err!r}"


def test_G7_1_a_settings_file_with_the_wrong_hooks_layout_exits_one(tmp_path, capsys):
    write(tmp_path, ".claude/settings.json", json.dumps({"hooks": {"SessionStart": ["x"]}}))
    code, out, err = run_cli(capsys, [LOAD_REPORT, str(tmp_path)])
    assert code == EXIT_REFUSED and "settings.json" in err and FIX_MARKER in err, f"got {code} {out!r} {err!r}"


def test_G7_1_a_missing_project_folder_is_refused_with_rule_and_fix(tmp_path, capsys):
    code, out, err = run_cli(capsys, [LOAD_REPORT, str(tmp_path / "nowhere")])
    assert code == EXIT_REFUSED and out == "", f"got {code} {out!r} {err!r}"
    assert "nowhere" in err and RULE_MARKER in err and FIX_MARKER in err, f"got {err!r}"


def test_G7_1_the_current_folder_is_the_default_project(tmp_path, capsys, monkeypatch):
    write(tmp_path, "CLAUDE.md", CLAUDE_TEXT)
    monkeypatch.chdir(tmp_path)
    code, out, err = run_cli(capsys, [LOAD_REPORT])
    assert code == EXIT_OK and f"instruction CLAUDE.md: {len(CLAUDE_TEXT)} characters" in out, f"got {code} {out!r} {err!r}"


def test_G7_1_a_folder_with_nothing_says_so(tmp_path, capsys):
    code, out, err = run_cli(capsys, [LOAD_REPORT, str(tmp_path)])
    assert code == EXIT_OK and out == "no instruction files, skills or hooks found\n", f"got {code} {out!r} {err!r}"


def test_G7_1_imports_stop_at_the_depth_limit_and_survive_a_cycle(tmp_path, capsys):
    write(tmp_path, "CLAUDE.md", "@a0.md")
    for number in range(8):
        write(tmp_path, f"a{number}.md", f"@a{number + 1}.md")
    write(tmp_path, "a8.md", "@CLAUDE.md")
    code, out, err = run_cli(capsys, [LOAD_REPORT, str(tmp_path)])
    listed = [line for line in out.splitlines() if line.startswith("instruction")]
    assert code == EXIT_OK and len(listed) == 6, f"CLAUDE.md plus 5 imports expected, got {code} {listed!r} {err!r}"


def test_G7_1_an_import_outside_the_project_is_not_read(tmp_path, capsys):
    project = tmp_path / "project"
    write(tmp_path, "outside.md", "secret")
    write(project, "CLAUDE.md", "@../outside.md")
    code, out, err = run_cli(capsys, [LOAD_REPORT, str(project)])
    assert code == EXIT_OK and "outside" not in out, f"got {code} {out!r} {err!r}"


def test_G7_1_instruction_lines_are_sorted_by_path_not_by_discovery_order(tmp_path, capsys):
    write(tmp_path, "AGENTS.md", "@zzz.md")
    write(tmp_path, "zzz.md", "z")
    write(tmp_path, "CLAUDE.md", "@bbb.md")
    write(tmp_path, "bbb.md", "b")
    code, out, err = run_cli(capsys, [LOAD_REPORT, str(tmp_path)])
    names = [line.split(" ")[1].rstrip(":") for line in out.splitlines()]
    assert code == EXIT_OK and names == ["AGENTS.md", "CLAUDE.md", "bbb.md", "zzz.md"], f"got {code} {names!r} {err!r}"


def test_G7_1_hook_lines_are_sorted_by_event_and_read_both_settings_files(tmp_path, capsys):
    hooks = {"Stop": [{"hooks": [{"type": "command", "command": CONTEXT_HOOK}]}], "SessionStart": [{"hooks": [{"type": "command", "command": CONTEXT_HOOK}]}]}
    write(tmp_path, ".claude/settings.json", json.dumps({"hooks": hooks}))
    settings_with(tmp_path, LOCAL_SETTINGS, ("PreToolUse", "Bash", CONTEXT_HOOK))
    code, out, err = run_cli(capsys, [LOAD_REPORT, str(tmp_path)])
    events = [line.split(" ")[1] for line in out.splitlines()]
    assert code == EXIT_OK and events == ["PreToolUse", "SessionStart", "Stop"], f"got {code} {events!r} {err!r}"
    assert "(settings.local.json)" in out, f"the local settings file must be read, got {out!r}"
