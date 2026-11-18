import argparse
import random
import sys
from dataclasses import dataclass

from willitharness.counts import Counts
from willitharness.intervals import WILSON_Z
from willitharness.verdict import verdict_at
from willitharness.vocabulary import Verdict

EXIT_PASSED = 0
EXIT_FAILED = 1
FALSE_POSITIVE_LIMIT = 0.08
POWER_MINIMUM = 0.95
EQUAL_RATE = 0.5
HIGH_RATE = 0.85
LOW_RATE = 0.10
DECISIVE_VERDICTS = frozenset({Verdict.FIRST_HIGHER, Verdict.FIRST_LOWER})
POWER_VERDICTS = frozenset({Verdict.FIRST_HIGHER})
RATE_FORMAT = "{:.4f}"


@dataclass(frozen=True)
class Setup:
    trials: int
    n: int
    z: float


@dataclass(frozen=True)
class Scenario:
    first_rate: float
    second_rate: float
    wanted: frozenset


def draw(generator, rate, n):
    assert 0.0 <= rate <= 1.0, f"a rate lies in [0, 1], got {rate}. Fix: pass a probability."
    assert n >= 1, f"a draw needs at least one run, got {n}. Fix: pass --n 1 or more."
    counts = Counts(sum(generator.random() < rate for _ in range(n)), n)
    assert counts.runs == n, f"draw returned {counts.runs} runs for n {n}"
    return counts


def decisive_share(generator, scenario, setup):
    assert setup.trials >= 1, f"trials is {setup.trials}. Rule: a rate needs at least one trial. Fix: pass --trials 1 or more."
    assert scenario.wanted <= set(Verdict), f"unknown verdicts in {scenario.wanted}. Fix: use Verdict members."
    hits = sum(
        verdict_at(draw(generator, scenario.first_rate, setup.n), draw(generator, scenario.second_rate, setup.n), setup.z) in scenario.wanted
        for _ in range(setup.trials)
    )
    share = hits / setup.trials
    assert 0.0 <= share <= 1.0, f"a share left [0, 1]: {share}"
    return share


def simulate_gate(seed, setup):
    assert isinstance(seed, int), f"the seed is {seed!r}. Rule: runs are seeded. Fix: pass --seed with a whole number."
    assert setup.z > 0, f"z is {setup.z}. Rule: z is above 0. Fix: pass a positive z."
    generator = random.Random(seed)
    false_positive = decisive_share(generator, Scenario(EQUAL_RATE, EQUAL_RATE, DECISIVE_VERDICTS), setup)
    power = decisive_share(generator, Scenario(HIGH_RATE, LOW_RATE, POWER_VERDICTS), setup)
    print(f"false-positive rate {RATE_FORMAT.format(false_positive)} (at most {FALSE_POSITIVE_LIMIT})")
    print(f"power ({HIGH_RATE} against {LOW_RATE:.2f}) {RATE_FORMAT.format(power)} (at least {POWER_MINIMUM})")
    passed = false_positive <= FALSE_POSITIVE_LIMIT and power >= POWER_MINIMUM
    assert 0.0 <= false_positive <= 1.0 and 0.0 <= power <= 1.0, f"rates left [0, 1]: {false_positive}, {power}"
    return EXIT_PASSED if passed else EXIT_FAILED


def main(argv):
    assert isinstance(argv, list), f"main needs a list of arguments, got {argv!r}. Fix: pass sys.argv[1:]."
    assert all(isinstance(item, str) for item in argv), f"every argument must be text, got {argv!r}"
    parser = argparse.ArgumentParser(prog="simulate")
    parser.add_argument("--trials", type=int, required=True)
    parser.add_argument("--n", type=int, required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--z", type=float, default=WILSON_Z)
    arguments = parser.parse_args(argv)
    code = simulate_gate(arguments.seed, Setup(arguments.trials, arguments.n, arguments.z))
    if code != EXIT_PASSED:
        print("simulation gate failed: the verdicts are not calibrated. Rule: G4.3. Fix: check the interval code.", file=sys.stderr)
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
