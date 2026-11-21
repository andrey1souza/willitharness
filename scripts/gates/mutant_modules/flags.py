TESTS = (
    'tests/unit/test_flags_unit.py',
    'tests/unit/test_detectors_unit.py',
    'tests/gates/test_guard_corpus_gate.py',
)

SOURCE = 'src/willitharness/flags.py'

MUTANTS = (
    ('short-flag-must-be-the-whole-word', SOURCE, 'SHORT_CLUSTER_PATTERN = "-[a-zA-Z]*{letter}[a-zA-Z]*"', 'SHORT_CLUSTER_PATTERN = "-{letter}"'),
    ('short-flag-ignores-case', SOURCE, 'SHORT_CLUSTER_PATTERN = "-[a-zA-Z]*{letter}[a-zA-Z]*"', 'SHORT_CLUSTER_PATTERN = "(?i)-[a-zA-Z]*{letter}[a-zA-Z]*"'),
    ('short-flag-needs-a-letter-before-it', SOURCE, 'SHORT_CLUSTER_PATTERN = "-[a-zA-Z]*{letter}[a-zA-Z]*"', 'SHORT_CLUSTER_PATTERN = "-[a-zA-Z]+{letter}[a-zA-Z]*"'),
    ('short-flag-needs-a-letter-after-it', SOURCE, 'SHORT_CLUSTER_PATTERN = "-[a-zA-Z]*{letter}[a-zA-Z]*"', 'SHORT_CLUSTER_PATTERN = "-[a-zA-Z]*{letter}[a-zA-Z]+"'),
    ('flag-matches-a-prefix', SOURCE, 'any(re.fullmatch(flag_pattern, word) for word in words[1:])', 'any(re.match(flag_pattern, word) for word in words[1:])'),
    ('program-word-read-as-an-option', SOURCE, 'for word in words[1:])', 'for word in words)'),
    ('flag-word-shape-unchecked', SOURCE, 'if short is None and not LONG_FLAG.fullmatch(flag):', 'if False:'),
    ('options-may-come-first', SOURCE, 'if not command_words or not all(', 'if not all('),
    ('options-may-sit-in-the-middle', SOURCE, 'if not command_words or not all(word.startswith(OPTION_PREFIX) for word in flag_words):', 'if not command_words:'),
    ('options-of-an-action-dropped', SOURCE, 'patterns = tuple(flag_pattern_of(word) for word in flag_words)', 'patterns = tuple(flag_pattern_of(word) for word in flag_words[:1])'),
)
