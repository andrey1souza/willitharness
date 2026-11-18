from pathlib import Path

PLAN_DIRECTORY = Path(__file__).resolve().parents[2] / "docs" / "plan"
RETIRED_COMMAND = "behave features/"


def test_no_plan_file_names_the_retired_behave_command():
    offenders = [path.name for path in sorted(PLAN_DIRECTORY.glob("*.md")) if RETIRED_COMMAND in path.read_text()]
    assert not offenders, f"{offenders} still name {RETIRED_COMMAND!r}. Rule: BDD gates run with pytest-bdd. Fix: write the pytest command."


def test_the_retired_command_is_not_hidden_by_a_missing_directory():
    files = sorted(PLAN_DIRECTORY.glob("*.md"))
    assert len(files) >= 7, f"expected the plan files in {PLAN_DIRECTORY}, found {[path.name for path in files]}"
