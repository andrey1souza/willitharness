STATS_TESTS = ("tests/unit", "tests/golden", "tests/property")
INTERVALS = "src/willitharness/intervals.py"
VERDICT = "src/willitharness/verdict.py"

STATS_MUTANTS = (
    ("min-runs-5-to-1", VERDICT, "MIN_RUNS = 5", "MIN_RUNS = 1"),
    ("z-1.96-to-1.0", INTERVALS, "WILSON_Z = 1.96", "WILSON_Z = 1.0"),
    (
        "swap-low-and-high",
        INTERVALS,
        "low, high = difference - lower_reach, difference + upper_reach",
        "low, high = difference + upper_reach, difference - lower_reach",
    ),
    (
        "remove-wilson-clamp",
        INTERVALS,
        "low = min(max(0.0, center - half_width), proportion)",
        "low = center - half_width",
    ),
    ("lower-bound-above-zero-to-at-least-zero", VERDICT, "if low > 0 else", "if low >= 0 else"),
    (
        "swap-first-higher-and-first-lower",
        VERDICT,
        "Verdict.FIRST_HIGHER if low > 0 else Verdict.FIRST_LOWER if high < 0",
        "Verdict.FIRST_LOWER if low > 0 else Verdict.FIRST_HIGHER if high < 0",
    ),
    (
        "difference-interval-unordered",
        INTERVALS,
        '{low}, {high}"\n    return low, high\n',
        '{low}, {high}"\n    return high, low\n',
    ),
    (
        "difference-without-negation-on-swap",
        INTERVALS,
        "difference = first_rate - second_rate",
        "difference = abs(first_rate - second_rate)",
    ),
)

PLAN_TESTS = ("tests/unit/test_plan_unit.py", "tests/gates/test_plan_gate.py")
PLAN = "src/willitharness/plan.py"

PLAN_MUTANTS = (
    ("default-reps-20-to-10", PLAN, "DEFAULT_REPS = 20", "DEFAULT_REPS = 10"),
    ("max-retries-2-to-3", PLAN, "MAX_RETRIES = 2", "MAX_RETRIES = 3"),
    ("min-probe-runs-3-to-1", PLAN, "MIN_PROBE_RUNS = 3", "MIN_PROBE_RUNS = 1"),
    ("noise-target-check-inverted", PLAN, "if target != loo_label:", "if target == loo_label:"),
    ("noise-pair-without-loo-arm-allowed", PLAN, "        if not leave_one_out:\n", "        if False:\n"),
    ("run-cap-may-exceed-budget", PLAN, "if run_cap > budget:", "if run_cap > budget * 2:"),
    ("two-loo-arms-allowed", PLAN, "if len(leave_one_out) > 1:", "if len(leave_one_out) > 2:"),
    ("repeated-labels-allowed-once", PLAN, "labels.count(label) > 1", "labels.count(label) > 2"),
)

FAKE_AGENT_TESTS = ("tests/gates/test_fakeagent.py",)
FAKE_AGENT = "src/willitharness/fakeagent.py"

FAKE_AGENT_MUTANTS = (
    ("fallback-file-always-read", FAKE_AGENT, "chosen = primary or fallback", "chosen = primary + fallback"),
    ("recall-ignored", FAKE_AGENT, "values[0] if values and draw < behavior.recall else", "values[0] if values else"),
    ("walk-passes-the-boundary", FAKE_AGENT, "while chain[-1] != boundary:", "while chain[-1] != chain[-1].parent:"),
    ("seed-ignored", FAKE_AGENT, 'random.Random(f"{behavior.seed}:{run_index}")', "random.Random()"),
    ("seed-message-changed", FAKE_AGENT, '"seed required; pass --seed N"', '"seed needed"'),
    ("claude-file-not-read", FAKE_AGENT, 'CONTEXT_FILE = "CLAUDE.md"', 'CONTEXT_FILE = "CLAUDE.txt"'),
)

MODULES = {
    "stats": (STATS_TESTS, STATS_MUTANTS),
    "plan": (PLAN_TESTS, PLAN_MUTANTS),
    "fakeagent": (FAKE_AGENT_TESTS, FAKE_AGENT_MUTANTS),
}
