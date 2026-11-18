import math
import threading
from decimal import Decimal

import pytest

from willitharness.budget import Ledger, abort_records, budget_allows_start, capped_record, timed_out_record, to_money
from willitharness.store import Record, RunState, in_flight_runs, spent

CAP = 0.02
BUDGET = 0.10
WAIT_SECONDS = 0.3


def started(index):
    return Record(f"B/t/{index}#1", "B", "t", index, 1, RunState.STARTED, {}, 0.0)


def usable(index, cost):
    return Record(f"B/t/{index}#1", "B", "t", index, 1, RunState.RECORDED_USABLE, {"attempted_violation": True, "completed": True}, cost)


def test_a_negative_cost_is_rejected_with_the_fix():
    with pytest.raises(AssertionError) as raised:
        to_money(-0.01)
    assert "cannot be negative" in str(raised.value) and "Fix:" in str(raised.value), f"unexpected message {str(raised.value)!r}"


def test_a_boolean_is_not_money():
    with pytest.raises(AssertionError) as raised:
        to_money(True)
    assert "must be a number" in str(raised.value), f"unexpected message {str(raised.value)!r}"


def test_a_start_that_exactly_reaches_the_budget_is_allowed():
    assert budget_allows_start(to_money(0.03), to_money(0), to_money(CAP), to_money(0.05)), f"0.03 spent plus {CAP} cap reaches 0.05 and must be allowed"


def test_a_start_that_passes_the_budget_by_a_cent_is_refused():
    assert not budget_allows_start(to_money(0.04), to_money(0), to_money(CAP), to_money(0.05)), f"0.04 spent plus {CAP} cap passes 0.05 and must be refused"


def test_reservations_count_against_the_budget_before_any_run_is_recorded():
    ledger = Ledger(BUDGET, CAP)
    allowed = [ledger.reserve() for _ in range(6)]
    assert allowed == [True, True, True, True, True, False], f"five reservations of 0.02 fit in 0.10 and the sixth must not, got {allowed}"


def test_a_record_replaces_the_reservation_with_the_real_cost():
    ledger = Ledger(BUDGET, CAP)
    ledger.reserve()
    charged = ledger.settle(0.01)
    assert (ledger.reserved, ledger.spent, charged) == (Decimal("0.00"), Decimal("0.01"), Decimal("0.01")), f"got {ledger.reserved}, {ledger.spent}, {charged}"


def test_a_cost_above_the_cap_is_charged_at_the_cap():
    ledger = Ledger(BUDGET, CAP)
    ledger.reserve()
    assert ledger.settle(0.05) == Decimal("0.02"), "an over-cap cost must be charged at RUN_CAP"


def test_settling_without_a_reservation_is_rejected_with_the_fix():
    ledger = Ledger(BUDGET, CAP)
    with pytest.raises(AssertionError) as raised:
        ledger.settle(0.01)
    assert "call reserve before settle" in str(raised.value), f"unexpected message {str(raised.value)!r}"


def test_a_run_over_the_cap_is_recorded_unusable_with_the_cost_at_the_cap():
    record = capped_record(started(1), RunState.RECORDED_USABLE, 0.05, CAP)
    assert (record.state, record.cost_usd, record.usable) == (RunState.RECORDED_UNUSABLE, CAP, {"attempted_violation": False, "completed": False}), f"got {record}"


def test_a_run_under_the_cap_keeps_its_state_and_cost():
    record = capped_record(started(1), RunState.RECORDED_USABLE, 0.01, CAP)
    assert (record.state, record.cost_usd) == (RunState.RECORDED_USABLE, 0.01), f"got {record}"


def test_a_timed_out_run_is_unusable_and_charges_the_full_cap():
    record = timed_out_record(started(1), CAP)
    assert (record.state, record.cost_usd) == (RunState.RECORDED_UNUSABLE, CAP), f"got {record}"


def test_an_abort_records_every_in_flight_run_unusable_and_charges_the_cap_for_each():
    records = (usable(0, 0.10), started(1), started(2), started(3))
    updated = abort_records(records, CAP)
    assert not in_flight_runs(updated), f"runs are still in flight: {in_flight_runs(updated)}"
    assert math.isclose(spent(updated), 0.16), f"0.10 recorded plus 3 times 0.02 must be 0.16, got {spent(updated)}"


def test_an_abort_with_nothing_in_flight_changes_nothing():
    records = (usable(0, 0.10),)
    assert abort_records(records, CAP) == records, "an abort with no run in flight must not change the records"


def test_a_reservation_waits_while_another_runner_holds_the_lock():
    ledger = Ledger(BUDGET, CAP)
    entered = threading.Event()
    outcome = []

    def reserve_when_free():
        entered.set()
        outcome.append(ledger.reserve())

    with ledger.lock:
        worker = threading.Thread(target=reserve_when_free)
        worker.start()
        entered.wait()
        worker.join(timeout=WAIT_SECONDS)
        assert worker.is_alive(), f"reserve finished while the lock was held, outcome {outcome}. Rule: spent plus reserved is checked and raised under one lock."
    worker.join()
    assert outcome == [True], f"after the lock was released reserve must succeed, got {outcome}"
