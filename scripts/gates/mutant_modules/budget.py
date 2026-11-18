TESTS = ("tests/unit/test_budget_unit.py", "tests/gates/test_budget_gate.py", "tests/bdd/test_budget_scenarios.py")

MUTANTS = (
    ("reserved-ignored", "src/willitharness/budget.py", "return spent_amount + reserved_amount + run_cap <= budget", "return spent_amount + run_cap <= budget"),
    ("budget-boundary-exclusive", "src/willitharness/budget.py", "return spent_amount + reserved_amount + run_cap <= budget", "return spent_amount + reserved_amount + run_cap < budget"),
    ("settle-not-capped", "src/willitharness/budget.py", "charged = min(to_money(cost_usd), self.run_cap)", "charged = to_money(cost_usd)"),
    ("reservation-never-released", "src/willitharness/budget.py", "            self.reserved -= self.run_cap\n", "            pass\n"),
    ("over-cap-run-kept-usable", "src/willitharness/budget.py", "    if cost > to_money(run_cap):\n", "    if False:\n"),
    ("timeout-charges-nothing", "src/willitharness/budget.py", "usable=dict(UNUSABLE_FLAGS), cost_usd=float(run_cap))\n\n\ndef abort_records", "usable=dict(UNUSABLE_FLAGS), cost_usd=0.0)\n\n\ndef abort_records"),
    ("abort-skips-runs", "src/willitharness/budget.py", "for started in in_flight_runs(records):", "for started in in_flight_runs(records)[:1]:"),
    ("no-lock-around-reserve", "src/willitharness/budget.py", "        with self.lock:\n            allowed =", "        if True:\n            allowed ="),
)
