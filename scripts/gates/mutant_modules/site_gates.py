SOURCE = 'scripts/site/gates.py'

TESTS = (
    'tests/site/test_site_gates.py',
)

MUTANTS = (
    ('duplicate-id-allowed', SOURCE, 'if identifier in seen:', 'if False:'),
    ('alt-not-required', SOURCE, 'if tag.name == "img" and "alt" not in tag.attributes:', 'if False:'),
    ('external-anchor-flagged', SOURCE, '(tag.attributes.get("href") if tag.name != "a" else None)', 'tag.attributes.get("href")'),
    ('caption-not-required', SOURCE, 'if tag.name == "table" and "<caption>" not in html]', 'if tag.name == "table" and False]'),
    ('second-h1-allowed', SOURCE, 'if len(top) != FIRST_LEVEL:', 'if len(top) < FIRST_LEVEL:'),
    ('heading-skip-allowed', SOURCE, 'if level > previous + MAX_LEVEL_STEP:', 'if False:'),
    ('anchor-unchecked', SOURCE, 'if anchor and anchor not in identifiers.get(target, set()):', 'if False:'),
    ('missing-target-unchecked', SOURCE, 'if target not in files:', 'if False:'),
    ('backticks-kept-in-coverage', SOURCE, 'if text.replace(BACKTICK, "") not in shown', 'if text not in shown'),
    ('citation-range-unchecked', SOURCE, 'if not 1 <= line <= len(lines):', 'if False:'),
    ('citation-text-unchecked', SOURCE, 'if key not in lines[line - 1].replace(BACKTICK, ""):', 'if False:'),
    ('list-items-untraced', SOURCE, 'elements += [found for found in SOURCE_ELEMENT.findall(html) if found[0] == "li"]', 'elements += []'),
    ('every-tuple-is-a-mutant-table', SOURCE, 'target.id == "MUTANTS"', 'True'),
    ('live-tests-collected', SOURCE, '"-o", "addopts=", "-m", "not live")', '"-o", "addopts=")'),
    ('survivors-accepted', SOURCE, 'if total != actual or killed != total:', 'if total != actual:'),
    ('failed-record-accepted', SOURCE, 'if row["status"] != "passed":', 'if False:'),
    ('count-drift-accepted', SOURCE, 'elif numbers[0] != actual:', 'elif False:'),
    ('status-not-checked', SOURCE, 'problems += status_problems(data["gates"]["rows"], counts)', 'problems += []'),
    ('built-files-not-scanned-for-comments', SOURCE, 'brand_gates.comment_problems({**sources, **files})', 'brand_gates.comment_problems(sources)'),
    ('template-numbers-not-scanned', SOURCE, 'sources[render.TEMPLATE_FILE])', '"")'),
    ('claims-always-true', SOURCE, 'claims = data["live"]["claims"]', 'claims = {phrase: True for phrase in brand_gates.HOLD_BACK_PHRASES}'),
)
