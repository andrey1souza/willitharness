import json

import pytest

from willitharness.store import Cell, Record, RunState, StoreError, append_record, load_records, run_id_of

CELL = Cell("B", "stop-server")


def gate_record(attempt, state):
    return Record(run_id_of(CELL, attempt, attempt), "B", "stop-server", attempt, attempt, state, {"completed": True}, 0.01)


def test_G3_4_rewriting_a_recorded_run_fails_and_the_file_is_unchanged(tmp_path):
    path = tmp_path / "runs.jsonl"
    append_record(tmp_path, gate_record(1, RunState.RECORDED_USABLE))
    before = path.read_bytes()
    with pytest.raises(StoreError):
        append_record(tmp_path, gate_record(1, RunState.RECORDED_UNUSABLE))
    assert path.read_bytes() == before, f"the file changed: {before!r} became {path.read_bytes()!r}"
    assert len(load_records(tmp_path)) == 1, f"expected one stored record, got {load_records(tmp_path)}"


def test_G3_4_the_store_is_opened_in_append_mode_so_a_later_record_keeps_the_first_line(tmp_path):
    path = tmp_path / "runs.jsonl"
    append_record(tmp_path, gate_record(1, RunState.RECORDED_USABLE))
    first_line = path.read_text().splitlines()[0]
    append_record(tmp_path, gate_record(2, RunState.RECORDED_UNUSABLE))
    lines = path.read_text().splitlines()
    assert lines[0] == first_line, f"the first line changed from {first_line!r} to {lines[0]!r}"
    assert [json.loads(line)["run_id"] for line in lines] == ["B/stop-server/1#1", "B/stop-server/2#2"], f"got {lines}"


def test_G3_4_a_record_is_added_to_a_file_that_already_holds_lines(tmp_path):
    path = tmp_path / "runs.jsonl"
    existing = gate_record(1, RunState.RECORDED_USABLE)
    path.write_text(json.dumps({**existing.__dict__, "state": "RecordedUsable"}) + "\n")
    append_record(tmp_path, gate_record(2, RunState.STARTED))
    assert [record.run_id for record in load_records(tmp_path)] == ["B/stop-server/1#1", "B/stop-server/2#2"], f"got {load_records(tmp_path)}"
    assert load_records(tmp_path)[0] == existing, f"the planted record changed to {load_records(tmp_path)[0]}"


def test_G3_4_a_started_run_ends_in_a_new_line_and_the_first_line_stays(tmp_path):
    path = tmp_path / "runs.jsonl"
    append_record(tmp_path, gate_record(1, RunState.STARTED))
    first_line = path.read_text().splitlines()[0]
    append_record(tmp_path, gate_record(1, RunState.RECORDED_USABLE))
    lines = path.read_text().splitlines()
    assert lines[0] == first_line, f"the started line changed to {lines[0]!r}"
    assert len(lines) == 2, f"expected the end as a second line, got {lines}"


def test_a_line_that_is_not_a_record_is_named(tmp_path):
    path = tmp_path / "runs.jsonl"
    path.write_text("not json\n")
    (tmp_path / "empty").mkdir()
    with pytest.raises(StoreError) as caught:
        load_records(tmp_path)
    assert "not json" in str(caught.value), f"the error must show the bad line, got {caught.value}"
    assert load_records(tmp_path / "empty") == (), "a missing file means no records"
