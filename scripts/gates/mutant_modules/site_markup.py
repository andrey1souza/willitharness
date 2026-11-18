SOURCE = 'scripts/site/markup.py'

TESTS = (
    'tests/site/test_markup.py',
)

MUTANTS = (
    ('head-text-visible', SOURCE, 'SKIPPED_TEXT_ELEMENTS = ("style", "script", "head")', 'SKIPPED_TEXT_ELEMENTS = ("style", "script")'),
    ('question-mark-not-a-stop', SOURCE, 'SENTENCE_END = re.compile(r"(?<=[.!?])\\s+")', 'SENTENCE_END = re.compile(r"(?<=[.!])\\s+")'),
    ('whitespace-removed-not-collapsed', SOURCE, 'WHITESPACE.sub(" ", "".join(open_blocks.pop()))', 'WHITESPACE.sub("", "".join(open_blocks.pop()))'),
    ('empty-blocks-kept', SOURCE, 'blocks = [block for block in parsed(html).blocks if block]', 'blocks = [block for block in parsed(html).blocks]'),
    ('entities-kept', SOURCE, 'for part in SENTENCE_END.split(unescape(block))', 'for part in SENTENCE_END.split(block)'),
    ('end-tag-marked-open', SOURCE, 'bool(slash), line))', 'False, line))'),
    ('end-tags-deepen-the-skip', SOURCE, 'step = -1 if slash else 1', 'step = 1'),
)
