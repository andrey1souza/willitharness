SOURCE = 'scripts/gates/repo_checks.py'

TESTS = (
    'tests/gates/test_integrate_not_for_publishing.py',
)

MUTANTS = (
    ('wrapped-sentence-split', SOURCE, 'sentence in SENTENCE_BREAK.split(paragraph)]', 'sentence in paragraph.splitlines()]'),
    ('readme-not-scanned', SOURCE, 'PUBLISH_DOCUMENTS = (Path("README.md"), Path("SECURITY.md"), MAKEFILE)', 'PUBLISH_DOCUMENTS = (Path("SECURITY.md"), MAKEFILE)'),
    ('security-not-scanned', SOURCE, 'PUBLISH_DOCUMENTS = (Path("README.md"), Path("SECURITY.md"), MAKEFILE)', 'PUBLISH_DOCUMENTS = (Path("README.md"), MAKEFILE)'),
    ('makefile-not-scanned', SOURCE, 'PUBLISH_DOCUMENTS = (Path("README.md"), Path("SECURITY.md"), MAKEFILE)', 'PUBLISH_DOCUMENTS = (Path("README.md"), Path("SECURITY.md"))'),
    ('docs-not-scanned', SOURCE, 'top_level = sorted(path.relative_to(root) for path in (root / docs_freshness.DOCS_DIRECTORY).glob("*.md"))', 'top_level = []'),
    ('docs-scanned-recursively', SOURCE, '(root / docs_freshness.DOCS_DIRECTORY).glob("*.md")', '(root / docs_freshness.DOCS_DIRECTORY).rglob("*.md")'),
    ('frozen-contract-scanned', SOURCE, 'if path not in docs_freshness.HISTORICAL_FILES]', 'if path]'),
    ('pull-request-word-dropped', SOURCE, '|pull requests?|PRs?)', ')'),
    ('push-word-dropped', SOURCE, '|push\\w*|', '|'),
    ('publish-word-dropped', SOURCE, '(?:publish\\w*|', '(?:'),
    ('land-local-not-required', SOURCE, 'if LAND_LOCAL_WORD.search(sentence) and PUBLISH_WORD', 'if PUBLISH_WORD'),
    ('negation-ignored', SOURCE, ' and not NEGATION_WORD.search(sentence)]', ']'),
    ('check-not-registered', SOURCE, '    "integrate-not-for-publishing": integrate_publishing_errors,\n', ''),
)
