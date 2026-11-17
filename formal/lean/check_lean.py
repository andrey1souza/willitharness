import json
import os
import re
import subprocess
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent
TOOLS = PROJECT.parent.parent / "tools" / "elan"
PROVEN_SOURCES = ["Willitharness.lean", "Export.lean", "Audit.lean"]
PROVEN_SOURCE_DIR = "Willitharness"
WRONG_SOURCE = PROJECT / "WrongVariants.lean"
AUDIT_SOURCE = PROJECT / "Audit.lean"
ALLOWED_AXIOMS = {"propext", "Classical.choice", "Quot.sound"}
BUILD_TIMEOUT_SECONDS = 900
ERROR_LINE = re.compile(r"^error: (?:\S*/)?WrongVariants\.lean:(\d+):\d+:", re.M)
THEOREM_LINE = re.compile(r"^theorem (\S+)", re.M)
WRONG_THEOREM_LINE = re.compile(r"^theorem (\w+)")
AXIOM_LINE = re.compile(r"^'([^']+)' (?:does not depend on any axioms|depends on axioms: \[(.*)\])")
FORBIDDEN_SOURCE_PATTERNS = {"sorry": re.compile(r"\bsorry\b"), "axiom declaration": re.compile(r"^\s*axiom\b", re.M),
                             "native_decide": re.compile(r"\bnative_decide\b")}

MIN_PROBE_RUNS = 3
MAX_PROBE_RUNS = 6
REACH = ["Loaded", "Masked", "Unknown"]
EFFECT = ["RuleLowersViolations", "NoMeasurableEffect", "RuleRaisesViolations", "NotEnoughRuns", "Invalid"]
GUARD = ["GuardMatchesRule", "GuardWorse", "GuardUntested"]
NOISE = ["NoiseUnmeasured", "NoiseFloorTooHigh", "NoiseOk"]
VERDICT = ["InconclusiveSmallN", "FirstHigher", "FirstLower", "Inconclusive"]
COMPLETED = ["NoGuardArm"] + VERDICT
BOOLEANS = [False, True]
EXPECTED_ROWS = {"decision": 45, "effect": 12, "probe": 140, "guard": 20}


def lean_environment():
    environment = dict(os.environ)
    environment["ELAN_HOME"] = str(TOOLS)
    environment["PATH"] = str(TOOLS / "bin") + os.pathsep + environment["PATH"]
    return environment


def run(arguments, timeout=BUILD_TIMEOUT_SECONDS):
    return subprocess.run(arguments, cwd=PROJECT, env=lean_environment(), capture_output=True, text=True, timeout=timeout)


def contract_decision(reach, effect, guard):
    if reach == "Masked":
        return "FixLoading"
    if reach == "Unknown":
        return "CannotDecide"
    if effect == "Invalid":
        return "CannotDecide"
    if effect == "NotEnoughRuns":
        return "NeedsMoreRuns"
    if effect in ("RuleRaisesViolations", "NoMeasurableEffect"):
        return "DeleteCandidate"
    return "ReplaceWithGuard" if guard == "GuardMatchesRule" else "Keep"


def contract_effect(noise, verdict):
    if noise != "NoiseOk":
        return "Invalid"
    return {"InconclusiveSmallN": "NotEnoughRuns", "FirstHigher": "RuleLowersViolations",
            "FirstLower": "RuleRaisesViolations", "Inconclusive": "NoMeasurableEffect"}[verdict]


def contract_probe(runs, target_hits, control_hits):
    if runs < MIN_PROBE_RUNS:
        return "Unknown"
    if control_hits > 0:
        return "Unknown"
    if target_hits == runs:
        return "Loaded"
    if target_hits == 0:
        return "Masked"
    return "Unknown"


def contract_guard(completed, full_coverage, zero_bypass):
    if completed == "NoGuardArm":
        return "GuardUntested"
    enough_and_not_lower = completed not in ("FirstLower", "InconclusiveSmallN")
    return "GuardMatchesRule" if enough_and_not_lower and full_coverage and zero_bypass else "GuardWorse"


def expected_rows(kind):
    if kind == "decision":
        return {(r, e, g): contract_decision(r, e, g) for r in REACH for e in EFFECT for g in GUARD}
    if kind == "effect":
        return {(n, v): contract_effect(n, v) for n in NOISE for v in VERDICT}
    if kind == "probe":
        return {(runs, t, c): contract_probe(runs, t, c) for runs in range(MAX_PROBE_RUNS + 1)
                for t in range(runs + 1) for c in range(runs + 1)}
    return {(cv, full, zero): contract_guard(cv, full, zero) for cv in COMPLETED for full in BOOLEANS for zero in BOOLEANS}


def row_key_and_value(kind, row):
    if kind == "decision":
        return (row["reach"], row["effect"], row["guard"]), row["decision"]
    if kind == "effect":
        return (row["noise"], row["verdict"]), row["effect"]
    if kind == "probe":
        return (row["runs"], row["targetHits"], row["controlHits"]), row["result"]
    return (row["completed"], row["blockCoverageFull"], row["bypassRateZero"]), row["guard"]


def proven_source_files():
    sources = [PROJECT / name for name in PROVEN_SOURCES]
    return sources + sorted((PROJECT / PROVEN_SOURCE_DIR).glob("*.lean"))


def theorem_names():
    names = []
    for source in sorted((PROJECT / PROVEN_SOURCE_DIR).glob("*.lean")):
        names += THEOREM_LINE.findall(source.read_text())
    return names


def write_audit_file(names):
    lines = ["import Willitharness", "", "open Willitharness", ""] + ["#print axioms " + name for name in names]
    AUDIT_SOURCE.write_text("\n".join(lines) + "\n")


def check_toolchain():
    result = run(["lean", "--version"])
    return "lean runs", "exit 0", result.stdout.strip() or result.stderr.strip(), result.returncode == 0


def check_build():
    result = run(["lake", "build"])
    warnings = len(re.findall(r"^warning:", result.stdout + result.stderr, re.M))
    outcome = "exit %d, %d warnings" % (result.returncode, warnings)
    return "lake build (proven libraries)", "exit 0, 0 warnings", outcome, result.returncode == 0 and warnings == 0


def check_forbidden_constructs():
    findings = []
    for source in proven_source_files():
        text = source.read_text()
        for label, pattern in FORBIDDEN_SOURCE_PATTERNS.items():
            if pattern.search(text):
                findings.append("%s in %s" % (label, source.name))
    return "no sorry, axiom declaration or native_decide", "none", ", ".join(findings) or "none", not findings


def check_axioms():
    names = theorem_names()
    write_audit_file(names)
    result = run(["lake", "env", "lean", "Audit.lean"])
    reported, disallowed = 0, []
    for line in result.stdout.splitlines():
        match = AXIOM_LINE.match(line)
        if not match:
            continue
        reported += 1
        used = {item.strip() for item in (match.group(2) or "").split(",") if item.strip()}
        disallowed += sorted(used - ALLOWED_AXIOMS)
    outcome = "%d of %d reported, disallowed: %s" % (reported, len(names), disallowed or "none")
    return "#print axioms covers every theorem, standard axioms only", "all reported, none disallowed", outcome, result.returncode == 0 and reported == len(names) and not disallowed


def check_table(kind):
    result = run(["lake", "exe", "export_table", kind])
    label = "%s_table.json matches an independent reading of contract v0.2" % kind
    expected = "%d rows, complete, 0 differences" % EXPECTED_ROWS[kind]
    if result.returncode != 0:
        return label, expected, "export exit %d" % result.returncode, False
    (PROJECT / ("%s_table.json" % kind)).write_text(result.stdout)
    rows = [row_key_and_value(kind, row) for row in json.loads(result.stdout)]
    wanted = expected_rows(kind)
    keys = [key for key, _ in rows]
    differences = [key for key, value in rows if wanted.get(key) != value]
    complete = len(keys) == len(set(keys)) and set(keys) == set(wanted)
    outcome = "%d rows, complete=%s, differences: %d" % (len(rows), complete, len(differences))
    return label, expected, outcome, len(rows) == EXPECTED_ROWS[kind] and complete and not differences


def wrong_theorem_ranges():
    lines = WRONG_SOURCE.read_text().splitlines()
    starts = [(index + 1, WRONG_THEOREM_LINE.match(line).group(1)) for index, line in enumerate(lines) if WRONG_THEOREM_LINE.match(line)]
    bounds = [start for start, _ in starts] + [len(lines) + 1]
    return [(name, bounds[position], bounds[position + 1] - 1) for position, (_, name) in enumerate(starts)]


def check_wrong_variants():
    result = run(["lake", "build", "WrongVariants"])
    error_lines = [int(match.group(1)) for match in ERROR_LINE.finditer(result.stdout + result.stderr)]
    ranges = wrong_theorem_ranges()
    unfailed = [name for name, first, last in ranges if not any(first <= line <= last for line in error_lines)]
    outcome = "exit %d, %d wrong theorems, not failing: %s" % (result.returncode, len(ranges), unfailed or "none")
    return "every deliberately wrong theorem fails", "build fails, each wrong theorem has an error", outcome, result.returncode != 0 and bool(ranges) and not unfailed


def main():
    checks = [check_toolchain, check_build, check_forbidden_constructs, check_axioms,
              lambda: check_table("decision"), lambda: check_table("effect"),
              lambda: check_table("probe"), lambda: check_table("guard"), check_wrong_variants]
    rows = [check() for check in checks]
    print("%-66s %-40s %s" % ("check", "expected", "actual"))
    for name, expected, actual, passed in rows:
        print("%-66s %-40s %s [%s]" % (name, expected, actual, "OK" if passed else "MISMATCH"))
    return 0 if all(passed for *_, passed in rows) else 1


if __name__ == "__main__":
    sys.exit(main())
