.PHONY: check test zanity

check: test zanity

test:
	uv run pytest

zanity:
	zanity check . --baseline zanity-baseline.json --new-only --fail-on warning
