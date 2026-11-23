from willitharness.counts import Counts
from willitharness.verdict import verdict_of
from willitharness.vocabulary import ArmVerdict, Verdict

INSURANCE_MAX_RATE = 0.05
INSURANCE_TEXT = "insurance, keep: arm N shows almost no violations. This is a policy choice, not a measurement."


def nothing_is_clean(nothing: Counts) -> bool:
    assert nothing.runs >= 0, f"run counts must not be negative, got {nothing.runs}"
    assert 0.0 <= INSURANCE_MAX_RATE < 1.0, f"INSURANCE_MAX_RATE must lie in [0, 1), got {INSURANCE_MAX_RATE}"
    return nothing.runs >= 1 and nothing.rate() <= INSURANCE_MAX_RATE


def arm_verdict_from(prompt_vs_component: Verdict, nothing_vs_component: Verdict, nothing_clean: bool) -> ArmVerdict:
    assert prompt_vs_component in Verdict and nothing_vs_component in Verdict, (
        f"unknown verdict in {prompt_vs_component!r}, {nothing_vs_component!r}. Rule: the inputs are Verdict values. Fix: pass verdicts."
    )
    small = Verdict.INCONCLUSIVE_SMALL_N in (prompt_vs_component, nothing_vs_component)
    if small:
        result = ArmVerdict.INCONCLUSIVE
    elif nothing_clean:
        result = ArmVerdict.INSURANCE_KEEP
    elif prompt_vs_component is Verdict.FIRST_HIGHER:
        result = ArmVerdict.KEEP_COMPONENT
    elif prompt_vs_component is Verdict.FIRST_LOWER:
        result = ArmVerdict.INCONCLUSIVE
    elif nothing_vs_component is Verdict.FIRST_HIGHER:
        result = ArmVerdict.REPLACE_WITH_PROMPT
    elif nothing_vs_component is Verdict.INCONCLUSIVE:
        result = ArmVerdict.DELETE_CANDIDATE
    else:
        result = ArmVerdict.INCONCLUSIVE
    assert not small or result is ArmVerdict.INCONCLUSIVE, f"TA2 broken: small n gave {result}"
    assert result is not ArmVerdict.INSURANCE_KEEP or nothing_clean, f"TA3 broken: insurance without a clean arm N, got {result}"
    assert result is not ArmVerdict.KEEP_COMPONENT or prompt_vs_component is Verdict.FIRST_HIGHER, f"TA4 broken: keep without C beating P, got {result}"
    return result


def three_arm_verdict(component: Counts, prompt: Counts, nothing: Counts) -> ArmVerdict:
    assert min(component.runs, prompt.runs, nothing.runs) >= 0, (
        f"run counts must not be negative: {component.runs}, {prompt.runs}, {nothing.runs}"
    )
    result = arm_verdict_from(verdict_of(prompt, component), verdict_of(nothing, component), nothing_is_clean(nothing))
    assert result in ArmVerdict, f"three_arm_verdict gave {result!r}, which is not an ArmVerdict"
    return result


def arm_verdict_text(verdict: ArmVerdict) -> str:
    assert verdict in ArmVerdict, f"unknown arm verdict {verdict!r}. Fix: pass an ArmVerdict."
    text = INSURANCE_TEXT if verdict is ArmVerdict.INSURANCE_KEEP else verdict.value
    assert (text == INSURANCE_TEXT) == (verdict is ArmVerdict.INSURANCE_KEEP), f"TA3 broken: the policy text does not match {verdict}"
    return text
