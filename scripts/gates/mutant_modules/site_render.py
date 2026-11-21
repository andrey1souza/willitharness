SOURCE = 'scripts/site/render.py'

TESTS = (
    'tests/site/test_render.py',
)

MUTANTS = (
    ('html-not-escaped', SOURCE, 'rendered = CODE_SPAN.sub(lambda found: f"<code>{found.group(1)}</code>", escape(text, quote=False))', 'rendered = CODE_SPAN.sub(lambda found: f"<code>{found.group(1)}</code>", text)'),
    ('unknown-status-is-bad', SOURCE, 'TONES.get(word, "warn")', 'TONES.get(word, "bad")'),
    ('failed-is-keep', SOURCE, '"failed": "bad"', '"failed": "keep"'),
    ('hits-above-runs-allowed', SOURCE, 'assert 0 <= hits <= runs,', 'assert 0 <= hits,'),
    ('cost-padded', SOURCE, 'repr(live["cost_usd"])', 'f"{live[\'cost_usd\']:.4f}"'),
    ('attribute-quote-kept', SOURCE, 'escape(readme["description"], quote=True)', 'escape(readme["description"], quote=False)'),
    ('source-line-shifted', SOURCE, 'f\'data-source="{escape(file)}:{line}"\'', 'f\'data-source="{escape(file)}:{line + 1}"\''),
    ('code-span-dropped', SOURCE, 'CODE_SPAN.sub(lambda found: f"<code>{found.group(1)}</code>", escape(text, quote=False))', 'escape(text, quote=False)'),
    ('match-claim-unchecked', SOURCE, 'assert live["matches_spike"] is close,', 'assert True,'),
    ('percent-unchecked', SOURCE, 'assert live["stop_server_percent"] == computed,', 'assert True,'),
    ('tolerance-widened', SOURCE, 'MATCH_TOLERANCE_POINTS = 5', 'MATCH_TOLERANCE_POINTS = 60'),
    ('tolerance-zero', SOURCE, 'MATCH_TOLERANCE_POINTS = 5', 'MATCH_TOLERANCE_POINTS = 0'),
    ('no-match-worded-as-match', SOURCE, 'verdict = "matches" if close else "does not match"', 'verdict = "matches"'),
    ('history-cost-dropped', SOURCE, 'plain(f"${item[\'cost_usd\']!r}")', 'plain("")'),
)
