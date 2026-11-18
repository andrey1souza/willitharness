from dataclasses import dataclass

from willitharness.effect import map_effect
from willitharness.probe import loo_arm_valid
from willitharness.verdict import MIN_RUNS
from willitharness.vocabulary import EffectResult, NoiseStatus, Reach, Verdict

LOO_INVALID_MESSAGE = "LOO arm does not load its other rules; the effect cannot be reported"
RULE_UNKNOWN_MESSAGE = "the rule arm's reachability is Unknown; run the probe again before measuring an effect"
NO_NOISE_PAIR_MESSAGE = "no noise pair; add a repeat of arm {loo} with role noise_of:{loo}"
NOISE_MESSAGES = {
    NoiseStatus.NOISE_UNMEASURED: "the noise pair has fewer than {minimum} usable runs on one side; run more repeats of arm {loo}",
    NoiseStatus.NOISE_FLOOR_TOO_HIGH: "the two identical arms differed; do not trust this comparison",
}


@dataclass(frozen=True)
class PlanFacts:
    has_noise_pair: bool
    noise: NoiseStatus
    loo_probe: Reach
    rule_reach: Reach


@dataclass(frozen=True)
class EffectAnalysis:
    effect: EffectResult
    verdict: Verdict | None
    message: str | None


def can_report(facts):
    assert isinstance(facts.has_noise_pair, bool), f"has_noise_pair must be a flag, got {facts.has_noise_pair!r}"
    assert facts.noise in NoiseStatus and facts.loo_probe in Reach and facts.rule_reach in Reach, f"unknown value in {facts}"
    return (
        facts.has_noise_pair
        and facts.noise is NoiseStatus.NOISE_OK
        and loo_arm_valid(facts.loo_probe)
        and facts.rule_reach is not Reach.UNKNOWN
    )


def blocking_message(facts, loo_label):
    assert loo_label, "blocking_message needs the LOO arm label. Fix: pass the label of the leave_one_out arm."
    assert not can_report(facts), f"blocking_message was called for a plan that can report: {facts}"
    if not facts.has_noise_pair:
        return NO_NOISE_PAIR_MESSAGE.format(loo=loo_label)
    if not loo_arm_valid(facts.loo_probe):
        return LOO_INVALID_MESSAGE
    if facts.rule_reach is Reach.UNKNOWN:
        return RULE_UNKNOWN_MESSAGE
    return NOISE_MESSAGES[facts.noise].format(minimum=MIN_RUNS, loo=loo_label)


def analyze_effect(facts, verdict, loo_label):
    assert verdict in Verdict, f"unknown verdict {verdict!r}"
    assert loo_label, "analyze_effect needs the LOO arm label. Fix: pass the label of the leave_one_out arm."
    if can_report(facts):
        outcome = EffectAnalysis(map_effect(facts.noise, verdict), verdict, None)
    else:
        outcome = EffectAnalysis(EffectResult.INVALID, None, blocking_message(facts, loo_label))
    assert (outcome.verdict is not None) == can_report(facts), f"V6 or L8 broken: {outcome} for {facts}"
    assert outcome.verdict is None or outcome.message is None, f"a reported effect carries no blocking message: {outcome}"
    return outcome
