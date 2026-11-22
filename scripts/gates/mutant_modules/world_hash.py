TESTS = (
    'tests/unit/test_lifecycle_ids_unit.py',
    'tests/unit/test_warning_rules_unit.py',
    'tests/gates/test_contract_sentences.py',
    'tests/gates/test_analysis_outcomes.py',
    'tests/gates/test_lifecycle_gate.py',
)

SOURCE = 'src/willitharness/lifecycle.py'
WARNINGS = 'src/willitharness/warning_rules.py'
ANALYSIS = 'src/willitharness/analysis.py'
CHECKS = 'scripts/gates/repo_checks.py'
WORLD = 'src/willitharness/world.py'
FACTS = 'src/willitharness/world_facts.py'

MUTANTS = (
    ('claim-stores-no-world-hash', SOURCE, 'begin_run(folder, job, claimed_world_hash(site.world_dir))', 'begin_run(folder, job, UNKNOWN_WORLD)'),
    ('claim-stores-the-validated-hash-not-the-files', WORLD, '    current = world_hash(world_dir)', '    current = stored_hash(world_dir.parent, world_dir)'),
    ('begin-run-drops-the-world-hash', SOURCE, 'RunState.STARTED, {}, 0.0, world_hash=world_hash)', 'RunState.STARTED, {}, 0.0)'),
    ('world-warning-needs-three-worlds', WARNINGS, 'if len(hashes) > 1]', 'if len(hashes) > 2]'),
    ('world-warning-counts-unknown-worlds', WARNINGS, '        if run.world_hash != UNKNOWN_WORLD:\n', '        if True:\n'),
    ('world-warning-pools-all-cells', WARNINGS, 'worlds[(run.arm, run.task)].add(run.world_hash)', 'worlds[("", "")].add(run.world_hash)'),
    ('analysis-drops-the-world-warning', ANALYSIS, '*world_warnings(inputs.records, inputs.world), ', ''),
    ('analysis-ignores-the-world-facts', ANALYSIS, '*world_warnings(inputs.records, inputs.world), ', '*world_warnings(inputs.records), '),
    ('left-world-warning-never-fires', WARNINGS, 'if validated is not None and run.world_hash not in (UNKNOWN_WORLD, validated):', 'if False:'),
    ('left-world-warning-counts-unhashed-runs', WARNINGS, 'run.world_hash not in (UNKNOWN_WORLD, validated)', 'run.world_hash != validated'),
    ('left-world-warning-without-a-validated-hash', WARNINGS, 'if validated is not None and run.world_hash', 'if run.world_hash'),
    ('no-hash-count-off-by-one', WARNINGS, 'NO_HASH_WARNING.format(n=unhashed)', 'NO_HASH_WARNING.format(n=unhashed + 1)'),
    ('no-hash-count-never-fires', WARNINGS, 'if unhashed else []', 'if False else []'),
    ('no-hash-count-counts-hashed-runs', WARNINGS, 'if run.world_hash == UNKNOWN_WORLD)\n    lines = [NO_HASH', 'if run.world_hash != UNKNOWN_WORLD)\n    lines = [NO_HASH'),
    ('ended-world-line-never-fires', WARNINGS, 'if world.ended_in_changed_world else []', 'if False else []'),
    ('ended-world-line-always-fires', WARNINGS, 'if world.ended_in_changed_world else []', 'if True else []'),
    ('conclude-forgets-the-changed-world', SOURCE, 'ended_in_changed_world=world_changed(site.root, site.world_dir)', 'ended_in_changed_world=False'),
    ('world-facts-forgets-the-ended-fact', FACTS, 'resume is not None and resume.ended_in_changed_world', 'False'),
    ('world-facts-forgets-the-validated-hash', FACTS, 'validated = stored_hash(root, world_dir) if world_dir.is_dir() else None', 'validated = None'),
    ('conclude-waits-for-a-validated-world', SOURCE, '        if state is not PlanState.RUNNING:\n            return state\n        pending', '        if state is not PlanState.RUNNING or world_changed(site.root, site.world_dir):\n            return state\n        pending'),
    ('contract-sentences-not-checked', CHECKS, 'for sentence in CONTRACT_SENTENCES if sentence not in text]', 'for sentence in CONTRACT_SENTENCES if False]'),
)
