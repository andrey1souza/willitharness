SOURCE = 'scripts/gates/docs_freshness.py'

TESTS = (
    'tests/gates/test_docs_freshness.py',
)

MUTANTS = (
    ('version-not-compared', SOURCE, 'if found.group(1) != str(facts[key]):', 'if False:'),
    ('world-range-against-id-count', SOURCE, '"world-rules", re.compile(rf"{WORLD_PREFIX}1 to {WORLD_PREFIX}(\\d+)"), "world_rule_count"', '"world-rules", re.compile(rf"{WORLD_PREFIX}1 to {WORLD_PREFIX}(\\d+)"), "id_count"'),
    ('id-list-subset-accepted', SOURCE, 'if listed != facts["ids"]:', 'if not listed <= facts["ids"]:'),
    ('resolved-issue-called-open', SOURCE, 'if int(found.group(1)) in facts["resolved_issues"]:', 'if False:'),
    ('missing-code-claim-always-checked', SOURCE, 'if not facts["has_code"]:\n        return []', 'if False:\n        return []'),
    ('unknown-flag-accepted', SOURCE, 'unknown = sorted(set(FLAG.findall(statement)) - known)', 'unknown = []'),
    ('check-dependency-ignored', SOURCE, 'if CHECK_PHRASES[target] not in found.group(1)]', 'if False]'),
    ('unknown-make-target-accepted', SOURCE, 'if target not in facts["make_targets"]', 'if False'),
    ('unnamed-dependency-tolerated', SOURCE, 'assert not unnamed,', 'assert True,'),
    ('summary-count-unchecked', SOURCE, 'if int(count) != expected:', 'if False:'),
    ('summary-total-unchecked', SOURCE, 'if total != facts["task_count"]:', 'if False:'),
    ('header-heading-mismatch-ignored', SOURCE, 'assert facts["task_count"] == facts["task_heading_count"], (', 'assert True, ('),
    ('research-directory-checked', SOURCE, 'if path not in skipped and HISTORICAL_DIRECTORY not in path.parents', 'if path not in skipped'),
    ('frozen-contract-checked', SOURCE, 'HISTORICAL_FILES = (DOCS_DIRECTORY / "contract-v0.1.md",)', 'HISTORICAL_FILES = ()'),
    ('contract-checked-against-itself', SOURCE, 'SOURCE_FILES = (CONTRACT_FILE,)', 'SOURCE_FILES = ()'),
    ('every-gate-counted-live', SOURCE, 'sum(1 for _, live in gates if live)', 'len(gates)'),
    ('outline-not-counted', SOURCE, 'Scenario(?: Outline)?:', 'Scenario:'),
    ('glob-reference-checked', SOURCE, 'if "*" not in reference and not beside.exists() and not (root / reference).exists():', 'if not beside.exists() and not (root / reference).exists():'),
    ('reference-beside-document-only', SOURCE, 'and not beside.exists() and not (root / reference).exists():', 'and not beside.exists():'),
    ('command-paths-unchecked', SOURCE, 'for pattern in (FILE_REFERENCE, COMMAND_PATH)', 'for pattern in (FILE_REFERENCE,)'),
    ('modules-unchecked', SOURCE, 'if not module_file.is_file() and not package_main.is_file():', 'if False:'),
    ('marker-section-never-ends', SOURCE, 'section = marker.group(1) if marker else None', 'section = section'),
    ('marker-exempts-nothing', SOURCE, 'kept = ["" if number in planned else line', 'kept = [line'),
    ('unknown-task-accepted', SOURCE, 'if task not in facts["task_ids"] and', 'if False and'),
    ('malformed-marker-accepted', SOURCE, 'for line, _ in matches_with_lines(text, MALFORMED_MARKER)]', 'for line, _ in []]'),
)
