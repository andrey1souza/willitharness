from willitharness.vocabulary import Reach

MIN_PROBE_RUNS = 3


def classify(runs: int, target_hits: int, control_hits: int) -> Reach:
    assert runs >= 0, f"runs must not be negative, got {runs}"
    assert 0 <= target_hits <= runs and 0 <= control_hits <= runs, (
        f"hits must lie between 0 and runs: target {target_hits}, control {control_hits}, runs {runs}"
    )
    if runs < MIN_PROBE_RUNS or control_hits > 0:
        result = Reach.UNKNOWN
    elif target_hits == runs:
        result = Reach.LOADED
    elif target_hits == 0:
        result = Reach.MASKED
    else:
        result = Reach.UNKNOWN
    assert result is not Reach.LOADED or (runs >= MIN_PROBE_RUNS and control_hits == 0 and target_hits == runs), (
        f"P3 broken: {result} for runs {runs}, target {target_hits}, control {control_hits}"
    )
    assert result is not Reach.MASKED or (runs >= MIN_PROBE_RUNS and control_hits == 0 and target_hits == 0), (
        f"P3 broken: {result} for runs {runs}, target {target_hits}, control {control_hits}"
    )
    return result


def loo_arm_valid(loo_probe: Reach) -> bool:
    assert loo_probe in Reach, f"unknown reach {loo_probe!r}"
    result = loo_probe is Reach.LOADED
    assert result == (loo_probe == Reach.LOADED.value), f"P4 broken: {loo_probe} gave {result}"
    assert result or loo_probe is not Reach.LOADED, f"P4 broken: a Loaded LOO probe gave {result}"
    return result
