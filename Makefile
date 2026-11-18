.PHONY: check test zanity mutants trace

check: test zanity mutants trace

test:
	uv run pytest

zanity:
	zanity check . --baseline zanity-baseline.json --new-only --fail-on warning

mutants:
	uv run python scripts/gates/mutants.py all

trace:
	uv run python scripts/gates/trace_check.py
