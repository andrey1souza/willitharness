TESTS = (
    'tests/unit/test_lifecycle_unit.py',
    'tests/gates/test_lifecycle_gate.py',
    'tests/property/test_lifecycle_chaos.py',
    'tests/bdd/test_lifecycle_scenarios.py',
)

SOURCE = 'src/willitharness/lifecycle.py'

MUTANTS = (
    ('world-validation-skipped', SOURCE, '    validated = stored_hash(site.root, site.world_dir) is not None and not world_changed(site.root, site.world_dir)', '    validated = True'),
    ('start-without-validation-check', SOURCE, '    if stored_hash(site.root, site.world_dir) is None:\n        raise LifecycleRefused(WORLD_NOT_VALIDATED)', '    if False:\n        raise LifecycleRefused(WORLD_NOT_VALIDATED)'),
    ('start-on-changed-world', SOURCE, '    if world_changed(site.root, site.world_dir):\n        raise LifecycleRefused(WORLD_CHANGED)', '    if False:\n        raise LifecycleRefused(WORLD_CHANGED)'),
    ('world-validated-kept-after-hash-change', SOURCE, '    validated = stored_hash(site.root, site.world_dir) is not None and not world_changed(site.root, site.world_dir)', '    validated = stored_hash(site.root, site.world_dir) is not None'),
    ('plan-not-sent-back-to-drafted', SOURCE, '    if goal < position:', '    if False:'),
    ('start-with-missing-arm', SOURCE, '    if absent:\n        raise LifecycleRefused(f"no reachability result', '    if False:\n        raise LifecycleRefused(f"no reachability result'),
    ('unknown-reachability-not-recorded', SOURCE, 'if arm.label not in recorded)', 'if recorded.get(arm.label, Reach.UNKNOWN) is Reach.UNKNOWN)'),
    ('count-only-usable-spend', SOURCE, 'if run.state is not RunState.STARTED), Decimal(0))', 'if run.state is RunState.RECORDED_USABLE), Decimal(0))'),
    ('ignore-reserved', SOURCE, 'ledger.reserved = ledger.run_cap * len(in_flight_runs(records))', 'ledger.reserved = Decimal(0)'),
    ('start-without-reserving', SOURCE, 'if cell is None or not context.ledger.reserve():', 'if cell is None:'),
    ('settle-charges-nothing', SOURCE, 'context.ledger.settle(final.cost_usd)', 'context.ledger.settle(0)'),
    ('timeout-not-charged-at-run-cap', SOURCE, 'timed_out_record(started, run_cap) if result.timed_out else judged_record(started, result, run_cap)', 'judged_record(started, result, run_cap)'),
    ('attempts-pass-reps-plus-max-retries', SOURCE, 'if missing[candidate] > 0)', 'if True)'),
    ('one-runner-only', SOURCE, 'MAX_PARALLEL_RUNNERS = 4', 'MAX_PARALLEL_RUNNERS = 1'),
    ('begin-run-outside-running', SOURCE, '    if state is not PlanState.RUNNING:\n        raise LifecycleRefused(f"plan is {state}; a run starts', '    if False:\n        raise LifecycleRefused(f"plan is {state}; a run starts'),
    ('claim-on-changed-world', SOURCE, 'if read_state(folder) is not PlanState.RUNNING or world_changed(site.root, site.world_dir):\n            return None\n        records', 'if read_state(folder) is not PlanState.RUNNING:\n            return None\n        records'),
    ('finished-plan-label-swapped', SOURCE, 'target = PlanState.BUDGET_STOPPED if pending else PlanState.COMPLETE', 'target = PlanState.COMPLETE if pending else PlanState.BUDGET_STOPPED'),
    ('in-flight-runs-dropped-on-abort', SOURCE, 'abort_records(records, plan.run_cap_usd)[len(records):]', 'abort_records(records, plan.run_cap_usd)[len(records):][:0]'),
    ('abort-after-analysis-allowed', SOURCE, '        if state in FINAL_STATES:', '        if False:'),
    ('analyze-allowed-on-aborted-plan', SOURCE, '    if state is PlanState.ABORTED:\n        raise LifecycleRefused(ANALYZE_AFTER_ABORT)', '    if False:\n        raise LifecycleRefused(ANALYZE_AFTER_ABORT)'),
    ('analyze-allowed-while-running', SOURCE, '    if state is PlanState.RUNNING:\n        raise LifecycleRefused(ANALYZE_WHILE_RUNNING)', '    if False:\n        raise LifecycleRefused(ANALYZE_WHILE_RUNNING)'),
    ('complete-may-run-again', SOURCE, 'PlanState.COMPLETE: frozenset({PlanState.ANALYZED, PlanState.ABORTED}),', 'PlanState.COMPLETE: frozenset({PlanState.ANALYZED, PlanState.ABORTED, PlanState.RUNNING}),'),
    ('aborted-plan-may-leave-aborted', SOURCE, 'PlanState.ABORTED: frozenset(),', 'PlanState.ABORTED: frozenset({PlanState.RUNNING}),'),
    ('analyzed-plan-may-be-aborted', SOURCE, 'PlanState.ANALYZED: frozenset({PlanState.REPORTED}),', 'PlanState.ANALYZED: frozenset({PlanState.REPORTED, PlanState.ABORTED}),'),
    ('finish-after-abort-writes-again', SOURCE, 'if started is None or started.state is not RunState.STARTED:', 'if started is None:'),
)
