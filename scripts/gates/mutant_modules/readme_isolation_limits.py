SOURCE = 'scripts/gates/repo_checks.py'

TESTS = (
    'tests/gates/test_readme_isolation_limits.py',
)

MUTANTS = (
    ('heading-not-required', SOURCE, 'if lines.count(ISOLATION_HEADING) != 1:', 'if False:'),
    ('repeated-heading-accepted', SOURCE, 'if lines.count(ISOLATION_HEADING) != 1:', 'if lines.count(ISOLATION_HEADING) < 1:'),
    ('phrases-not-checked', SOURCE, 'for phrase in ISOLATION_PHRASES if phrase not in normalized]', 'for phrase in ISOLATION_PHRASES if False]'),
    ('phrases-searched-in-the-whole-file', SOURCE, 'normalized = " ".join(" ".join(body).replace', 'normalized = " ".join(" ".join(lines).replace'),
    ('section-runs-to-the-end', SOURCE, 'following[0] if following else len(lines)', 'len(lines)'),
    ('case-sensitive-match', SOURCE, '.replace("`", "").lower().split())', '.replace("`", "").split())'),
    ('backticks-kept', SOURCE, '.replace("`", "").lower()', '.lower()'),
    ('line-breaks-break-phrases', SOURCE, 'normalized = " ".join(" ".join(body)', 'normalized = "\\n".join("\\n".join(body)'),
    ('length-limit-dropped', SOURCE, 'if len(body) > ISOLATION_MAX_LINES:', 'if False:'),
    ('length-limit-off-by-one', SOURCE, 'if len(body) > ISOLATION_MAX_LINES:', 'if len(body) >= ISOLATION_MAX_LINES:'),
    ('limit-raised', SOURCE, 'ISOLATION_MAX_LINES = 6', 'ISOLATION_MAX_LINES = 60'),
    ('network-phrase-dropped', SOURCE, '    "the network is not blocked",\n', ''),
    ('linux-phrase-dropped', SOURCE, '    "there is no sandbox on linux",\n', ''),
    ('claude-phrase-dropped', SOURCE, '    "the claude process itself is not confined",\n', ''),
    ('hostile-phrase-dropped', SOURCE, '    "not a security boundary against a hostile plan",\n', ''),
    ('read-plans-phrase-dropped', SOURCE, '    "run only plans you have read",\n', ''),
    ('sandbox-exec-phrase-dropped', SOURCE, '    "isolation uses macos sandbox-exec",\n', ''),
    ('check-not-registered', SOURCE, '    "readme-isolation-limits": readme_isolation_errors,\n', ''),
    ('check-reads-another-file', SOURCE, 'README_FILE = Path("README.md")', 'README_FILE = Path("SECURITY.md")'),
)
