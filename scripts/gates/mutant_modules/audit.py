TESTS = (
    'tests/unit/test_rule_class_unit.py',
    'tests/gates/test_audit.py',
)

RULE_CLASS = 'src/willitharness/rule_class.py'
AUDIT = 'src/willitharness/audit.py'
CLI = 'src/willitharness/cli.py'
HOOK_CODE = 'src/willitharness/hook_code.py'

MUTANTS = (
    ('audit-any-file-counts-as-a-script', RULE_CLASS, 'SCRIPT_SUFFIXES = (".sh", ".bash", ".zsh", ".py", ".js", ".mjs", ".ts", ".rb")', 'SCRIPT_SUFFIXES = (".sh", ".bash", ".zsh", ".py", ".js", ".mjs", ".ts", ".rb", ".md")'),
    ('audit-a-missing-script-counts', RULE_CLASS, "        found = inside(root, candidate).is_file()", "        found = True"),
    ('audit-a-script-outside-the-repo-counts', RULE_CLASS, "inside(root, candidate).is_file()", "(root / candidate).is_file()"),
    ('audit-a-bare-word-is-a-command', RULE_CLASS, "    bare = len(span.split()) == 1", "    bare = False"),
    ('audit-a-span-needs-no-cue', RULE_CLASS, "        direction = REQUIRES if REQUIRE_CUE.search(window) else None", "        direction = REQUIRES"),
    ('audit-a-ban-reads-as-a-requirement', RULE_CLASS, "    elif FORBID_CUE.search(window):\n        direction = FORBIDS", "    elif FORBID_CUE.search(window):\n        direction = REQUIRES"),
    ('audit-bullets-inside-fences-count', RULE_CLASS, "        elif fenced:\n            continue", "        elif False:\n            continue"),
    ('audit-continuation-lines-are-dropped', RULE_CLASS, "        elif open_rule and CONTINUATION.match(line):", "        elif False:"),
    ('audit-the-prediction-label-changes', AUDIT, 'PREDICTION_LABEL = "predicted, not verified; a paid probe confirms it"', 'PREDICTION_LABEL = "predicted"'),
    ('audit-writes-the-import-to-the-repo', AUDIT, '    assert diff.startswith("--- "), f"import_diff built', '    path.write_text(new)\n    assert diff.startswith("--- "), f"import_diff built'),
    ('audit-proposes-an-entry-when-a-guard-exists', AUDIT, '        elif not guarded(texts, entry["name"]):', "        else:"),
    ('audit-proposes-an-entry-for-a-required-command', AUDIT, "        if verdict.direction != FORBIDS:", "        if False:"),
    ('audit-proposes-an-entry-for-a-file-that-does-not-load', AUDIT, "        if verdict.label != COMMAND or item.loads == MASKED_LOADS:", "        if verdict.label != COMMAND:"),
    ('audit-never-shortens-a-rule', AUDIT, "SHORT_LIMIT = 60", "SHORT_LIMIT = 600"),
    ('audit-drops-the-flag-pattern', AUDIT, '    blocked = {"program": program, **({"flag_pattern": patterns[0]} if patterns else {})}', '    blocked = {"program": program}'),
    ('audit-any-hook-event-is-a-guard', HOOK_CODE, 'GUARD_EVENT, []', 'GUARD_EVENT, []) or events.get("PostToolUse", []'),
    ('audit-any-settings-hook-event-is-a-guard', HOOK_CODE, 'if hook.event == GUARD_EVENT]', 'if True]'),
    ('audit-hook-code-is-ignored', AUDIT, '    found = any(pattern.search(text) for text in texts)', '    found = any(pattern.search(text) for text in texts[:0])'),
    ('audit-follows-imports-without-limit', HOOK_CODE, '            texts += [imported[1]] if imported else []', '            texts += [imported[1]] if imported else []\n            texts += script_code(root, [resolved.parent], specifier)'),
    ('audit-reads-code-outside-the-repo', HOOK_CODE, '        resolved = inside(root, path)', '        resolved = (root / path).resolve()'),
    ('audit-refusal-exits-zero', CLI, "        print(refusal, file=sys.stderr)\n        return EXIT_DOMAIN_FAILURE", "        print(refusal, file=sys.stderr)\n        return EXIT_OK"),
)
