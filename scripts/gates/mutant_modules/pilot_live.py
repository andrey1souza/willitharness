PLATFORM = "darwin"
TESTS = ("tests/gates/test_pilot_live.py",)
SOURCE = "scripts/gates/pilot_live.py"

MUTANTS = (
    ("reachability-not-loaded", SOURCE, "record_reachability(site, label, Reach.LOADED)", "record_reachability(site, label, Reach.UNKNOWN)"),
    ("report-rows-not-printed", SOURCE, 'print("\\n".join([*report, *lines]))', 'print("\\n".join(lines))'),
    ("pass-line-always-printed", SOURCE, "print(PASS_LINE if code == EXIT_PASSED else NOT_REPRODUCED_MESSAGE)", "print(PASS_LINE)"),
    ("refusal-exits-one", SOURCE, "        return EXIT_REFUSED", "        return EXIT_FAILED"),
    ("spend-check-dropped", SOURCE, "worst = check_spend(len(ARMS) * len(TASKS), arguments.reps, RUN_CAP_USD, COST_CAP_USD)", "worst = 0.0"),
    ("cells-counted-per-arm-only", SOURCE, "check_spend(len(ARMS) * len(TASKS), arguments.reps", "check_spend(len(ARMS), arguments.reps"),
    ("identical-flag-not-written", SOURCE, "write_pilot_project(Path(directory).resolve(), arguments.reps, arguments.identical)", "write_pilot_project(Path(directory).resolve(), arguments.reps, False)"),
    ("identical-flag-not-judged", SOURCE, "lines = verdict_lines(report, arguments.reps, arguments.identical)", "lines = verdict_lines(report, arguments.reps, False)"),
    ("model-not-passed", SOURCE, "run_pilot_project(root, arguments.model, runner_factory)", 'run_pilot_project(root, "haiku", runner_factory)'),
    ("task-not-set-up", SOURCE, "RunSetup(site, (task.name,), claude_agent.RUN_TIMEOUT_SECONDS)", "RunSetup(site, (), claude_agent.RUN_TIMEOUT_SECONDS)"),
    ("cost-not-read", SOURCE, "cost = float(spent(load_records(lifecycle_dir(root, site.plan))))", "cost = 0.0"),
    ("cost-of-first-task-only", SOURCE, "        total += cost", "        total = cost"),
    ("report-of-last-task-only", SOURCE, "        report += lines", "        report = lines"),
    ("missing-agent-uncaught", SOURCE, "except (AgentUnavailable, AnalysisError,", "except (AnalysisError,"),
    ("world-not-validated", SOURCE, "    store_validation(root, site.world_dir, validate_world(site.world_dir))\n", ""),
    ("warnings-off", SOURCE, "report_lines(analyze_plan(AnalysisInput(plan, load_records(folder), read_reach(folder), False), True))", "report_lines(analyze_plan(AnalysisInput(plan, load_records(folder), read_reach(folder), False), False))"),
)
