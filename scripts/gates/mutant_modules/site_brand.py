SOURCE = 'scripts/site/brand_gates.py'

TESTS = (
    'tests/site/test_brand_gates.py',
)

MUTANTS = (
    ('hype-case-sensitive', SOURCE, 'r")(?![\\w-])", re.IGNORECASE)', 'r")(?![\\w-])")'),
    ('hype-inside-words', SOURCE, 'HYPE_PATTERN = re.compile(r"(?<![\\w-])(?:"', 'HYPE_PATTERN = re.compile(r"(?:"'),
    ('true-claims-still-reported', SOURCE, 'and claims.get(phrase) is not True', 'and True'),
    ('held-back-case-sensitive', SOURCE, '(?![\\w-])", text, re.IGNORECASE)', '(?![\\w-])", text)'),
    ('empty-meta-content-accepted', SOURCE, 'if found and (found[0].attributes.get("content") or "").strip():', 'if found:'),
    ('title-limit-raised', SOURCE, 'MAX_TITLE_CHARS = 60', 'MAX_TITLE_CHARS = 80'),
    ('description-limit-raised', SOURCE, 'MAX_DESCRIPTION_CHARS = 160', 'MAX_DESCRIPTION_CHARS = 200'),
    ('page-budget-doubled', SOURCE, 'PAGE_BUDGET_KIB = 64', 'PAGE_BUDGET_KIB = 128'),
    ('total-budget-doubled', SOURCE, 'TOTAL_BUDGET_KIB = 128', 'TOTAL_BUDGET_KIB = 256'),
    ('sentence-limit-raised', SOURCE, 'MAX_SENTENCE_WORDS = 20', 'MAX_SENTENCE_WORDS = 25'),
    ('share-lowered', SOURCE, 'MIN_SHORT_SENTENCE_PERCENT = 80', 'MIN_SHORT_SENTENCE_PERCENT = 50'),
    ('placeholders-hide-nothing', SOURCE, 'PLACEHOLDER = re.compile(r"\\$\\$|\\$\\{?\\w+\\}?")', 'PLACEHOLDER = re.compile(r"\\$\\$")'),
    ('any-rendered-number-allowed', SOURCE, 'sorted(set(shown) - allowed)', 'sorted(set())'),
    ('hash-in-string-is-a-comment', SOURCE, 'if token.type == tokenize.COMMENT]', 'if "#" in token.string]'),
    ('css-comment-ignored', SOURCE, 'STYLE_COMMENT = re.compile(r"/\\*")', 'STYLE_COMMENT = re.compile(r"/\\*x")'),
    ('markup-comment-ignored', SOURCE, 'MARKUP_COMMENT = re.compile(r"<!--")', 'MARKUP_COMMENT = re.compile(r"<!--x")'),
    ('markdown-only-at-top', SOURCE, '.rglob("*.md")', '.glob("*.md")'),
    ('missing-charset-accepted', SOURCE, 'if any(tag.name == "meta" and CHARSET in tag.attributes for tag in tags):\n        return []', 'if True:\n        return []'),
    ('lang-not-required', SOURCE, 'if not any(tag.name == "html" and tag.attributes.get("lang") for tag in tags):', 'if False:'),
)
