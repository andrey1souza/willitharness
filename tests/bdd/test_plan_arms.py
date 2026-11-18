import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from willitharness.plan import PlanError, load_plan

scenarios("../../features/plan-arms.feature")

BASE_PLAN = {"schema": 1, "name": "channels", "budget_usd": 2.0, "run_cap_usd": 0.5}


@given(parsers.parse('a plan with a leave-one-out arm "{label}"'))
def plan_with_loo_arm(world, label):
    world["arms"] = [{"label": label, "role": "leave_one_out", "overlay": f"arms/{label}"}]


@given(parsers.parse('a rule arm "{label}" with no channel'))
def rule_arm_without_channel(world, label):
    world["arms"].append({"label": label, "role": "rule", "overlay": f"arms/{label}"})


@given(parsers.parse('a rule arm "{label}" with the channel "{channel}"'))
def rule_arm_with_channel(world, label, channel):
    world["arms"].append({"label": label, "role": "rule", "overlay": f"arms/{label}", "channel": channel})


@when("I load the plan")
def load_the_plan(world):
    try:
        world["plan"] = load_plan({**BASE_PLAN, "arms": world["arms"]})
        world["message"] = ""
    except PlanError as error:
        world["plan"] = None
        world["message"] = str(error)


@then(parsers.parse('the arm "{label}" has the channel "{channel}"'))
def arm_has_channel(world, label, channel):
    assert world["plan"] is not None, f"the plan was rejected: {world['message']}"
    found = {arm.label: arm.channel for arm in world["plan"].arms}
    assert found[label] == channel, f"expected {channel} for {label}, got {found}"


@then("the plan is rejected")
def plan_is_rejected(world):
    assert world["plan"] is None, f"the plan must be rejected, got {world['plan']}"
