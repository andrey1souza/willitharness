TESTS = (
    'tests/gates/test_analysis_outcomes.py',
    'tests/gates/test_lifecycle_gate.py',
    'tests/bdd/analysis/test_effect_with_noise.py',
)

SOURCE = 'src/willitharness/cli.py'

MUTANTS = (
    ('analyze-moves-state-without-a-verdict', SOURCE, "    if not has_verdict(analysis):", "    if False:"),
    ('analyze-without-a-verdict-exits-zero', SOURCE, "NO_VERDICT_MESSAGE]), file=sys.stderr)\n        return EXIT_DOMAIN_FAILURE", "NO_VERDICT_MESSAGE]), file=sys.stderr)\n        return EXIT_OK"),
    ('resume-warning-on-the-wrong-state', SOURCE, "if finish_analysis(root, plan) is PlanState.BUDGET_STOPPED:", "if finish_analysis(root, plan) is PlanState.COMPLETE:"),
    ('resume-warning-never-printed', SOURCE, "if finish_analysis(root, plan) is PlanState.BUDGET_STOPPED:", "if finish_analysis(root, plan) is None:"),
    ('pooled-flag-ignored', SOURCE, "read_reach(folder), arguments.pooled), True)", "read_reach(folder), False), True)"),
    ('analyze-skips-the-state-gate', SOURCE, "        analyze_gate(root, plan)\n        folder = lifecycle_dir(root, plan)", "        folder = lifecycle_dir(root, plan)"),
    ('analyze-hides-the-report', SOURCE, '    print("\\n".join(report_lines(analysis)))', '    pass'),
    ('analysis-error-not-caught', SOURCE, "except (PathOutsideRoot, PlanError, LifecycleRefused, AnalysisError) as error:\n        print(str(error), file=sys.stderr)\n        return EXIT_DOMAIN_FAILURE\n    print(\"\\n\".join(report_lines", "except (PathOutsideRoot, PlanError, LifecycleRefused) as error:\n        print(str(error), file=sys.stderr)\n        return EXIT_DOMAIN_FAILURE\n    print(\"\\n\".join(report_lines"),
)
