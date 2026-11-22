TESTS = (
    'tests/gates/test_side_effects.py',
)

SOURCE = 'src/willitharness/side_effects.py'

MUTANTS = (
    ('threshold-hides-the-difference', SOURCE, 'MIN_RATE_GAP = 0.2', 'MIN_RATE_GAP = 0.5'),
    ('threshold-excludes-the-minimum-gap', SOURCE, 'result = max(rates) - min(rates) >= MIN_RATE_GAP', 'result = max(rates) - min(rates) > MIN_RATE_GAP'),
    ('threshold-accepts-any-gap', SOURCE, 'MIN_RATE_GAP = 0.2', 'MIN_RATE_GAP = 0.0'),
    ('counts-compared-not-rates', SOURCE, 'rates = [counts.rate() for counts in per_arm.values()]', 'rates = [counts.successes / 10 for counts in per_arm.values()]'),
    ('every-command-listed', SOURCE, 'if differs(per_arm)]', 'if per_arm]'),
    ('no-difference-line-dropped', SOURCE, 'else [NO_DIFFERENCE_LINE]', 'else []'),
    ('command-key-keeps-every-word', SOURCE, 'takewhile(lambda word: word.startswith(FLAG_PREFIX), words[1:])', 'words[1:]'),
    ('command-key-drops-flags', SOURCE, 'takewhile(lambda word: word.startswith(FLAG_PREFIX), words[1:])', '()'),
    ('repeat-use-counts-each-time', SOURCE, 'sum(name in names for names in per_run)', 'sum(len(names) for names in per_run)'),
    ('only-the-first-segment-counts', SOURCE, 'for segment in shell_segments(call.command))', 'for segment in shell_segments(call.command)[:1])'),
    ('assignment-only-segment-counted', SOURCE, 'for segment in segments if program_words(segment))', 'for segment in segments)'),
    ('bash-listed-as-a-channel', SOURCE, 'for call in run if call.tool != BASH_TOOL)', 'for call in run)'),
    ('channels-not-listed', SOURCE, '    if channels:\n', '    if False:\n'),
    ('first-arm-only', SOURCE, 'for arm, runs in runs_by_arm.items()}\n    every_name', 'for arm, runs in list(runs_by_arm.items())[:1]}\n    every_name'),
    ('single-arm-accepted', SOURCE, 'MIN_ARMS = 2', 'MIN_ARMS = 1'),
    ('rule-note-dropped', SOURCE, 'lines = [*differing, NOT_PART_OF_RULE_LINE] if differing', 'lines = [*differing] if differing'),
)
