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
    ('planned-command-allowed-everywhere', SOURCE, 'name in PLANNED_COMMANDS and path in PLANNED_DOCUMENTS', 'name in PLANNED_COMMANDS'),
    ('built-planned-command-ignored', SOURCE, 'if known is not None and name in PLANNED_COMMANDS:', 'if False:'),
    ('check-dependency-ignored', SOURCE, 'if CHECK_PHRASES[target] not in found.group(1)]', 'if False]'),
    ('unknown-make-target-accepted', SOURCE, 'if target not in facts["make_targets"]', 'if False'),
    ('unnamed-dependency-tolerated', SOURCE, 'assert not unnamed,', 'assert True,'),
    ('planned-documents-skip-nothing', SOURCE, 'if path in PLANNED_DOCUMENTS:\n        return errors', 'if False:\n        return errors'),
    ('glob-reference-checked', SOURCE, 'if "*" in reference:\n            continue', 'if False:\n            continue'),
    ('reference-beside-document-only', SOURCE, 'if not beside.is_file() and not (root / reference).is_file():', 'if not beside.is_file():'),
    ('summary-count-unchecked', SOURCE, 'if int(count) != expected:', 'if False:'),
    ('summary-total-unchecked', SOURCE, 'if total != facts["task_count"]:', 'if False:'),
    ('header-heading-mismatch-ignored', SOURCE, 'assert facts["task_count"] == facts["task_heading_count"], (', 'assert True, ('),
    ('research-directory-checked', SOURCE, 'if path not in skipped and HISTORICAL_DIRECTORY not in path.parents', 'if path not in skipped'),
    ('frozen-contract-checked', SOURCE, 'HISTORICAL_FILES = (DOCS_DIRECTORY / "contract-v0.1.md",)', 'HISTORICAL_FILES = ()'),
    ('contract-checked-against-itself', SOURCE, 'SOURCE_FILES = (CONTRACT_FILE,)', 'SOURCE_FILES = ()'),
    ('every-gate-counted-live', SOURCE, 'sum(1 for _, live in gates if live)', 'len(gates)'),
    ('outline-not-counted', SOURCE, 'Scenario(?: Outline)?:', 'Scenario:'),
)
