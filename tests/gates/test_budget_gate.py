import threading
from decimal import Decimal

from willitharness.budget import Ledger

RUNNERS = 4
CYCLES = 25
BUDGET = 0.10
CAP = 0.02
REAL_COST = 0.01
BUDGET_AS_MONEY = Decimal("0.10")


def test_four_parallel_runners_never_push_spent_plus_reserved_over_the_budget():
    ledger = Ledger(BUDGET, CAP)
    highest = []

    def runner():
        for _ in range(CYCLES):
            if ledger.reserve():
                highest.append(ledger.spent + ledger.reserved)
                ledger.settle(REAL_COST)

    threads = [threading.Thread(target=runner) for _ in range(RUNNERS)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert highest, "no run started at all"
    assert max(highest) <= BUDGET_AS_MONEY, f"spent plus reserved reached {max(highest)} above {BUDGET_AS_MONEY}"
    assert ledger.spent <= BUDGET_AS_MONEY and ledger.reserved == 0, f"the end state was spent {ledger.spent}, reserved {ledger.reserved}"
