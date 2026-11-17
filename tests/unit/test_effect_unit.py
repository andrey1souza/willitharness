import pytest

from willitharness.effect import map_effect
from willitharness.vocabulary import EffectResult, NoiseStatus, Verdict

E1_TABLE = [
    (NoiseStatus.NOISE_OK, Verdict.INCONCLUSIVE_SMALL_N, EffectResult.NOT_ENOUGH_RUNS),
    (NoiseStatus.NOISE_OK, Verdict.FIRST_HIGHER, EffectResult.RULE_LOWERS_VIOLATIONS),
    (NoiseStatus.NOISE_OK, Verdict.FIRST_LOWER, EffectResult.RULE_RAISES_VIOLATIONS),
    (NoiseStatus.NOISE_OK, Verdict.INCONCLUSIVE, EffectResult.NO_MEASURABLE_EFFECT),
]
NOISE_PROBLEMS = [NoiseStatus.NOISE_UNMEASURED, NoiseStatus.NOISE_FLOOR_TOO_HIGH]


@pytest.mark.parametrize(("noise", "verdict", "expected"), E1_TABLE)
def test_E1_noise_ok_rows(noise, verdict, expected):
    result = map_effect(noise, verdict)
    assert result is expected, f"{result=} expected {expected=} for {noise=} {verdict=}"


@pytest.mark.parametrize("noise", NOISE_PROBLEMS)
@pytest.mark.parametrize("verdict", list(Verdict))
def test_E1_any_noise_problem_gives_invalid(noise, verdict):
    result = map_effect(noise, verdict)
    assert result is EffectResult.INVALID, f"{result=} for {noise=} {verdict=}"


def test_E1_covers_twelve_cases():
    tabled = len(NOISE_PROBLEMS) * len(Verdict) + len(E1_TABLE)
    expected = len(NoiseStatus) * len(Verdict)
    assert tabled == expected, f"{tabled=} {expected=}"
