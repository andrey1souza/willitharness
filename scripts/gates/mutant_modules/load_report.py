TESTS = (
    'tests/gates/test_load_report.py',
)

LOAD = 'src/willitharness/load_report.py'
CLI = 'src/willitharness/cli.py'

MUTANTS = (
    ('load-report-runs-hooks-by-default', LOAD, "context = NOT_MEASURED if timeout_seconds is None else measured_context(root, hook, timeout_seconds)", "context = measured_context(root, hook, timeout_seconds or HOOK_TIMEOUT_SECONDS)"),
    ('load-report-never-runs-hooks', LOAD, "context = NOT_MEASURED if timeout_seconds is None else measured_context(root, hook, timeout_seconds)", "context = NOT_MEASURED"),
    ('load-report-measures-a-live-session-hook', LOAD, "    if hook.event not in CONTEXT_EVENTS:", "    if False:"),
    ('load-report-measures-a-failed-hook', LOAD, "    if finished.returncode != SUCCESS_CODE:", "    if False:"),
    ('load-report-has-no-timeout', LOAD, "timeout=timeout_seconds, ", ""),
    ('load-report-ignores-additional-context', LOAD, "    text = str(nested.get(CONTEXT_KEY, \"\")) if isinstance(nested, dict) else \"\"", "    text = output"),
    ('load-report-skips-imports', LOAD, "        queue.extend((item, depth + 1) for item in imported_files(root, relative, seen[relative]))", "        pass"),
    ('load-report-follows-imports-too-deep', LOAD, "MAX_IMPORT_DEPTH = 5", "MAX_IMPORT_DEPTH = 50"),
    ('load-report-reads-imports-outside-the-project', LOAD, "            candidate = inside(root, relative.parent / name)", "            candidate = (root / relative.parent / name).resolve()"),
    ('load-report-skips-agents-file', LOAD, 'ROOT_INSTRUCTION_FILES = ("AGENTS.md", "CLAUDE.md")', 'ROOT_INSTRUCTION_FILES = ("CLAUDE.md",)'),
    ('load-report-counts-description-as-body', LOAD, "len(name) + len(fields.get(\"description\", \"\"))", "len(name)"),
    ('load-report-body-counts-the-header', LOAD, "len(name) + len(fields.get(\"description\", \"\")), len(body))", "len(name) + len(fields.get(\"description\", \"\")), len(body) + len(name))"),
    ('load-report-skips-local-settings', LOAD, 'SETTINGS_FILES = ("settings.json", "settings.local.json")', 'SETTINGS_FILES = ("settings.json",)'),
    ('load-report-drops-the-matcher', LOAD, 'group.get("matcher", NO_MATCHER)', "NO_MATCHER"),
    ('load-report-unsorted-lines', LOAD, "lines = sorted(f\"instruction", "lines = list(f\"instruction"),
    ('load-report-unsorted-hooks', LOAD, "found = sorted((hook for path in paths for hook in hooks_of(root, path)), key=lambda hook: (hook.event, hook.matcher, hook.source, hook.command))", "found = [hook for path in paths for hook in hooks_of(root, path)]"),
    ('load-report-swallows-unreadable-files', LOAD, "        raise LoadRefused(UNREADABLE.format(path=root / relative, reason=type(error).__name__)) from error\n    assert isinstance(text, str)", "        text = \"\"\n    assert isinstance(text, str)"),
    ('load-report-swallows-bad-json', LOAD, "    except json.JSONDecodeError as error:\n        raise LoadRefused(UNREADABLE.format(path=root / relative, reason=type(error).__name__)) from error", "    except json.JSONDecodeError:\n        return {}"),
    ('load-report-accepts-a-bad-hooks-layout', LOAD, "    except (AttributeError, KeyError, TypeError) as error:\n        raise LoadRefused(BAD_SETTINGS.format(path=root / relative, reason=type(error).__name__)) from error", "    except (AttributeError, KeyError, TypeError):\n        return []"),
    ('load-report-accepts-a-missing-folder', LOAD, "    if not folder.is_dir():", "    if False:"),
    ('load-report-empty-folder-prints-nothing', LOAD, "return lines or [NOTHING_LOADED]", "return lines"),
    ('load-report-refusal-exits-zero', CLI, "    except LoadRefused as error:\n        print(str(error), file=sys.stderr)\n        return EXIT_DOMAIN_FAILURE", "    except LoadRefused as error:\n        print(str(error), file=sys.stderr)\n        return EXIT_OK"),
    ('load-report-hides-the-report', CLI, '    print(text)\n    assert text, f"a load report', '    assert text, f"a load report'),
    ('load-report-ignores-run-hooks', CLI, "build_load_report(project_folder(Path.cwd(), arguments.project_dir), timeout)", "build_load_report(project_folder(Path.cwd(), arguments.project_dir), None)"),
    ('load-report-ignores-the-folder-argument', CLI, "project_folder(Path.cwd(), arguments.project_dir)", "project_folder(Path.cwd(), \".\")"),
    ('load-report-not-routed', CLI, 'if command == ["load-report"]:', 'if command == ["load-report-off"]:'),
)
