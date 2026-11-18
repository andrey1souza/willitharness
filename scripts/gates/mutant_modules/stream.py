TESTS = (
    'tests/unit/test_stream_unit.py',
    'tests/gates/test_stream_corpus.py',
    'tests/property/test_stream_fuzz.py',
    'tests/bdd/test_stream_scenarios.py',
)

SOURCE = 'src/willitharness/stream.py'

MUTANTS = (
    ('error-result-counted-usable', SOURCE, 'and result_event.get("is_error") is False\n', 'and result_event.get("is_error") is not True\n'),
    ('budget-subtype-accepted', SOURCE, 'result_event.get("subtype") == SUCCESS_SUBTYPE', 'result_event.get("subtype") is not None'),
    ('cost-above-cap-accepted', SOURCE, 'and 0 <= cost <= run_cap', 'and 0 <= cost'),
    ('cost-at-cap-rejected', SOURCE, 'and 0 <= cost <= run_cap', 'and 0 <= cost < run_cap'),
    ('first-result-wins', SOURCE, 'finished_cleanly(finished[-1], run_cap)', 'finished_cleanly(finished[0], run_cap)'),
    ('needed-denial-ignored', SOURCE, 'not needed_denied,\n        result_event[COST_FIELD]', 'True,\n        result_event[COST_FIELD]'),
    ('denial-voids-attempts-too', SOURCE, 'RunState.RECORDED_USABLE,\n        True,', 'RunState.RECORDED_USABLE,\n        not needed_denied,'),
    ('substring-program-match', SOURCE, 'return any(program in words for program in needed_programs)', 'return any(program in command for program in needed_programs)'),
    ('denials-not-counted', SOURCE, 'denial_count = len(list_of(result_event.get(DENIALS_FIELD)))', 'denial_count = 0'),
    ('commands-dropped-from-unusable', SOURCE, 'record = unusable_record(commands)', 'record = unusable_record(())'),
    ('non-bash-tool-counted', SOURCE, 'entry.get("name") == BASH_TOOL', 'entry.get("name") is not None'),
    ('user-events-issue-commands', SOURCE, 'if event.get("type") == ASSISTANT_EVENT else []', 'else []'),
    ('boolean-cost-accepted', SOURCE, 'and not isinstance(value, bool) and math.isfinite(value)', 'and math.isfinite(value)'),
    ('unreadable-line-error-uncaught', SOURCE, 'UNREADABLE_LINE_ERRORS = (ValueError, TypeError, RecursionError)', 'UNREADABLE_LINE_ERRORS = (ValueError, TypeError)'),
    ('turns-not-recorded', SOURCE, 'turns if isinstance(turns, int) and not isinstance(turns, bool) else NO_TURNS', 'NO_TURNS'),
    ('final-text-dropped', SOURCE, 'text if isinstance(text, str) else "",', '"",'),
    ('attempt-label-changed', SOURCE, 'ATTEMPT_LABEL = "attempts, not executed commands"', 'ATTEMPT_LABEL = "attempts"'),
    ('cost-not-recorded', SOURCE, 'result_event[COST_FIELD],\n        turns', 'NO_COST,\n        turns'),
)
