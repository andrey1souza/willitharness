PLATFORM = "darwin"
TESTS = ("tests/gates/test_run_live.py",)
SOURCE = "scripts/gates/run_live.py"

MUTANTS = (
    ("usable-count-ignored", SOURCE, "if usable != REPS or calls != REPS or cost > COST_CAP_USD:", "if calls != REPS or cost > COST_CAP_USD:"),
    ("not-proven-exits-zero", SOURCE, "        print(NOT_PROVEN_MESSAGE)\n        return EXIT_FAILED", "        print(NOT_PROVEN_MESSAGE)\n        return EXIT_PASSED"),
    ("stub-call-count-ignored", SOURCE, "if usable != REPS or calls != REPS or cost > COST_CAP_USD:", "if usable != REPS or cost > COST_CAP_USD:"),
    ("stub-calls-always-counted", SOURCE, "calls += any(line.split()[:1] == [STUB_COMMAND] for line in lines)", "calls += 1"),
    ("live-world-without-prompt-file", SOURCE, '    (world / "prompts" / f"{TASK_NAME}.txt").write_text(TASK_PROMPT)\n', ""),
    ("pass-line-changed", SOURCE, 'print("GATE G3.10 PASS")', 'print("ok")'),
)
