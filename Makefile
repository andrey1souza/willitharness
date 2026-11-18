.PHONY: check test zanity mutants trace repo

check: test zanity mutants trace repo

test:
	uv run pytest

zanity:
	zanity check . --baseline zanity-baseline.json --new-only --fail-on warning

mutants:
	uv run python scripts/gates/mutants.py all

trace:
	uv run python scripts/gates/trace_check.py

repo:
	uv run python scripts/gates/repo_checks.py
