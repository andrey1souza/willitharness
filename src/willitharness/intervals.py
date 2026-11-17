import math

from willitharness.counts import Counts

WILSON_Z = 1.96
Interval = tuple[float, float]


def wilson(counts: Counts) -> Interval:
    assert counts.runs >= 1, f"a Wilson interval needs at least one run, got {counts.runs}"
    assert counts.successes <= counts.runs, f"successes {counts.successes} cannot exceed runs {counts.runs}"
    proportion = counts.rate()
    squared_z = WILSON_Z**2
    denominator = 1 + squared_z / counts.runs
    center = (proportion + squared_z / (2 * counts.runs)) / denominator
    spread = proportion * (1 - proportion) / counts.runs + squared_z / (4 * counts.runs**2)
    half_width = WILSON_Z * math.sqrt(spread) / denominator
    low = min(max(0.0, center - half_width), proportion)
    high = max(min(1.0, center + half_width), proportion)
    assert 0.0 <= low <= proportion <= high <= 1.0, f"V5 broken: {low}, {proportion}, {high}"
    return low, high


def difference_interval(first: Counts, second: Counts) -> Interval:
    assert first.runs >= 1, f"the first arm needs at least one run, got {first.runs}"
    assert second.runs >= 1, f"the second arm needs at least one run, got {second.runs}"
    first_rate, second_rate = first.rate(), second.rate()
    first_low, first_high = wilson(first)
    second_low, second_high = wilson(second)
    difference = first_rate - second_rate
    lower_reach = math.sqrt((first_rate - first_low) ** 2 + (second_high - second_rate) ** 2)
    upper_reach = math.sqrt((first_high - first_rate) ** 2 + (second_rate - second_low) ** 2)
    low, high = difference - lower_reach, difference + upper_reach
    assert low <= high, f"DI-1 broken: {low} > {high}"
    assert -1.0 <= low and high <= 1.0, f"difference left [-1, 1]: {low}, {high}"
    return low, high
