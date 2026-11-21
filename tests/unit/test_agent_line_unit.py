import json

import pytest

from willitharness.agent_line import agent_line, stored_models, stored_version
from willitharness.stream import model_of

INIT = {"type": "system", "subtype": "init", "model": "claude-haiku-5-5"}


def write_transcript(path, events):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(event) for event in events) + "\n")
    return path


@pytest.mark.parametrize(
    ("version", "models", "expected"),
    [
        ("2.1.0 (Claude Code)", ("claude-haiku-5-5",), "agent: claude 2.1.0 (Claude Code), model claude-haiku-5-5"),
        ("2.1.0", ("b", "a", "b"), "agent: claude 2.1.0, models a, b"),
        ("2.1.0", (), "agent: claude 2.1.0, model unknown"),
        (None, ("a",), "agent: claude unknown, model a"),
        (None, (), "agent: claude unknown, model unknown"),
    ],
)
def test_the_agent_line_names_the_version_and_the_models_or_unknown(version, models, expected):
    assert agent_line(version, models) == expected, f"Rule: one model reads model, several read models, none reads unknown. Fix: got {agent_line(version, models)!r}"
    assert agent_line(version, models).startswith("agent: claude "), "the line has a fixed start"


def test_a_model_comes_from_the_init_event_only():
    lines = [json.dumps({"type": "assistant", "model": "wrong"}), json.dumps(INIT), json.dumps({"type": "system", "subtype": "init", "model": "second"})]
    assert model_of(lines) == "claude-haiku-5-5", f"the first init event names the model, got {model_of(lines)!r}"
    assert model_of([json.dumps({"type": "system", "subtype": "init"}), "not json", json.dumps({"type": "result", "model": "x"})]) is None, "an init without a model names none"


def test_the_stored_models_come_from_every_transcript_of_the_plan(tmp_path):
    write_transcript(tmp_path / "runs/C/task/1/transcript-1.jsonl", [INIT])
    write_transcript(tmp_path / "runs/B/task/1/transcript-1.jsonl", [{**INIT, "model": "claude-sonnet-5-5"}])
    write_transcript(tmp_path / "runs/B/task/2/transcript-2.jsonl", [{"type": "result"}])
    write_transcript(tmp_path / "runs/B/task/2/calls-2.log", [INIT])
    assert sorted(stored_models(tmp_path)) == ["claude-haiku-5-5", "claude-sonnet-5-5"], f"got {stored_models(tmp_path)}"
    (tmp_path / "bare").mkdir()
    assert stored_models(tmp_path / "bare") == (), f"a plan with no runs has no models under {tmp_path}"


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        ('{"claude_version": "2.1.0"}', "2.1.0"),
        ('{"claude_version": ""}', None),
        ('{"other": "2.1.0"}', None),
        ("not json", None),
        (None, None),
    ],
)
def test_the_stored_version_comes_from_the_agent_record_or_is_absent(tmp_path, content, expected):
    if content is not None:
        (tmp_path / "agent.json").write_text(content)
    assert stored_version(tmp_path) == expected, f"Rule: only a non-empty claude_version counts. Fix: got {stored_version(tmp_path)!r} for {content!r}"
    assert stored_version(tmp_path) is None or stored_version(tmp_path) == "2.1.0", f"no other text passes in {tmp_path}"
