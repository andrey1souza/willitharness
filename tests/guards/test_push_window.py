from datetime import datetime

import pytest

from guards import push_window

DAY = (2026, 11, 17)


def at(hour, minute):
    return datetime(*DAY, hour, minute)


@pytest.mark.parametrize(
    "hour, minute, expected",
    [
        (17, 59, False),
        (18, 0, True),
        (23, 59, True),
        (0, 0, True),
        (8, 59, True),
        (9, 0, False),
        (12, 30, False),
    ],
)
def test_window_boundaries(hour, minute, expected):
    moment = at(hour, minute)
    assert push_window.push_allowed(moment) is expected, (
        "push at %s should be allowed=%r but the window said otherwise" % (moment.strftime("%H:%M"), expected)
    )


def test_main_allows_inside_the_window(capsys):
    environment = {push_window.NOW_VARIABLE: "2026-11-17T20:33:00"}
    code = push_window.main(environment)
    printed = capsys.readouterr().err
    assert code == push_window.EXIT_ALLOWED, "20:33 is inside the window, but main exited %r" % (code,)
    assert printed == "", "an allowed push must stay silent, but main printed %r" % (printed,)


def test_main_blocks_outside_the_window_with_an_actionable_message(capsys):
    environment = {push_window.NOW_VARIABLE: "2026-11-17T14:05:00"}
    code = push_window.main(environment)
    message = capsys.readouterr().err
    assert code == push_window.EXIT_BLOCKED, "14:05 is outside the window, but main exited %r" % (code,)
    assert "14:05" in message, "the message must show the clock time, got %r" % (message,)
    assert "Rule:" in message, "the message must state the rule, got %r" % (message,)
    assert "Fix:" in message, "the message must end with a fix, got %r" % (message,)
    assert "18:00" in message, "the message must name when pushing opens, got %r" % (message,)


def test_override_variable_sets_the_moment():
    environment = {push_window.NOW_VARIABLE: "2026-01-02T03:04:00"}
    moment = push_window.current_moment(environment)
    assert moment == datetime(2026, 1, 2, 3, 4), "the override must be parsed as given, got %r" % (moment,)


def test_blocked_message_refuses_to_describe_an_allowed_moment():
    with pytest.raises(AssertionError) as refusal:
        push_window.blocked_message(at(20, 0))
    assert "inside the window" in str(refusal.value), (
        "the refusal must say the moment is inside the window, got %r" % (str(refusal.value),)
    )
