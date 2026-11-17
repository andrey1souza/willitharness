import os
import sys
from datetime import datetime

OPENS_AT_HOUR = 18
CLOSES_AT_HOUR = 9
LAST_ALLOWED_MINUTE = 59
HOURS_PER_DAY = 24
NOW_VARIABLE = "WILLITHARNESS_NOW"
EXIT_ALLOWED = 0
EXIT_BLOCKED = 1


def push_allowed(moment):
    assert isinstance(moment, datetime), (
        "push_allowed needs a datetime but got %r. Rule: the window compares the hour. "
        "Fix: pass datetime.now() or a parsed ISO time." % (moment,)
    )
    assert 0 <= moment.hour < HOURS_PER_DAY, (
        "hour %r is outside 0 to %d. Rule: the window compares an hour of the day. "
        "Fix: pass a real datetime." % (moment.hour, HOURS_PER_DAY - 1)
    )
    return moment.hour >= OPENS_AT_HOUR or moment.hour < CLOSES_AT_HOUR


def current_moment(environment):
    override = environment.get(NOW_VARIABLE)
    assert override is None or override.strip(), (
        "%s is set to %r. Rule: the override must be an ISO time or unset. "
        "Fix: unset the variable or give a value such as 2026-11-17T20:00:00." % (NOW_VARIABLE, override)
    )
    moment = datetime.fromisoformat(override) if override else datetime.now()
    assert isinstance(moment, datetime), (
        "current_moment built %r instead of a datetime. Rule: callers compare hours. "
        "Fix: check the %s value %r." % (moment, NOW_VARIABLE, override)
    )
    return moment


def blocked_message(moment):
    assert isinstance(moment, datetime), (
        "blocked_message needs a datetime but got %r. Rule: the message shows the clock time. "
        "Fix: pass the moment that push_allowed rejected." % (moment,)
    )
    assert not push_allowed(moment), (
        "blocked_message was called for %s, which is inside the window. Rule: only a blocked "
        "moment gets this message. Fix: call it only when push_allowed returns False." % moment
    )
    return (
        "push-window: it is %s and pushes are allowed from %02d:00 until %02d:%02d local time. "
        "Rule: push only after %02d:00 and before %02d:00. "
        "Fix: wait until %02d:00, then push again."
        % (moment.strftime("%H:%M"), OPENS_AT_HOUR, CLOSES_AT_HOUR - 1, LAST_ALLOWED_MINUTE,
           OPENS_AT_HOUR, CLOSES_AT_HOUR, OPENS_AT_HOUR)
    )


def main(environment):
    moment = current_moment(environment)
    allowed = push_allowed(moment)
    assert allowed in (True, False), (
        "push_allowed returned %r for %s. Rule: the window answers yes or no. "
        "Fix: return a bool from push_allowed." % (allowed, moment)
    )
    assert (moment.hour >= OPENS_AT_HOUR or moment.hour < CLOSES_AT_HOUR) == allowed, (
        "hour %r gave %r. Rule: allowed means hour >= %d or hour < %d. "
        "Fix: correct push_allowed." % (moment.hour, allowed, OPENS_AT_HOUR, CLOSES_AT_HOUR)
    )
    if allowed:
        return EXIT_ALLOWED
    print(blocked_message(moment), file=sys.stderr)
    return EXIT_BLOCKED


if __name__ == "__main__":
    sys.exit(main(os.environ))
