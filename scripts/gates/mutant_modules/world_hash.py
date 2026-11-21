TESTS = (
    'tests/unit/test_lifecycle_ids_unit.py',
    'tests/unit/test_warning_rules_unit.py',
    'tests/gates/test_contract_sentences.py',
)

SOURCE = 'src/willitharness/lifecycle.py'
WARNINGS = 'src/willitharness/warning_rules.py'
ANALYSIS = 'src/willitharness/analysis.py'
CHECKS = 'scripts/gates/repo_checks.py'

MUTANTS = (
    ('claim-stores-no-world-hash', SOURCE, 'begin_run(folder, job, stored_hash(site.root, site.world_dir) or UNKNOWN_WORLD)', 'begin_run(folder, job, UNKNOWN_WORLD)'),
    ('begin-run-drops-the-world-hash', SOURCE, 'RunState.STARTED, {}, 0.0, world_hash=world_hash)', 'RunState.STARTED, {}, 0.0)'),
    ('world-warning-needs-three-worlds', WARNINGS, 'if len(hashes) > 1]', 'if len(hashes) > 2]'),
    ('world-warning-counts-unknown-worlds', WARNINGS, '        if run.world_hash != UNKNOWN_WORLD:\n', '        if True:\n'),
    ('world-warning-pools-all-cells', WARNINGS, 'worlds[(run.arm, run.task)].add(run.world_hash)', 'worlds[("", "")].add(run.world_hash)'),
    ('analysis-drops-the-world-warning', ANALYSIS, '*world_warnings(inputs.records), ', ''),
    ('conclude-waits-for-a-validated-world', SOURCE, '        if state is not PlanState.RUNNING:\n            return state\n        pending', '        if state is not PlanState.RUNNING or world_changed(site.root, site.world_dir):\n            return state\n        pending'),
    ('contract-sentences-not-checked', CHECKS, 'for sentence in CONTRACT_SENTENCES if sentence not in text]', 'for sentence in CONTRACT_SENTENCES if False]'),
)
