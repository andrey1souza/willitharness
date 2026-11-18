TESTS = ("tests/gates/test_run_live.py",)
SOURCE = "scripts/gates/run_live.py"

MUTANTS = (
    ("usable-count-ignored", SOURCE, "if usable != REPS or cost > COST_CAP_USD:", "if cost > COST_CAP_USD:"),
    ("not-proven-exits-zero", SOURCE, "        print(NOT_PROVEN_MESSAGE)\n        return EXIT_FAILED", "        print(NOT_PROVEN_MESSAGE)\n        return EXIT_PASSED"),
    ("pass-line-changed", SOURCE, 'print("GATE G3.10 PASS")', 'print("ok")'),
)
