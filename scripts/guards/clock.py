from datetime import datetime

NOW_VARIABLE = "WILLITHARNESS_NOW"


def current_moment(environment):
    override = environment.get(NOW_VARIABLE)
    assert override is None or override.strip(), (
        "%s is set to %r. Rule: the override must be an ISO time or unset. "
        "Fix: unset the variable or give a value such as 2026-11-17T20:00:00." % (NOW_VARIABLE, override)
    )
    moment = datetime.fromisoformat(override) if override else datetime.now()
    assert isinstance(moment, datetime), (
        "current_moment built %r instead of a datetime. Rule: callers read the time. "
        "Fix: check the %s value %r." % (moment, NOW_VARIABLE, override)
    )
    return moment
