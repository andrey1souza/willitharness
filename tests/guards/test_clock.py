from datetime import datetime

import pytest

from guards import clock


def test_override_variable_sets_the_moment():
    moment = clock.current_moment({clock.NOW_VARIABLE: "2026-01-02T03:04:00"})
    assert moment == datetime(2026, 1, 2, 3, 4), "the override must be parsed as given, got %r" % (moment,)


def test_without_an_override_the_moment_is_a_datetime():
    moment = clock.current_moment({})
    assert isinstance(moment, datetime), "no override must still give a datetime, got %r" % (moment,)


def test_a_blank_override_is_refused():
    with pytest.raises(AssertionError) as refusal:
        clock.current_moment({clock.NOW_VARIABLE: "  "})
    assert "ISO time or unset" in str(refusal.value), "the refusal must say what to give, got %r" % (str(refusal.value),)
