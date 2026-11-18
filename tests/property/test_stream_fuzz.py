import json

from hypothesis import given, settings
from hypothesis import strategies as st

from willitharness.stream import RunRecord, RunState, load_event, parse_stream

CAP = 0.5
NEEDED = ("cp", "unlink")
EXAMPLES = 400
fuzz_settings = settings(max_examples=EXAMPLES, deadline=None)

json_values = st.recursive(
    st.none() | st.booleans() | st.integers() | st.floats() | st.text(),
    lambda children: st.lists(children, max_size=4) | st.dictionaries(st.text(max_size=12), children, max_size=4),
    max_leaves=12,
)
event_keys = st.sampled_from(["type", "subtype", "is_error", "message", "content", "name", "input", "command", "total_cost_usd", "num_turns", "permission_denials", "tool_input", "result"])
event_types = st.sampled_from(["assistant", "result", "user", "system", "tool_use", "Bash", "success"])
shaped_events = st.dictionaries(event_keys, json_values | event_types, max_size=8)
lines = (
    st.text()
    | json_values.map(json.dumps)
    | shaped_events.map(lambda event: json.dumps(event, allow_nan=True))
    | st.binary().map(lambda raw: raw.decode("latin-1"))
)


@fuzz_settings
@given(lines)
def test_parsing_one_line_never_raises_and_gives_an_object(line):
    event = load_event(line)
    assert isinstance(event, dict), f"line {line!r} gave {type(event)}, expected a dict"
    assert all(isinstance(key, str) for key in event), f"line {line!r} gave non-text keys in {event!r}"


@fuzz_settings
@given(st.lists(lines, max_size=8))
def test_an_arbitrary_stream_gives_a_consistent_record(stream):
    record = parse_stream(stream, NEEDED, CAP)
    assert isinstance(record, RunRecord), f"stream {stream!r} gave {type(record)}"
    unusable = record.state is RunState.RECORDED_UNUSABLE
    counted = record.usable_for_attempted_violation or record.usable_for_completed
    assert unusable != counted, f"state {record.state} with flags {record} for stream {stream!r}"
    assert record.cost <= CAP and record.denials >= 0, f"bad numbers in {record} for stream {stream!r}"


@fuzz_settings
@given(st.lists(shaped_events, max_size=6), st.floats(min_value=0, max_value=10, allow_nan=False))
def test_shaped_streams_never_raise_and_unusable_never_counts(events, cap):
    record = parse_stream([json.dumps(event) for event in events], NEEDED, cap)
    counted = record.usable_for_attempted_violation or record.usable_for_completed
    assert not counted or record.state is RunState.RECORDED_USABLE, f"flags set on {record} for {events!r}"
    assert record.cost <= cap, f"cost {record.cost} above cap {cap} for {events!r}"
