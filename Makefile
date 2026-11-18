.PHONY: check test zanity mutants trace repo formal integrate

check: test zanity mutants trace repo

test:
	uv run pytest

zanity:
	zanity check . --fail-on warning

mutants:
	uv run python scripts/gates/mutants.py all

trace:
	uv run python scripts/gates/trace_check.py

repo:
	uv run python scripts/gates/repo_checks.py

formal:
	python3 formal/lean/check_lean.py
	python3 formal/tla/check_models.py

integrate:
	python3 scripts/guards/integrate.py
