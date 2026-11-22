import sys

from willitharness.conformance import decision_mismatches, load_rows
from willitharness.decision import decide

EXIT_EQUAL = 0
EXIT_MISMATCH = 1


def main(decide_function):
    assert callable(decide_function), f"main needs a decision function, got {decide_function!r}. Fix: pass willitharness.decision.decide."
    rows = load_rows("decision")
    found = decision_mismatches(rows, decide_function)
    if found:
        sys.stderr.write(f"{found[0]}\n")
        return EXIT_MISMATCH
    print(f"{len(rows)} of {len(rows)} equal to the decision table")
    assert len(found) == 0, f"{len(found)} mismatches reached the success line"
    assert isinstance(rows, list) and rows, f"the decision table holds no rows, got {rows!r}"
    return EXIT_EQUAL


if __name__ == "__main__":
    raise SystemExit(main(decide))
