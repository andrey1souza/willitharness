TESTS = (
    'tests/gates/test_report_golden.py',
)

REPORT = 'src/willitharness/report.py'
CLI = 'src/willitharness/cli.py'

MUTANTS = (
    ('report-skips-the-analyzed-check', REPORT, "    if state not in FINAL_STATES:", "    if False:"),
    ('report-skips-the-abort-refusal', REPORT, "    if state is PlanState.ABORTED:", "    if False:"),
    ('report-refusal-text-changed', REPORT, 'NO_VERDICTS_REFUSAL = "no verdicts yet; run: willitharness analyze"', 'NO_VERDICTS_REFUSAL = "no verdicts yet"'),
    ('report-refusal-exits-zero', CLI, '        return EXIT_DOMAIN_FAILURE\n    print(text, end="")', '        return EXIT_OK\n    print(text, end="")'),
    ('report-guard-refusal-not-caught', CLI, "AnalysisError, DecideRefused, ReportRefused)", "AnalysisError, ReportRefused)"),
    ('report-plan-error-not-caught', CLI, "(PathOutsideRoot, PlanError, AnalysisError, DecideRefused, ReportRefused)", "(PathOutsideRoot, AnalysisError, DecideRefused, ReportRefused)"),
    ('report-adds-a-line-break', CLI, 'print(text, end="")', "print(text)"),
    ('report-not-routed', CLI, 'if command == ["report"]:', 'if command == ["report-off"]:'),
    ('report-folder-read-as-file', REPORT, "(target, PLAN_FILE) if target.is_dir() else (cwd, argument)", "(cwd, argument)"),
    ('report-saturated-flag-always-false', REPORT, 'str(saturated).lower()', '"false"'),
    ('report-saturated-never-read', REPORT, "SATURATED_WARNING.format(arm=row.first, task=row.task) in analysis.warnings", "False"),
    ('report-caveat-dropped', REPORT, "caveat = item.decision is Decision.DELETE_CANDIDATE and item.effect is EffectResult.NO_MEASURABLE_EFFECT", "caveat = False"),
    ('report-caveat-on-every-delete-candidate', REPORT, " and item.effect is EffectResult.NO_MEASURABLE_EFFECT", ""),
    ('report-noise-message-dropped', REPORT, "result = [*lines, f\"{CONTINUATION}{row.message}.\"] if row.message else lines", "result = lines"),
    ('report-limit-dropped', REPORT, '    "The result covers tasks written by the plan author. Your real tasks can differ.",\n', ""),
    ('report-isolation-limit-dropped', REPORT, '    "The result covers the isolation flags used. Effect runs use the sandbox of Claude and have no network.",\n', ""),
    ('report-counts-meaning-dropped', REPORT, "The counts are attempts, not executed commands.", "The counts are runs."),
    ('report-cost-dropped', REPORT, 'f"Total cost: ${data.cost_usd:.2f}."', '"Total cost: $0.00."'),
    ('report-warnings-dropped', REPORT, "shown = analysis.warnings or (NO_WARNINGS_LINE,)", "shown = (NO_WARNINGS_LINE,)"),
    ('report-side-effects-always-unmeasured', REPORT, "if every_arm_has_runs else", "if False else"),
    ('report-side-effects-ignore-missing-arms', REPORT, "set(calls) == {arm.label for arm in plan.arms} and len(calls) >= MIN_ARMS", "True"),
    ('report-reach-dropped', REPORT, 'f"{BULLET}Arm {rule}: {reach}."', 'f"{BULLET}Arm {rule}."'),
    ('report-completed-noise-from-the-target-row', REPORT, "{(row.task, row.second): row.noise for row in analysis.rows if row.outcome == COMPLETED_OUTCOME}", "{(row.task, row.second): row.noise for row in analysis.rows if row.outcome == TARGET_OUTCOME}"),
)
