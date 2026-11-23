TESTS = (
    'tests/unit/test_placebo_unit.py',
    'tests/golden/test_golden_tables.py',
)

SOURCE = 'src/willitharness/placebo.py'

MUTANTS = (
    ('small-n-in-placebo-comparison-ignored', SOURCE, 'small = Verdict.INCONCLUSIVE_SMALL_N in comparisons', 'small = Verdict.INCONCLUSIVE_SMALL_N in comparisons[1:]'),
    ('small-n-in-nothing-against-placebo-ignored', SOURCE, 'small = Verdict.INCONCLUSIVE_SMALL_N in comparisons', 'small = Verdict.INCONCLUSIVE_SMALL_N in (comparisons[0], comparisons[2])'),
    ('small-n-in-nothing-against-component-ignored', SOURCE, 'small = Verdict.INCONCLUSIVE_SMALL_N in comparisons', 'small = Verdict.INCONCLUSIVE_SMALL_N in comparisons[:2]'),
    ('no-room-never-given', SOURCE, '    elif nothing_clean:\n        result = ContentVerdict.NO_ROOM_TO_HELP', '    elif False:\n        result = ContentVerdict.NO_ROOM_TO_HELP'),
    ('no-room-before-small-n', SOURCE, '    if small:\n        result = ContentVerdict.INCONCLUSIVE\n    elif nothing_clean:', '    if nothing_clean:\n        result = ContentVerdict.NO_ROOM_TO_HELP\n    elif small:'),
    ('content-win-ignored', SOURCE, 'FIRST_HIGHER:\n        result = ContentVerdict.CONTENT_BEATS_FILLER', 'FIRST_HIGHER:\n        result = ContentVerdict.NOTHING_HELPS'),
    ('content-win-for-any-difference', SOURCE, '    elif placebo_vs_component is Verdict.FIRST_HIGHER:\n        result = ContentVerdict.CONTENT_BEATS_FILLER', '    elif placebo_vs_component is not Verdict.INCONCLUSIVE:\n        result = ContentVerdict.CONTENT_BEATS_FILLER'),
    ('filler-win-called-content-win', SOURCE, 'FIRST_LOWER:\n        result = ContentVerdict.FILLER_BEATS_CONTENT', 'FIRST_LOWER:\n        result = ContentVerdict.CONTENT_BEATS_FILLER'),
    ('filler-win-ignored', SOURCE, 'FIRST_LOWER:\n        result = ContentVerdict.FILLER_BEATS_CONTENT', 'FIRST_LOWER:\n        result = ContentVerdict.INCONCLUSIVE'),
    ('added-text-when-only-the-filler-beats-nothing', SOURCE, 'both_beat_nothing = nothing_vs_placebo is Verdict.FIRST_HIGHER and nothing_vs_component is Verdict.FIRST_HIGHER', 'both_beat_nothing = nothing_vs_placebo is Verdict.FIRST_HIGHER'),
    ('added-text-when-only-the-component-beats-nothing', SOURCE, 'both_beat_nothing = nothing_vs_placebo is Verdict.FIRST_HIGHER and nothing_vs_component is Verdict.FIRST_HIGHER', 'both_beat_nothing = nothing_vs_component is Verdict.FIRST_HIGHER'),
    ('added-text-when-either-beats-nothing', SOURCE, 'both_beat_nothing = nothing_vs_placebo is Verdict.FIRST_HIGHER and nothing_vs_component is Verdict.FIRST_HIGHER', 'both_beat_nothing = nothing_vs_placebo is Verdict.FIRST_HIGHER or nothing_vs_component is Verdict.FIRST_HIGHER'),
    ('added-text-never-given', SOURCE, '    elif both_beat_nothing:\n        result = ContentVerdict.ADDED_TEXT_HELPS', '    elif False:\n        result = ContentVerdict.ADDED_TEXT_HELPS'),
    ('nothing-helps-when-the-filler-alone-beats-nothing', SOURCE, 'neither_beats_nothing = nothing_vs_placebo is not Verdict.FIRST_HIGHER and nothing_vs_component is not Verdict.FIRST_HIGHER', 'neither_beats_nothing = nothing_vs_component is not Verdict.FIRST_HIGHER'),
    ('nothing-helps-when-the-component-alone-beats-nothing', SOURCE, 'neither_beats_nothing = nothing_vs_placebo is not Verdict.FIRST_HIGHER and nothing_vs_component is not Verdict.FIRST_HIGHER', 'neither_beats_nothing = nothing_vs_placebo is not Verdict.FIRST_HIGHER'),
    ('nothing-helps-never-given', SOURCE, '    elif neither_beats_nothing:\n        result = ContentVerdict.NOTHING_HELPS', '    elif False:\n        result = ContentVerdict.NOTHING_HELPS'),
    ('unclear-called-added-text', SOURCE, '    else:\n        result = ContentVerdict.UNCLEAR', '    else:\n        result = ContentVerdict.ADDED_TEXT_HELPS'),
    ('unclear-called-nothing-helps', SOURCE, '    else:\n        result = ContentVerdict.UNCLEAR', '    else:\n        result = ContentVerdict.NOTHING_HELPS'),
    ('arms-swapped-in-placebo-comparison', SOURCE, 'verdict_of(placebo, component), verdict_of(nothing, placebo), verdict_of(nothing, component)', 'verdict_of(component, placebo), verdict_of(nothing, placebo), verdict_of(nothing, component)'),
    ('nothing-against-the-placebo-read-from-the-component', SOURCE, 'verdict_of(nothing, placebo), verdict_of(nothing, component)', 'verdict_of(nothing, component), verdict_of(nothing, component)'),
    ('nothing-against-the-component-read-from-the-placebo', SOURCE, 'verdict_of(nothing, placebo), verdict_of(nothing, component)', 'verdict_of(nothing, placebo), verdict_of(nothing, placebo)'),
    ('arms-swapped-in-nothing-against-the-placebo', SOURCE, 'verdict_of(nothing, placebo), verdict_of(nothing, component)', 'verdict_of(placebo, nothing), verdict_of(nothing, component)'),
    ('arms-swapped-in-nothing-against-the-component', SOURCE, 'verdict_of(nothing, placebo), verdict_of(nothing, component)', 'verdict_of(nothing, placebo), verdict_of(component, nothing)'),
    ('clean-read-from-the-placebo', SOURCE, 'nothing_is_clean(nothing))\n    assert result in', 'nothing_is_clean(placebo))\n    assert result in'),
    ('added-text-sentence-changed', SOURCE, 'added text helps and the content does not', 'the content helps'),
    ('policy-text-dropped', SOURCE, 'ContentVerdict.NO_ROOM_TO_HELP: NO_ROOM_TEXT,', 'ContentVerdict.NO_ROOM_TO_HELP: "no room to help",'),
)
