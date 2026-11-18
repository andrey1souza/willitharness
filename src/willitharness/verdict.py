from willitharness.counts import Counts
from willitharness.intervals import WILSON_Z, difference_interval_at
from willitharness.vocabulary import NoiseStatus, Verdict

MIN_RUNS = 5
FLIP_FIXED_VERDICTS = frozenset({Verdict.INCONCLUSIVE_SMALL_N, Verdict.INCONCLUSIVE})
FLIPPED_VERDICTS = {Verdict.FIRST_HIGHER: Verdict.FIRST_LOWER, Verdict.FIRST_LOWER: Verdict.FIRST_HIGHER}
NOISE_STATUS_BY_VERDICT = {
    Verdict.INCONCLUSIVE_SMALL_N: NoiseStatus.NOISE_UNMEASURED,
    Verdict.FIRST_HIGHER: NoiseStatus.NOISE_FLOOR_TOO_HIGH,
    Verdict.FIRST_LOWER: NoiseStatus.NOISE_FLOOR_TOO_HIGH,
    Verdict.INCONCLUSIVE: NoiseStatus.NOISE_OK,
}


def verdict_from_interval(low: float, high: float) -> Verdict:
    assert low <= high, f"an interval needs low <= high, got {low} and {high}"
    assert -1.0 <= low and high <= 1.0, f"a difference interval lies within [-1, 1], got {low} and {high}"
    return Verdict.FIRST_HIGHER if low > 0 else Verdict.FIRST_LOWER if high < 0 else Verdict.INCONCLUSIVE


def verdict_of(first: Counts, second: Counts) -> Verdict:
    assert first.runs >= 0 and second.runs >= 0, f"run counts must not be negative: {first.runs}, {second.runs}"
    assert WILSON_Z > 0, f"WILSON_Z must be above 0, got {WILSON_Z}"
    return verdict_at(first, second, WILSON_Z)


def verdict_at(first: Counts, second: Counts, z: float) -> Verdict:
    assert first.runs >= 0 and second.runs >= 0, f"run counts must not be negative: {first.runs}, {second.runs}"
    assert MIN_RUNS >= 1, f"MIN_RUNS must keep intervals defined, got {MIN_RUNS}"
    small = min(first.runs, second.runs) < MIN_RUNS
    if small:
        result = Verdict.INCONCLUSIVE_SMALL_N
    else:
        low, high = difference_interval_at(first, second, z)
        result = verdict_from_interval(low, high)
    assert (result is Verdict.INCONCLUSIVE_SMALL_N) == small, (
        f"V2 broken: small-n rule gave {result} for runs {first.runs}, {second.runs}"
    )
    assert small or result is not Verdict.INCONCLUSIVE_SMALL_N, f"V2 broken: enough runs gave {result}"
    return result


def flip(verdict: Verdict) -> Verdict:
    result = FLIPPED_VERDICTS.get(verdict, verdict)
    assert (result is verdict) == (verdict in FLIP_FIXED_VERDICTS), (
        f"flip must fix exactly two verdicts: {verdict} gave {result}"
    )
    assert FLIPPED_VERDICTS.get(result, result) is verdict, f"flip must be an involution: {verdict} gave {result}"
    return result


def noise_status_of(noise_first: Counts, noise_second: Counts) -> NoiseStatus:
    assert noise_first.runs >= 0 and noise_second.runs >= 0, (
        f"run counts must not be negative: {noise_first.runs}, {noise_second.runs}"
    )
    verdict = verdict_of(noise_first, noise_second)
    result = NOISE_STATUS_BY_VERDICT[verdict]
    assert (result is NoiseStatus.NOISE_OK) == (verdict is Verdict.INCONCLUSIVE), (
        f"V6 broken: verdict {verdict} gave {result}"
    )
    assert min(noise_first.runs, noise_second.runs) >= MIN_RUNS or result is NoiseStatus.NOISE_UNMEASURED, (
        f"V6 broken: unmeasured noise pair {noise_first.runs}, {noise_second.runs} gave {result}"
    )
    return result
