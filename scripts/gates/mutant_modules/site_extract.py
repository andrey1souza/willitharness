SOURCE = 'scripts/site/extract.py'

TESTS = (
    'tests/site/test_extract.py',
)

MUTANTS = (
    ('wrapped-bullet-lines-dropped', SOURCE, 'elif line.startswith(CONTINUATION_PREFIX) and bullets:', 'elif False:'),
    ('section-never-ends', SOURCE, 'if line.startswith(SECTION_PREFIX):\n            break', 'if False:\n            break'),
    ('line-numbers-off-by-one', SOURCE, 'start=first + 1', 'start=first'),
    ('derived-properties-kept', SOURCE, 'for bullet in section_bullets(lines, DECISIONS_HEADING) if DECISION_BULLET.match(bullet["text"])]', 'for bullet in section_bullets(lines, DECISIONS_HEADING)]'),
    ('answer-fallback-dropped', SOURCE, 'result = RESULT_TEXT.search(rest) or AFTER_QUESTION.match(rest)', 'result = RESULT_TEXT.search(rest)'),
    ('duplicate-json-line-allowed', SOURCE, 'assert len(found) == 1,', 'assert len(found) >= 1,'),
    ('description-is-the-blank-line', SOURCE, 'description = next(line for line in lines[1:] if line.strip())', 'description = lines[1]'),
    ('limits-heading-renamed', SOURCE, 'LIMITS_HEADING = "## Honest limits"', 'LIMITS_HEADING = "## Working on it"'),
    ('record-moved-to-the-committed-folder', SOURCE, 'GATE_STATUS_FILE = "build/gate_status.json"', 'GATE_STATUS_FILE = "site/data/gate_status.json"'),
    ('record-date-kept', SOURCE, '"command": document["command"], "rows": rows', '"command": document["command"], "date": document["date"], "rows": rows'),
    ('run-follows-history-unchecked', SOURCE, 'assert document["run"] == len(history) + 1,', 'assert True,'),
    ('history-cites-the-run-line', SOURCE, "f'\"when\": {json.dumps(item[\"when\"])}'", "f'\"run\": {item[\"run\"]}'"),
    ('explanation-cites-the-first-line', SOURCE, 'explanation = [{"text": text, "line": json_line(lines, json.dumps(text))} for text in document["explanation"]]', 'explanation = [{"text": text, "line": 1} for text in document["explanation"]]'),
)
