import shutil
from pathlib import Path

import pytest

from willitharness.stream import RunState, parse_stream

CORPUS = Path(__file__).resolve().parents[2] / "fixtures" / "streams"
CAP = 0.5
NEEDED = ("cp", "unlink")
USABLE = RunState.RECORDED_USABLE.value
UNUSABLE = RunState.RECORDED_UNUSABLE.value

EXPECTED = {
    "good-plain.jsonl": (USABLE, True, True, 0.012, 1, 0, ()),
    "good-denied-attempt.jsonl": (USABLE, True, True, 0.02, 3, 1, ("pkill -f vitest",)),
    "good-denied-needed.jsonl": (USABLE, True, False, 0.02, 2, 1, ("cp -f package.json package.json.bak",)),
    "good-string-message.jsonl": (USABLE, True, True, 0.01, 1, 0, ()),
    "bad-no-result.jsonl": (UNUSABLE, False, False, 0.0, 0, 0, ("ls",)),
    "bad-error-result.jsonl": (UNUSABLE, False, False, 0.0, 0, 0, ()),
    "bad-budget-exceeded.jsonl": (UNUSABLE, False, False, 0.0, 0, 0, ()),
    "bad-cost-above-cap.jsonl": (UNUSABLE, False, False, 0.0, 0, 0, ()),
    "bad-garbage-lines.jsonl": (UNUSABLE, False, False, 0.0, 0, 0, ()),
}


def test_every_fixture_has_an_expectation_and_the_reverse():
    names = sorted(path.name for path in CORPUS.glob("*.jsonl"))
    assert names == sorted(EXPECTED), f"fixtures {names} differ from expectations {sorted(EXPECTED)}. Fix: add or remove the row."


def stream_lines_of(name, workspace):
    shutil.copytree(CORPUS, workspace / "streams")
    return (workspace / "streams" / name).read_text().splitlines()


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_each_fixture_parses_to_its_expected_record(name, tmp_path):
    lines = stream_lines_of(name, tmp_path)
    record = parse_stream(lines, NEEDED, CAP)
    actual = (record.state.value, record.usable_for_attempted_violation, record.usable_for_completed, record.cost, record.turns, record.denials, record.commands)
    assert actual == EXPECTED[name], f"{name} parsed to {actual}, expected {EXPECTED[name]}"


def test_the_names_say_what_each_fixture_must_be():
    for name, expected in EXPECTED.items():
        assert name.startswith("good-") == (expected[0] == USABLE), f"{name} is named good or bad against state {expected[0]}"
