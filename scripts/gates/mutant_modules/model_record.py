TESTS = (
    'tests/unit/test_lifecycle_ids_unit.py',
    'tests/unit/test_warning_rules_unit.py',
    'tests/gates/test_contract_sentences.py',
    'tests/gates/test_analysis_outcomes.py',
    'tests/gates/test_lifecycle_gate.py',
    'tests/bdd/analysis/test_warnings.py',
)

SOURCE = 'src/willitharness/lifecycle.py'
WARNINGS = 'src/willitharness/warning_rules.py'
ANALYSIS = 'src/willitharness/analysis.py'
CLI = 'src/willitharness/cli.py'

MUTANTS = (
    ('claim-stores-no-model', SOURCE, 'claimed_world_hash(site.world_dir), context.setup.model)', 'claimed_world_hash(site.world_dir), UNKNOWN_MODEL)'),
    ('begin-run-drops-the-model', SOURCE, 'record = started_record(job, world_hash, model)', 'record = started_record(job, world_hash, UNKNOWN_MODEL)'),
    ('started-record-drops-the-model', SOURCE, 'world_hash=world_hash, model=model)', 'world_hash=world_hash)'),
    ('run-command-sets-up-no-model', CLI, 'arguments.timeout_seconds, run_model(arguments, setup_runners))', 'arguments.timeout_seconds)'),
    ('fake-agent-records-the-claude-model', CLI, 'model = arguments.model if arguments.agent in setup_runners else arguments.agent', 'model = arguments.model'),
    ('analysis-drops-the-model-warning', ANALYSIS, '*model_warnings(inputs.records), ', ''),
    ('model-mix-needs-three-models', WARNINGS, 'if len(runs) > 1:', 'if len(runs) > 2:'),
    ('model-mix-never-fires', WARNINGS, 'if len(runs) > 1:', 'if False:'),
    ('model-mix-counts-unnamed-runs-as-a-model', WARNINGS, '    unnamed = runs.pop(UNKNOWN_MODEL, 0)\n', '    unnamed = runs[UNKNOWN_MODEL]\n'),
    ('model-mix-counts-records-not-runs', WARNINGS, 'Counter(run.model for run in latest_by_run(records).values())', 'Counter(run.model for run in records)'),
    ('model-mix-lists-no-run-counts', WARNINGS, 'f"{model} {count} runs" for', 'f"{model}" for'),
    ('model-mix-miscounts-the-models', WARNINGS, 'MODEL_MIX_WARNING.format(n=len(runs),', 'MODEL_MIX_WARNING.format(n=len(runs) + 1,'),
    ('no-model-count-off-by-one', WARNINGS, 'NO_MODEL_WARNING.format(n=unnamed)', 'NO_MODEL_WARNING.format(n=unnamed + 1)'),
    ('no-model-count-never-fires', WARNINGS, '    if unnamed:\n', '    if False:\n'),
    ('no-model-count-always-fires', WARNINGS, '    if unnamed:\n', '    if True:\n'),
)
