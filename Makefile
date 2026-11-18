.PHONY: check test zanity mutants trace repo simulate formal integrate live

check: test zanity mutants trace repo simulate

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

simulate:
	uv run python scripts/gates/simulate.py --trials 400 --n 20 --seed 20261117

formal:
	python3 formal/lean/check_lean.py
	uv run python formal/tla/check_models.py

integrate:
	python3 scripts/guards/integrate.py

live:
	uv run python scripts/gates/probe_live.py
	uv run python scripts/gates/isolation_live.py
	uv run python scripts/gates/run_live.py
