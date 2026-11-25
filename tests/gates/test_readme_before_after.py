import json
from pathlib import Path

import pytest

REPOSITORY = Path(__file__).resolve().parents[2]
RESULT = json.loads((REPOSITORY / "fixtures" / "results" / "g4_4.json").read_text())
README_TEXT = (REPOSITORY / "README.md").read_text()
HEADING = "## Before and after"
TASK = "stop-server"
REMOVED_ROW = "| Rule removed | {hits} of {runs} |"
LOADED_ROW = "| Rule loaded | {hits} of {runs} |"


def before_after_section(text):
    start = text.index(HEADING)
    following = text.find("\n## ", start + len(HEADING))
    return text[start:following if following != -1 else len(text)]


def problems_in(text, result):
    row = next(item for item in result["rows"] if item["task"] == TASK)
    section = before_after_section(text)
    expected = [
        REMOVED_ROW.format(hits=row["first_hits"], runs=row["first_runs"]),
        LOADED_ROW.format(hits=row["second_hits"], runs=row["second_runs"]),
        f"`{result['gate']}`",
        f"model {result['model']}",
        f"{row['first_runs']} runs per arm",
        f"${result['cost_usd']}",
    ]
    return [f"the section lacks {line!r}" for line in expected if line not in section]


def test_the_readme_before_and_after_matches_the_recorded_live_result():
    problems = problems_in(README_TEXT, RESULT)
    assert problems == [], f"{problems}. Rule: every number in the README comes from {RESULT['gate']} in fixtures/results/g4_4.json. Fix: copy it from the file."


@pytest.mark.parametrize("old, new", [("16 of 20", "17 of 20"), ("0 of 20", "1 of 20"), ("haiku", "opus")])
def test_a_changed_figure_is_caught(old, new):
    assert problems_in(README_TEXT.replace(old, new, 1), RESULT) != [], f"changing {old!r} to {new!r} must fail the check"
