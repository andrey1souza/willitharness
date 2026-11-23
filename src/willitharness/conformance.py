import json
import sys
from collections.abc import Callable
from pathlib import Path

from willitharness.analysis import PlanFacts, can_report
from willitharness.decision import decide
from willitharness.effect import map_effect
from willitharness.guard import evaluate
from willitharness.probe import classify
from willitharness.placebo import content_verdict_from
from willitharness.three_arm import arm_verdict_from
from willitharness.vocabulary import ArmVerdict, ContentVerdict, Coverage, Decision, EffectResult, GuardResult, NoiseStatus, Reach, Verdict

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
    "reported": "reported_table.json",
    "arms": "arms_table.json",
    "placebo": "placebo_table.json",
}


def table_file(kind: str, source: Path | None) -> Path:
    assert kind in FILE_BY_KIND, f"unknown table kind {kind!r}, expected one of {sorted(FILE_BY_KIND)}"
    target = source if source is not None else GOLDEN_DIRECTORY
    resolved = target / FILE_BY_KIND[kind] if target.is_dir() else target
    assert resolved.is_file(), f"{kind} table missing: {resolved}. Rule: pass the table file or the folder that holds it."
    return resolved


def load_rows(kind: str, source: Path | None = None) -> list[dict]:
    assert kind in FILE_BY_KIND, f"unknown table kind {kind!r}, expected one of {sorted(FILE_BY_KIND)}"
    rows = json.loads(table_file(kind, source).read_text())
    assert isinstance(rows, list) and rows, f"{kind} table must be a non-empty list, got {type(rows).__name__}"
    return rows


def decision_mismatches(rows: list[dict], decide_function: Callable = decide) -> list[str]:
    assert rows, f"no decision rows to check, got {rows!r}"
    assert all({"reach", "effect", "guard", "decision"} <= row.keys() for row in rows), (
        f"decision rows are incomplete: {rows[:1]!r}"
    )
    found = []
    for row in rows:
        try:
            got = decide_function(Reach(row["reach"]), EffectResult(row["effect"]), GuardResult(row["guard"]))
            expected = Decision(row["decision"])
        except ValueError as error:
            found.append(f"decision {row}: {error}")
            continue
        if got != expected:
            found.append(f"decision {row}: lean={expected} python={got}")
    return found


def effect_mismatches(rows: list[dict], effect_function: Callable = map_effect) -> list[str]:
    assert rows, f"no effect rows to check, got {rows!r}"
    assert all({"noise", "verdict", "effect"} <= row.keys() for row in rows), f"effect rows are incomplete: {rows[:1]!r}"
    found = []
    for row in rows:
        try:
            got = effect_function(NoiseStatus(row["noise"]), Verdict(row["verdict"]))
            expected = EffectResult(row["effect"])
        except ValueError as error:
            found.append(f"effect {row}: {error}")
            continue
        if got != expected:
            found.append(f"effect {row}: lean={expected} python={got}")
    return found


def probe_mismatches(rows: list[dict], classify_function: Callable = classify) -> list[str]:
    assert rows, f"no probe rows to check, got {rows!r}"
    assert all({"runs", "targetHits", "controlHits", "result"} <= row.keys() for row in rows), (
        f"probe rows are incomplete: {rows[:1]!r}"
    )
    found = []
    for row in rows:
        got = classify_function(row["runs"], row["targetHits"], row["controlHits"])
        try:
            expected = Reach(row["result"])
        except ValueError as error:
            found.append(f"probe {row}: {error}")
            continue
        if got != expected:
            found.append(f"probe {row}: lean={expected} python={got}")
    return found


def guard_mismatches(rows: list[dict], evaluate_function: Callable = evaluate) -> list[str]:
    assert rows, f"no guard rows to check, got {rows!r}"
    assert all({"completed", "coverage", "bypassRateZero", "guard"} <= row.keys() for row in rows), (
        f"guard rows are incomplete: {rows[:1]!r}"
    )
    found = []
    for row in rows:
        try:
            completed = None if row["completed"] == NO_GUARD_ARM else Verdict(row["completed"])
            got = evaluate_function(completed, Coverage(row["coverage"]), row["bypassRateZero"])
            expected = GuardResult(row["guard"])
        except ValueError as error:
            found.append(f"guard {row}: {error}")
            continue
        if got != expected:
            found.append(f"guard {row}: lean={expected} python={got}")
    return found


def reported_mismatches(rows: list[dict], report_function: Callable = can_report) -> list[str]:
    assert rows, f"no reported rows to check, got {rows!r}"
    assert all({"hasNoisePair", "noise", "looProbe", "ruleReach", "canReport"} <= row.keys() for row in rows), (
        f"reported rows are incomplete: {rows[:1]!r}"
    )
    found = []
    for row in rows:
        try:
            facts = PlanFacts(row["hasNoisePair"], NoiseStatus(row["noise"]), Reach(row["looProbe"]), Reach(row["ruleReach"]))
        except ValueError as error:
            found.append(f"reported {row}: {error}")
            continue
        got = report_function(facts)
        if got != row["canReport"]:
            found.append(f"reported {row}: lean={row['canReport']} python={got}")
    return found


def arms_mismatches(rows: list[dict], arms_function: Callable = arm_verdict_from) -> list[str]:
    assert rows, f"no arms rows to check, got {rows!r}"
    assert all({"promptVsComponent", "nothingVsComponent", "nothingClean", "verdict"} <= row.keys() for row in rows), (
        f"arms rows are incomplete: {rows[:1]!r}"
    )
    found = []
    for row in rows:
        try:
            got = arms_function(Verdict(row["promptVsComponent"]), Verdict(row["nothingVsComponent"]), row["nothingClean"])
            expected = ArmVerdict(row["verdict"])
        except ValueError as error:
            found.append(f"arms {row}: {error}")
            continue
        if got != expected:
            found.append(f"arms {row}: lean={expected} python={got}")
    return found


def placebo_mismatches(rows: list[dict], placebo_function: Callable = content_verdict_from) -> list[str]:
    assert rows, f"no placebo rows to check, got {rows!r}"
    assert all({"placeboVsComponent", "nothingVsPlacebo", "nothingVsComponent", "nothingClean", "verdict"} <= row.keys() for row in rows), (
        f"placebo rows are incomplete: {rows[:1]!r}"
    )
    found = []
    for row in rows:
        try:
            got = placebo_function(Verdict(row["placeboVsComponent"]), Verdict(row["nothingVsPlacebo"]), Verdict(row["nothingVsComponent"]), row["nothingClean"])
            expected = ContentVerdict(row["verdict"])
        except ValueError as error:
            found.append(f"placebo {row}: {error}")
            continue
        if got != expected:
            found.append(f"placebo {row}: lean={expected} python={got}")
    return found


MISMATCH_FUNCTION_BY_KIND = {
    "decision": decision_mismatches,
    "effect": effect_mismatches,
    "probe": probe_mismatches,
    "guard": guard_mismatches,
    "reported": reported_mismatches,
    "arms": arms_mismatches,
    "placebo": placebo_mismatches,
}


def run_kind(kind: str, source: Path | None = None) -> tuple[str, int]:
    assert kind in FILE_BY_KIND, f"unknown table kind {kind!r}, expected one of {sorted(FILE_BY_KIND)}"
    rows = load_rows(kind, source)
    found = MISMATCH_FUNCTION_BY_KIND[kind](rows)
    code = MISMATCH_EXIT_CODE if found else CONFORMS_EXIT_CODE
    message = "\n".join(found) if found else f"{kind} table conforms: {len(rows)} cases"
    assert (code == CONFORMS_EXIT_CODE) == (not found), f"exit code {code} disagrees with {len(found)} mismatches"
    assert message, f"a {kind} run must print something, got {message!r}"
    return message, code


def main(arguments: list[str]) -> int:
    kind = arguments[0] if arguments else ""
    if kind not in FILE_BY_KIND:
        sys.stderr.write(f"usage: conformance <{'|'.join(FILE_BY_KIND)}> [table-file], got {arguments!r}\n")
        return USAGE_EXIT_CODE
    source = Path(arguments[1]) if len(arguments) > 1 else None
    message, code = run_kind(kind, source)
    stream = sys.stdout if code == CONFORMS_EXIT_CODE else sys.stderr
    stream.write(message + "\n")
    assert code in KNOWN_EXIT_CODES, f"unexpected exit code {code}, expected one of {sorted(KNOWN_EXIT_CODES)}"
    assert stream.writable(), f"the output stream for exit code {code} must be writable"
    return code


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
