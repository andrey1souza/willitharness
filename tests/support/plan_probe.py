TARGET = "ZQ-8841-lumen"
CONTROL = "purple-giraffe-91"
PROBE_SEED = 3
PROBE_RUNS = 3


def plan_probe_arguments(directory, arm, plan_file):
    assert arm and plan_file, f"plan_probe_arguments needs an arm and a plan file, got {arm!r} and {plan_file!r}. Fix: pass both."
    return [
        "probe", "--agent", "fake", "--directory", str(directory), "--boundary", str(directory),
        "--runs", str(PROBE_RUNS), "--seed", str(PROBE_SEED), "--target-token", TARGET, "--control-token", CONTROL,
        "--plan", plan_file, "--arm", arm,
    ]
