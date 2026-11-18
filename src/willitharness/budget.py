import threading
from dataclasses import replace
from decimal import Decimal

from willitharness.store import Record, RunState, in_flight_runs, with_record

UNUSABLE_FLAGS = {"attempted_violation": False, "completed": False}


def to_money(value):
    assert isinstance(value, (int, float, str, Decimal)) and not isinstance(value, bool), f"a cost must be a number, got {value!r}. Fix: pass a float, int or Decimal."
    amount = Decimal(str(value))
    assert amount >= 0, f"a cost cannot be negative, got {amount}. Rule: money only goes out. Fix: record the cost as 0 or more."
    return amount


def budget_allows_start(spent_amount, reserved_amount, run_cap, budget):
    assert min(spent_amount, reserved_amount, run_cap, budget) >= 0, f"amounts must not be negative: {spent_amount}, {reserved_amount}, {run_cap}, {budget}"
    assert run_cap > 0 and budget > 0, f"RUN_CAP {run_cap} and the budget {budget} must be above 0. Fix: set both in the plan."
    return spent_amount + reserved_amount + run_cap <= budget


class Ledger:
    def __init__(self, budget_usd, run_cap_usd):
        assert budget_usd > 0, f"the budget is {budget_usd!r}. Rule: a plan has a budget above 0. Fix: set budget_usd in the plan."
        self.budget = to_money(budget_usd)
        self.run_cap = to_money(run_cap_usd)
        assert self.run_cap > 0 and self.run_cap <= self.budget, f"RUN_CAP {self.run_cap} must be above 0 and at most the budget {self.budget}. Fix: correct the plan."
        self.spent = Decimal(0)
        self.reserved = Decimal(0)
        self.lock = threading.Lock()

    def reserve(self):
        with self.lock:
            allowed = budget_allows_start(self.spent, self.reserved, self.run_cap, self.budget)
            reserved_before = self.reserved
            if allowed:
                self.reserved += self.run_cap
            assert self.reserved - reserved_before in (0, self.run_cap), f"reserve changed reserved by {self.reserved - reserved_before}. Rule: a start reserves exactly RUN_CAP or nothing."
            assert self.spent + self.reserved <= self.budget, f"L2 broken: spent {self.spent} plus reserved {self.reserved} exceeds the budget {self.budget}"
            return allowed

    def settle(self, cost_usd):
        charged = min(to_money(cost_usd), self.run_cap)
        with self.lock:
            assert self.reserved >= self.run_cap, f"settle was called with {self.reserved} reserved. Rule: every settled run first reserved RUN_CAP. Fix: call reserve before settle."
            self.reserved -= self.run_cap
            self.spent += charged
            assert self.spent + self.reserved <= self.budget, f"L2 broken: spent {self.spent} plus reserved {self.reserved} exceeds the budget {self.budget}"
        return charged


def capped_record(started, state, cost_usd, run_cap):
    assert started.state is RunState.STARTED, f"capped_record needs a Started run, got {started.state}. Fix: pass the record written at the start."
    assert state in (RunState.RECORDED_USABLE, RunState.RECORDED_UNUSABLE), f"a run ends usable or unusable, got {state}. Fix: pass one of them."
    cost = to_money(cost_usd)
    if cost > to_money(run_cap):
        return replace(started, state=RunState.RECORDED_UNUSABLE, usable=dict(UNUSABLE_FLAGS), outcome={}, cost_usd=float(run_cap))
    return replace(started, state=state, cost_usd=float(cost))


def timed_out_record(started, run_cap):
    assert started.state is RunState.STARTED, f"timed_out_record needs a Started run, got {started.state}. Fix: pass the record written at the start."
    assert run_cap > 0, f"RUN_CAP is {run_cap}. Rule: a timeout charges the full RUN_CAP. Fix: set RUN_CAP above 0."
    return replace(started, state=RunState.RECORDED_UNUSABLE, usable=dict(UNUSABLE_FLAGS), cost_usd=float(run_cap))


def abort_records(records, run_cap):
    assert isinstance(records, tuple), f"abort_records needs a tuple of records, got {type(records).__name__}. Fix: pass load_records output."
    assert run_cap > 0, f"RUN_CAP is {run_cap}. Rule: an abort charges RUN_CAP for each in-flight run. Fix: set RUN_CAP above 0."
    updated = records
    for started in in_flight_runs(records):
        updated = with_record(updated, timed_out_record(started, run_cap))
    assert not in_flight_runs(updated), f"runs are still in flight after the abort: {in_flight_runs(updated)}"
    assert all(isinstance(record, Record) for record in updated), f"the abort returned a non-record among {updated!r}. Rule: abort returns store records. Fix: build them with timed_out_record."
    return updated
