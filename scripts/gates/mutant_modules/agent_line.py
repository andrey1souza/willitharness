PLATFORM = "darwin"
TESTS = (
    'tests/unit/test_agent_line_unit.py',
    'tests/gates/test_analysis_outcomes.py',
    'tests/gates/test_detectors_gate.py',
)

SOURCE = 'src/willitharness/agent_line.py'
STREAM = 'src/willitharness/stream.py'
CLI = 'src/willitharness/cli.py'

MUTANTS = (
    ('several-models-read-as-one', SOURCE, 'label = "models" if len(shown) > 1 else "model"', 'label = "model"'),
    ('duplicate-models-listed', SOURCE, 'tuple(sorted(set(models)))', 'tuple(sorted(models))'),
    ('models-in-first-seen-order', SOURCE, 'tuple(sorted(set(models)))', 'tuple(dict.fromkeys(models))'),
    ('absent-model-hidden', SOURCE, 'or (UNKNOWN,)', 'or ("",)'),
    ('absent-version-hidden', SOURCE, '{version or UNKNOWN}', '{version}'),
    ('empty-version-accepted', SOURCE, 'result = version if isinstance(version, str) and version else None', 'result = version if isinstance(version, str) else None'),
    ('only-the-first-transcript-read', SOURCE, 'sorted(runs.rglob(TRANSCRIPT_GLOB))', 'sorted(runs.rglob(TRANSCRIPT_GLOB))[:1]'),
    ('every-stored-file-read-as-a-transcript', SOURCE, 'TRANSCRIPT_GLOB = TRANSCRIPT_NAME.format(attempt="*")', 'TRANSCRIPT_GLOB = "*"'),
    ('model-read-from-any-event', STREAM, 'if event.get("type") == SYSTEM_EVENT and event.get("subtype") == INIT_SUBTYPE]', 'if True]'),
    ('model-of-the-last-init', STREAM, 'found = next((model for model in models if', 'found = next((model for model in reversed(models) if'),
    ('model-field-renamed', STREAM, 'MODEL_FIELD = "model"', 'MODEL_FIELD = "name"'),
    ('agent-line-not-printed', CLI, '[read_agent_line(root, plan), *report_lines(analysis)]', '[*report_lines(analysis)]'),
    ('agent-line-printed-last', CLI, '[read_agent_line(root, plan), *report_lines(analysis)]', '[*report_lines(analysis), read_agent_line(root, plan)]'),
)
