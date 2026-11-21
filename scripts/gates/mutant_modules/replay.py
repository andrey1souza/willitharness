TESTS = (
    'tests/unit/test_trace_replay_unit.py',
)

SOURCE = 'src/willitharness/lifecycle.py'
REPLAY = 'scripts/gates/trace_replay.py'
FIXTURES = 'scripts/gates/trace_fixtures.py'

MUTANTS = (
    ('replay-conclude-always-complete', SOURCE, '        pending = any(count > 0 for count in runs_to_start(facts, load_records(folder)).values())', '        pending = False'),
    ('replay-ledger-forgets-spent', SOURCE, '    ledger.spent = money_spent(records)', '    ledger.spent = Decimal(0)'),
    ('replay-resume-keeps-old-budget', SOURCE, 'write_resume(folder, ResumeRecord(site.plan.budget_usd, stored.fingerprint, NOT_ENDED))', 'write_resume(folder, ResumeRecord(stored.budget_usd, stored.fingerprint, NOT_ENDED))'),
    ('replay-conclude-ignores-the-budget', SOURCE, '        if pending and not budget_blocks:\n            return state', '        if False:\n            return state'),
    ('replay-never-compares-states', REPLAY, 'reason = reason or ("" if observed == expected_of(state) else "the code state differs from the model state")', 'reason = reason or ""'),
    ('replay-coverage-forgets-abort-in-flight', REPLAY, '([] if aborted_in_flight else [ABORT_IN_FLIGHT])', '[]'),
    ('replay-start-probe-skipped', REPLAY, 'if cell_key(arm) not in startable and claim_next_job', 'if False and claim_next_job'),
    ('replay-stale-fixture-accepted', FIXTURES, '        if header["model_sha256"] != model_digest(root, header["scenario"]):', '        if False:'),
    ('replay-digest-ignores-the-walker', FIXTURES, 'MODEL_FILES = ("WillItHarness.tla", "TraceWalk.tla")', 'MODEL_FILES = ("WillItHarness.tla",)'),
)
