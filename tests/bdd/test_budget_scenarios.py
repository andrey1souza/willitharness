import threading
from decimal import Decimal

from pytest_bdd import given, parsers, scenario, then, when

from willitharness.budget import Ledger, capped_record, timed_out_record
from willitharness.store import Record, RunState, in_flight_runs, with_record

FEATURE = "../../features/budget-and-resume.feature"
CAP = 0.02


def started_run():
    return Record("B/stop-server/1", "B", "stop-server", 1, 1, RunState.STARTED, {}, 0.0)


@scenario(FEATURE, "A record replaces the reservation with the real cost")
def test_a_record_replaces_the_reservation(world):
    assert world["ledger"].reserved == 0 and world["ledger"].spent == Decimal("0.01"), f"reserved {world['ledger'].reserved}, spent {world['ledger'].spent}. Rule: L2. Fix: settle replaces the reservation."


@scenario(FEATURE, "Parallel runners cannot overspend")
def test_parallel_runners_cannot_overspend(world):
    assert float(world["ledger"].spent) <= 0.10, f"spent {world['ledger'].spent}. Rule: L2. Fix: reserve under one lock."


@scenario(FEATURE, "A run whose cost would exceed RUN_CAP is ended and recorded unusable")
def test_a_run_over_the_cap_is_ended(world):
    assert world["record"].state is RunState.RECORDED_UNUSABLE, f"state {world['record'].state}. Rule: A-CAP. Fix: record an over-cap run as unusable."


@scenario(FEATURE, "A timed-out run still ends")
def test_a_timed_out_run_still_ends(world):
    assert not in_flight_runs(world["records"]), f"runs still in flight: {in_flight_runs(world['records'])}. Rule: T1. Fix: a timeout records the run."


@given(parsers.parse("a plan with a fake agent that costs {cost:f} per run"))
def plan_with_fake_agent_cost(world, cost):
    world["cost_per_run"] = cost


@given(parsers.parse("RUN_CAP is {cap:f}"))
def run_cap_is(world, cap):
    assert cap == CAP, f"the scenarios in this file assume RUN_CAP {CAP}, the feature says {cap}"
    world["run_cap"] = cap


@given(parsers.parse("a started run that reserved {amount:f}"))
def run_that_reserved(world, amount):
    world["ledger"] = Ledger(1.00, amount)
    world["ledger"].reserve()
    world["before"] = (world["ledger"].reserved, world["ledger"].spent)


@when(parsers.parse("the run is recorded with a real cost of {cost:f}"))
def run_recorded_with_cost(world, cost):
    world["ledger"].settle(cost)


@then(parsers.parse("reserved falls by {amount:f}"))
def reserved_falls(world, amount):
    fell = world["before"][0] - world["ledger"].reserved
    assert float(fell) == amount, f"reserved fell by {fell}, expected {amount}"


@then(parsers.parse("spent rises by {amount:f}"))
def spent_rises(world, amount):
    rose = world["ledger"].spent - world["before"][1]
    assert float(rose) == amount, f"spent rose by {rose}, expected {amount}"


@given(parsers.parse("a budget of {budget:f} and {runners:d} parallel runners"))
def budget_and_runners(world, budget, runners):
    world["ledger"] = Ledger(budget, CAP)
    world["budget"], world["runners"] = budget, runners
    world["highest"] = []


@given("reserved is RUN_CAP times the number of started, unrecorded runs")
def reserved_definition(world):
    probe = Ledger(world["budget"], CAP)
    probe.reserve()
    assert float(probe.reserved) == CAP, f"one started run must reserve RUN_CAP {CAP}, reserved {probe.reserved}"


@when("I run the plan")
def run_the_plan(world):
    ledger, highest = world["ledger"], world["highest"]
    cost = world["cost_per_run"]

    def runner():
        for _ in range(25):
            if ledger.reserve():
                highest.append(ledger.spent + ledger.reserved)
                ledger.settle(cost)

    threads = [threading.Thread(target=runner) for _ in range(world["runners"])]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()


@then(parsers.parse("spent plus reserved never exceeds {budget:f} at any moment"))
def never_exceeds(world, budget):
    assert world["highest"] and float(max(world["highest"])) <= budget, f"highest {world['highest'][-3:]} against {budget}"


@then(parsers.parse("the recorded spend at the end is at most {budget:f}"))
def spend_at_most(world, budget):
    assert float(world["ledger"].spent) <= budget, f"spent {world['ledger'].spent} above {budget}"


@given("a run that would cost more than RUN_CAP")
def run_over_the_cap(world):
    world["run"] = started_run()
    world["cost"] = 0.05


@when("the runner enforces the cap")
def runner_enforces_the_cap(world):
    world["record"] = capped_record(world["run"], RunState.RECORDED_USABLE, world["cost"], CAP)


@then(parsers.parse('the run state is "{state}"'))
def run_state_is(world, state):
    assert world["record"].state.value == state, f"expected {state}, got {world['record'].state}"


@then(parsers.parse("the recorded cost is at most {cap:f}"))
def recorded_cost_at_most(world, cap):
    assert world["record"].cost_usd <= cap, f"cost {world['record'].cost_usd} above {cap}"


@given("a run that exceeds the run timeout")
def run_over_the_timeout(world):
    world["run"] = started_run()
    world["records"] = (world["run"],)


@when("the timeout fires")
def the_timeout_fires(world):
    world["record"] = timed_out_record(world["run"], CAP)
    world["records"] = with_record(world["records"], world["record"])


@then(parsers.parse('no run stays in the state "{state}"'))
def no_run_stays(world, state):
    assert state == RunState.STARTED.value and not in_flight_runs(world["records"]), f"runs still {state}: {in_flight_runs(world['records'])}"
