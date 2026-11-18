.PHONY: check test zanity mutants

check: test zanity mutants

test:
	uv run pytest

zanity:
	zanity check . --baseline zanity-baseline.json --new-only --fail-on warning

mutants:
	uv run python scripts/gates/mutants.py stats
