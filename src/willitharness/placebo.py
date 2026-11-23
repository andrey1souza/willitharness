from willitharness.counts import Counts
from willitharness.three_arm import nothing_is_clean
from willitharness.verdict import verdict_of
from willitharness.vocabulary import ContentVerdict, Verdict

NO_ROOM_TEXT = "no room to help: arm N shows almost no violations. This is a policy choice, not a measurement."
CONTENT_TEXT_BY_VERDICT = {
    ContentVerdict.CONTENT_BEATS_FILLER: "the content helps beyond added text",
    ContentVerdict.ADDED_TEXT_HELPS: "added text helps and the content does not",
    ContentVerdict.NOTHING_HELPS: "neither the content nor added text helps",
    ContentVerdict.FILLER_BEATS_CONTENT: "filler text beats the content",
    ContentVerdict.UNCLEAR: "unclear: only one of the content and the filler text beats arm N",
    ContentVerdict.NO_ROOM_TO_HELP: NO_ROOM_TEXT,
    ContentVerdict.INCONCLUSIVE: "inconclusive: an arm has too few runs",
}


def content_verdict_from(placebo_vs_component: Verdict, nothing_vs_placebo: Verdict, nothing_vs_component: Verdict, nothing_clean: bool) -> ContentVerdict:
    comparisons = (placebo_vs_component, nothing_vs_placebo, nothing_vs_component)
    assert all(comparison in Verdict for comparison in comparisons), (
        f"unknown verdict in {comparisons!r}. Rule: the inputs are Verdict values. Fix: pass verdicts."
    )
    small = Verdict.INCONCLUSIVE_SMALL_N in comparisons
    both_beat_nothing = nothing_vs_placebo is Verdict.FIRST_HIGHER and nothing_vs_component is Verdict.FIRST_HIGHER
    neither_beats_nothing = nothing_vs_placebo is not Verdict.FIRST_HIGHER and nothing_vs_component is not Verdict.FIRST_HIGHER
    if small:
        result = ContentVerdict.INCONCLUSIVE
    elif nothing_clean:
        result = ContentVerdict.NO_ROOM_TO_HELP
    elif placebo_vs_component is Verdict.FIRST_HIGHER:
        result = ContentVerdict.CONTENT_BEATS_FILLER
    elif placebo_vs_component is Verdict.FIRST_LOWER:
        result = ContentVerdict.FILLER_BEATS_CONTENT
    elif both_beat_nothing:
        result = ContentVerdict.ADDED_TEXT_HELPS
    elif neither_beats_nothing:
        result = ContentVerdict.NOTHING_HELPS
    else:
        result = ContentVerdict.UNCLEAR
    assert not small or result is ContentVerdict.INCONCLUSIVE, f"PB2 broken: small n gave {result}"
    assert result is not ContentVerdict.NO_ROOM_TO_HELP or nothing_clean, f"PB3 broken: no room without a clean arm N, got {result}"
    assert result is not ContentVerdict.ADDED_TEXT_HELPS or (
        placebo_vs_component is Verdict.INCONCLUSIVE and both_beat_nothing
    ), f"PB6 broken: added text helps without C equal to PL and both beating N, got {result}"
    assert (result is ContentVerdict.CONTENT_BEATS_FILLER) <= (placebo_vs_component is Verdict.FIRST_HIGHER), f"PB4 broken: got {result}"
    return result


def content_verdict(component: Counts, placebo: Counts, nothing: Counts) -> ContentVerdict:
    assert min(component.runs, placebo.runs, nothing.runs) >= 0, (
        f"run counts must not be negative: {component.runs}, {placebo.runs}, {nothing.runs}"
    )
    result = content_verdict_from(verdict_of(placebo, component), verdict_of(nothing, placebo), verdict_of(nothing, component), nothing_is_clean(nothing))
    assert result in ContentVerdict, f"content_verdict gave {result!r}, which is not a ContentVerdict"
    return result


def content_verdict_text(verdict: ContentVerdict) -> str:
    assert verdict in ContentVerdict, f"unknown content verdict {verdict!r}. Fix: pass a ContentVerdict."
    text = CONTENT_TEXT_BY_VERDICT[verdict]
    assert text, f"content_verdict_text built no text for {verdict}"
    return text
