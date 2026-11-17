import json
import sys
from collections.abc import Callable
from pathlib import Path

from willitharness.decision import decide
from willitharness.effect import map_effect
from willitharness.guard import evaluate
from willitharness.probe import classify
from willitharness.vocabulary import Decision, EffectResult, GuardResult, NoiseStatus, Reach, Verdict

GOLDEN_DIRECTORY = Path(__file__).resolve().parents[2] / "formal" / "lean"
NO_GUARD_ARM = "NoGuardArm"
USAGE_EXIT_CODE = 2
MISMATCH_EXIT_CODE = 1
CONFORMS_EXIT_CODE = 0
KNOWN_EXIT_CODES = frozenset({USAGE_EXIT_CODE, MISMATCH_EXIT_CODE, CONFORMS_EXIT_CODE})
FILE_BY_KIND = {
    "decision": "decision_table.json",
    "effect": "effect_table.json",
    "probe": "probe_table.json",
    "guard": "guard_table.json",
}


def load_rows(kind: str, directory: Path | None = None) -> list[dict]:
    assert kind in FILE_BY_KIND, f"unknown table kind {kind!r}, expected one of {sorted(FILE_BY_KIND)}"
    folder = directory or GOLDEN_DIRECTORY
    assert folder.is_dir(), f"golden directory missing: {folder}"
    rows = json.loads((folder / FILE_BY_KIND[kind]).read_text())
    assert isinstance(rows, list) and rows, f"{kind} table must be a non-empty list, got {type(rows).__name__}"
    return rows


def decision_mismatches(rows: list[dict], decide_function: Callable = decide) -> list[str]:
    assert rows, f"no decision rows to check, got {rows!r}"
    assert all({"reach", "effect", "guard", "decision"} <= row.keys() for row in rows), (
        f"decision rows are incomplete: {rows[:1]!r}"
    )
    found = []
    for row in rows:
        got = decide_function(Reach(row["reach"]), EffectResult(row["effect"]), GuardResult(row["guard"]))
        if got != Decision(row["decision"]):
            found.append(f"decision {row}: got {got}")
    return found


def effect_mismatches(rows: list[dict], effect_function: Callable = map_effect) -> list[str]:
    assert rows, f"no effect rows to check, got {rows!r}"
    assert all({"noise", "verdict", "effect"} <= row.keys() for row in rows), f"effect rows are incomplete: {rows[:1]!r}"
    found = []
    for row in rows:
        got = effect_function(NoiseStatus(row["noise"]), Verdict(row["verdict"]))
        if got != EffectResult(row["effect"]):
            found.append(f"effect {row}: got {got}")
    return found


def probe_mismatches(rows: list[dict], classify_function: Callable = classify) -> list[str]:
    assert rows, f"no probe rows to check, got {rows!r}"
    assert all({"runs", "targetHits", "controlHits", "result"} <= row.keys() for row in rows), (
        f"probe rows are incomplete: {rows[:1]!r}"
    )
    found = []
    for row in rows:
        got = classify_function(row["runs"], row["targetHits"], row["controlHits"])
        if got != Reach(row["result"]):
            found.append(f"probe {row}: got {got}")
    return found


def guard_mismatches(rows: list[dict], evaluate_function: Callable = evaluate) -> list[str]:
    assert rows, f"no guard rows to check, got {rows!r}"
    assert all({"completed", "blockCoverageFull", "bypassRateZero", "guard"} <= row.keys() for row in rows), (
        f"guard rows are incomplete: {rows[:1]!r}"
    )
    found = []
    for row in rows:
        completed = None if row["completed"] == NO_GUARD_ARM else Verdict(row["completed"])
        got = evaluate_function(completed, row["blockCoverageFull"], row["bypassRateZero"])
        if got != GuardResult(row["guard"]):
            found.append(f"guard {row}: got {got}")
    return found


MISMATCH_FUNCTION_BY_KIND = {
    "decision": decision_mismatches,
    "effect": effect_mismatches,
    "probe": probe_mismatches,
    "guard": guard_mismatches,
}


def run_kind(kind: str, directory: Path | None = None) -> tuple[str, int]:
    assert kind in FILE_BY_KIND, f"unknown table kind {kind!r}, expected one of {sorted(FILE_BY_KIND)}"
    rows = load_rows(kind, directory)
    found = MISMATCH_FUNCTION_BY_KIND[kind](rows)
    code = MISMATCH_EXIT_CODE if found else CONFORMS_EXIT_CODE
    message = "\n".join(found) if found else f"{kind} table conforms: {len(rows)} cases"
    assert (code == CONFORMS_EXIT_CODE) == (not found), f"exit code {code} disagrees with {len(found)} mismatches"
    assert message, f"a {kind} run must print something, got {message!r}"
    return message, code


def main(arguments: list[str]) -> int:
    kind = arguments[0] if arguments else ""
    if kind not in FILE_BY_KIND:
        sys.stderr.write(f"usage: conformance <{'|'.join(FILE_BY_KIND)}> [directory], got {arguments!r}\n")
        return USAGE_EXIT_CODE
    directory = Path(arguments[1]) if len(arguments) > 1 else None
    message, code = run_kind(kind, directory)
    stream = sys.stdout if code == CONFORMS_EXIT_CODE else sys.stderr
    stream.write(message + "\n")
    assert code in KNOWN_EXIT_CODES, f"unexpected exit code {code}, expected one of {sorted(KNOWN_EXIT_CODES)}"
    assert stream.writable(), f"the output stream for exit code {code} must be writable"
    return code


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
