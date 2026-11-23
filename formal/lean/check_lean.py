import hashlib
import json
import os
import platform
import re
import subprocess
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent
TOOLS = Path(os.environ.get("WILLITHARNESS_ELAN_HOME", Path.home() / ".cache" / "willitharness" / "elan"))
PROVEN_SOURCES = ["Willitharness.lean", "Export.lean", "Audit.lean"]
PROVEN_SOURCE_DIR = "Willitharness"
WRONG_SOURCE = PROJECT / "WrongVariants.lean"
AUDIT_SOURCE = PROJECT / "Audit.lean"
TOOLCHAIN_FILE = PROJECT / "lean-toolchain"
PINNED_BINARY_SHA256 = {
    ("Darwin", "arm64"): {
        "lean": "a4c5d3dfc1672faf014e59bd17724035259ff0d22a4ffbdf5a75e142f564817e",
        "lake": "a0e516de0ba03a26cb90c80f06666022ef9de3f0943f8b26e9b902d229b43ebe",
    },
}
ALLOWED_AXIOMS = {"propext", "Classical.choice", "Quot.sound"}
BUILD_TIMEOUT_SECONDS = 900
CONTRACT_VERSION = "v0.3"
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
COVERAGE = ["Full", "Partial", "NoneSeen"]
BOOLEANS = [False, True]
EXPECTED_ROWS = {"decision": 45, "effect": 12, "probe": 140, "guard": 30, "reported": 54, "arms": 32}
TABLE_KINDS = tuple(EXPECTED_ROWS)


def lean_environment():
    assert TOOLS.is_dir(), f"the Lean tools folder {TOOLS} is missing. Rule: the checker runs the installed toolchain. Fix: install elan there or set WILLITHARNESS_ELAN_HOME."
    environment = dict(os.environ)
    environment["ELAN_HOME"] = str(TOOLS)
    environment["PATH"] = str(TOOLS / "bin") + os.pathsep + environment["PATH"]
    assert environment["PATH"].startswith(str(TOOLS / "bin")), f"the Lean binaries are not first on PATH: {environment['PATH']}"
    return environment


def run(arguments):
    assert arguments and all(isinstance(item, str) for item in arguments), f"run needs a non-empty list of text arguments, got {arguments!r}. Fix: pass the command as a list of strings."
    assert BUILD_TIMEOUT_SECONDS > 0, f"the timeout must be above 0 seconds, got {BUILD_TIMEOUT_SECONDS}. Fix: set BUILD_TIMEOUT_SECONDS."
    result = subprocess.run(arguments, cwd=PROJECT, env=lean_environment(), capture_output=True, text=True, timeout=BUILD_TIMEOUT_SECONDS)
    assert isinstance(result.returncode, int), f"the command {arguments} gave no exit code. Fix: check that it started."
    return result


def contract_decision(reach, effect, guard):
    assert reach in REACH and effect in EFFECT and guard in GUARD, f"unknown value in ({reach}, {effect}, {guard}). Fix: use the contract's names."
    if reach == "Masked":
        result = "FixLoading"
    elif reach == "Unknown" or effect == "Invalid":
        result = "CannotDecide"
    elif effect == "NotEnoughRuns":
        result = "NeedsMoreRuns"
    elif effect in ("RuleRaisesViolations", "NoMeasurableEffect"):
        result = "DeleteCandidate"
    else:
        result = "ReplaceWithGuard" if guard == "GuardMatchesRule" else "Keep"
    assert result != "ReplaceWithGuard" or (reach == "Loaded" and effect == "RuleLowersViolations" and guard == "GuardMatchesRule"), f"D10 broken for ({reach}, {effect}, {guard}): {result}"
    return result


def contract_effect(noise, verdict):
    assert noise in NOISE and verdict in VERDICT, f"unknown value in ({noise}, {verdict}). Fix: use the contract's names."
    if noise != "NoiseOk":
        result = "Invalid"
    else:
        result = {"InconclusiveSmallN": "NotEnoughRuns", "FirstHigher": "RuleLowersViolations",
                  "FirstLower": "RuleRaisesViolations", "Inconclusive": "NoMeasurableEffect"}[verdict]
    assert (result == "Invalid") == (noise != "NoiseOk"), f"V6 broken for ({noise}, {verdict}): {result}"
    return result


def contract_probe(runs, target_hits, control_hits):
    assert runs >= 0 and 0 <= target_hits <= runs and 0 <= control_hits <= runs, f"probe inputs ({runs}, {target_hits}, {control_hits}) break 0 <= hits <= runs. Fix: pass valid inputs."
    if runs < MIN_PROBE_RUNS or control_hits > 0:
        result = "Unknown"
    elif target_hits == runs:
        result = "Loaded"
    elif target_hits == 0:
        result = "Masked"
    else:
        result = "Unknown"
    assert result != "Loaded" or (runs >= MIN_PROBE_RUNS and control_hits == 0), f"P3 broken for ({runs}, {target_hits}, {control_hits}): {result}"
    return result


def contract_guard(completed, coverage, zero_bypass):
    assert completed in COMPLETED and coverage in COVERAGE, f"unknown value in ({completed}, {coverage}). Fix: use the contract's names."
    assert isinstance(zero_bypass, bool), f"zero_bypass must be a flag, got {zero_bypass!r}. Fix: pass True or False."
    untested = completed in ("NoGuardArm", "InconclusiveSmallN") or coverage == "NoneSeen"
    if untested:
        result = "GuardUntested"
    elif completed != "FirstLower" and coverage == "Full" and zero_bypass:
        result = "GuardMatchesRule"
    else:
        result = "GuardWorse"
    assert result != "GuardMatchesRule" or coverage == "Full", f"G1 broken for ({completed}, {coverage}, {zero_bypass}): {result}"
    return result


def contract_reported(has_noise_pair, noise, loo_probe, rule_reach):
    assert isinstance(has_noise_pair, bool), f"has_noise_pair must be a flag, got {has_noise_pair!r}. Fix: pass True or False."
    assert noise in NOISE and loo_probe in REACH and rule_reach in REACH, f"unknown value in ({noise}, {loo_probe}, {rule_reach}). Fix: use the contract's names."
    result = has_noise_pair and noise == "NoiseOk" and loo_probe == "Loaded" and rule_reach != "Unknown"
    assert not result or has_noise_pair, f"L8 broken: reported without a noise pair for ({noise}, {loo_probe}, {rule_reach})"
    return result


def contract_arms(prompt_vs_component, nothing_vs_component, nothing_clean):
    assert prompt_vs_component in VERDICT and nothing_vs_component in VERDICT, f"unknown value in ({prompt_vs_component}, {nothing_vs_component}). Fix: use the contract's names."
    assert isinstance(nothing_clean, bool), f"nothing_clean must be a flag, got {nothing_clean!r}. Fix: pass True or False."
    if "InconclusiveSmallN" in (prompt_vs_component, nothing_vs_component):
        result = "Inconclusive"
    elif nothing_clean:
        result = "InsuranceKeep"
    elif prompt_vs_component == "FirstHigher":
        result = "KeepComponent"
    elif prompt_vs_component == "Inconclusive" and nothing_vs_component == "FirstHigher":
        result = "ReplaceWithPrompt"
    elif prompt_vs_component == "Inconclusive" and nothing_vs_component == "Inconclusive":
        result = "DeleteCandidate"
    else:
        result = "Inconclusive"
    assert result != "InsuranceKeep" or nothing_clean, f"TA3 broken for ({prompt_vs_component}, {nothing_vs_component}): {result}"
    return result


ROW_BUILDERS = {
    "decision": lambda: {(r, e, g): contract_decision(r, e, g) for r in REACH for e in EFFECT for g in GUARD},
    "effect": lambda: {(n, v): contract_effect(n, v) for n in NOISE for v in VERDICT},
    "probe": lambda: {(runs, t, c): contract_probe(runs, t, c) for runs in range(MAX_PROBE_RUNS + 1)
                      for t in range(runs + 1) for c in range(runs + 1)},
    "guard": lambda: {(cv, coverage, zero): contract_guard(cv, coverage, zero)
                      for cv in COMPLETED for coverage in COVERAGE for zero in BOOLEANS},
    "arms": lambda: {(p, n, clean): contract_arms(p, n, clean) for p in VERDICT for n in VERDICT for clean in BOOLEANS},
    "reported": lambda: {(pair, noise, loo, rule): contract_reported(pair, noise, loo, rule)
                         for pair in BOOLEANS for noise in NOISE for loo in REACH for rule in REACH},
}


def expected_rows(kind):
    assert kind in ROW_BUILDERS, f"unknown table kind {kind!r}. Rule: the kinds are {TABLE_KINDS}. Fix: use one of them."
    rows = ROW_BUILDERS[kind]()
    assert len(rows) == EXPECTED_ROWS[kind], f"the contract reading of {kind} has {len(rows)} rows, expected {EXPECTED_ROWS[kind]}. Fix: correct EXPECTED_ROWS or the inputs."
    return rows


def row_key_and_value(kind, row):
    assert kind in TABLE_KINDS, f"unknown table kind {kind!r}. Rule: the kinds are {TABLE_KINDS}. Fix: use one of them."
    assert isinstance(row, dict), f"a {kind} row must be an object, got {row!r}. Fix: check the exporter output."
    if kind == "decision":
        return (row["reach"], row["effect"], row["guard"]), row["decision"]
    if kind == "effect":
        return (row["noise"], row["verdict"]), row["effect"]
    if kind == "probe":
        return (row["runs"], row["targetHits"], row["controlHits"]), row["result"]
    if kind == "guard":
        return (row["completed"], row["coverage"], row["bypassRateZero"]), row["guard"]
    if kind == "arms":
        return (row["promptVsComponent"], row["nothingVsComponent"], row["nothingClean"]), row["verdict"]
    return (row["hasNoisePair"], row["noise"], row["looProbe"], row["ruleReach"]), row["canReport"]


def proven_source_files():
    assert (PROJECT / PROVEN_SOURCE_DIR).is_dir(), f"the folder {PROJECT / PROVEN_SOURCE_DIR} is missing. Rule: the proofs live there. Fix: restore it."
    sources = [PROJECT / name for name in PROVEN_SOURCES] + sorted((PROJECT / PROVEN_SOURCE_DIR).glob("*.lean"))
    assert len(sources) > len(PROVEN_SOURCES), f"no Lean files under {PROVEN_SOURCE_DIR}. Fix: restore the proofs."
    return sources


def theorem_names():
    names = []
    for source in sorted((PROJECT / PROVEN_SOURCE_DIR).glob("*.lean")):
        names += THEOREM_LINE.findall(source.read_text())
    assert names, f"no theorem found under {PROJECT / PROVEN_SOURCE_DIR}. Rule: the audit covers every theorem. Fix: check the source folder."
    assert len(names) == len(set(names)), f"theorem names repeat: {sorted(name for name in set(names) if names.count(name) > 1)}. Fix: rename one of each pair."
    return names


def write_audit_file(names):
    assert names, "write_audit_file got no theorem names. Rule: an empty audit proves nothing. Fix: pass theorem_names()."
    assert all(re.fullmatch(r"[\w.']+", name) for name in names), f"a theorem name is not a plain identifier: {names}. Fix: check the theorem lines."
    lines = ["import Willitharness", "", "open Willitharness", ""] + ["#print axioms " + name for name in names]
    AUDIT_SOURCE.write_text("\n".join(lines) + "\n")
    assert AUDIT_SOURCE.is_file(), f"the audit file {AUDIT_SOURCE} was not written. Fix: check the folder permissions."


def toolchain_directory_name():
    text = TOOLCHAIN_FILE.read_text().strip()
    assert "/" in text and ":" in text, f"{TOOLCHAIN_FILE} holds {text!r}. Rule: it names a toolchain as origin/name:version. Fix: restore the file."
    directory = text.replace("/", "--").replace(":", "---")
    assert "/" not in directory and ":" not in directory, f"the directory name {directory!r} still holds a separator. Fix: replace every / and :."
    return directory


def installed_digests(names):
    assert names, "installed_digests got no binary names. Fix: pass the pinned names."
    binaries = TOOLS / "toolchains" / toolchain_directory_name() / "bin"
    assert binaries.is_dir(), f"the toolchain folder {binaries} is missing. Rule: the checker runs the toolchain named in lean-toolchain. Fix: install it with elan."
    return {name: hashlib.sha256((binaries / name).read_bytes()).hexdigest() for name in names}


def pin_mismatches(actual, pinned):
    assert pinned, "pin_mismatches got no pins. Rule: a pin check with no pins proves nothing. Fix: pass the pinned digests."
    lengths = {len(digest) for digest in pinned.values()}
    assert len(lengths) == 1, f"pinned digests differ in length: {pinned!r}. Fix: use sha256 hex digests."
    return [f"{name} has sha256 {actual.get(name)}, pinned {digest}" for name, digest in pinned.items() if actual.get(name) != digest]


def check_toolchain_pin():
    key = (platform.system(), platform.machine())
    name = "toolchain binaries match the pinned sha256"
    if key not in PINNED_BINARY_SHA256:
        return name, "a pin for this platform", f"no pin for {key}. Fix: add its lean and lake digests to PINNED_BINARY_SHA256", False
    pinned = PINNED_BINARY_SHA256[key]
    assert pinned, f"the pins for {key} are empty. Rule: a pinned platform names its binaries. Fix: add the lean and lake digests."
    mismatches = pin_mismatches(installed_digests(sorted(pinned)), pinned)
    row = name, "lean and lake match", "match" if not mismatches else "; ".join(mismatches), not mismatches
    assert len(row) == 4, f"a check returns four fields, got {row!r}. Fix: return name, expected, actual, passed."
    return row


def check_toolchain():
    assert (PROJECT / "lakefile.toml").is_file(), f"no lakefile.toml in {PROJECT}. Rule: the checks run lake there. Fix: run the checker from a complete Lean project."
    result = run(["lean", "--version"])
    assert isinstance(result.stdout, str), f"lean printed {type(result.stdout)} instead of text. Rule: the checker reads text. Fix: check that lean starts."
    return "lean runs", "exit 0", result.stdout.strip() or result.stderr.strip(), result.returncode == 0


def check_build():
    assert (PROJECT / "lakefile.toml").is_file(), f"no lakefile.toml in {PROJECT}. Rule: the checks run lake there. Fix: run the checker from a complete Lean project."
    result = run(["lake", "build"])
    warnings = len(re.findall(r"^warning:", result.stdout + result.stderr, re.M))
    outcome = "exit %d, %d warnings" % (result.returncode, warnings)
    assert warnings >= 0, f"the warning count {warnings} cannot be negative. Fix: check the pattern."
    return "lake build (proven libraries)", "exit 0, 0 warnings", outcome, result.returncode == 0 and warnings == 0


def check_forbidden_constructs():
    assert (PROJECT / "lakefile.toml").is_file(), f"no lakefile.toml in {PROJECT}. Rule: the checks run lake there. Fix: run the checker from a complete Lean project."
    findings = []
    for source in proven_source_files():
        text = source.read_text()
        for label, pattern in FORBIDDEN_SOURCE_PATTERNS.items():
            if pattern.search(text):
                findings.append("%s in %s" % (label, source.name))
    assert all(isinstance(finding, str) for finding in findings), f"findings must be text, got {findings!r}. Fix: build them with a format string."
    return "no sorry, axiom declaration or native_decide", "none", ", ".join(findings) or "none", not findings


def check_axioms():
    assert (PROJECT / "lakefile.toml").is_file(), f"no lakefile.toml in {PROJECT}. Rule: the checks run lake there. Fix: run the checker from a complete Lean project."
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
    assert reported <= len(names), f"{reported} axiom lines for {len(names)} theorems. Rule: one line per theorem. Fix: check the audit output."
    return "#print axioms covers every theorem, standard axioms only", "all reported, none disallowed", outcome, result.returncode == 0 and reported == len(names) and not disallowed


def check_table(kind):
    assert kind in TABLE_KINDS, f"unknown table kind {kind!r}. Rule: the kinds are {TABLE_KINDS}. Fix: use one of them."
    assert (PROJECT / "Export.lean").is_file(), f"no Export.lean in {PROJECT}. Rule: the exporter writes the tables. Fix: restore it."
    result = run(["lake", "exe", "export_table", kind])
    label = "%s_table.json matches an independent reading of contract %s" % (kind, CONTRACT_VERSION)
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
    assert starts, f"no wrong theorem found in {WRONG_SOURCE}. Rule: the gate needs wrong variants that must fail. Fix: restore them."
    bounds = [start for start, _ in starts] + [len(lines) + 1]
    ranges = [(name, bounds[position], bounds[position + 1] - 1) for position, (_, name) in enumerate(starts)]
    assert all(first <= last for _, first, last in ranges), f"a theorem range runs backwards: {ranges}. Fix: check the source order."
    return ranges


def check_wrong_variants():
    assert (PROJECT / "lakefile.toml").is_file(), f"no lakefile.toml in {PROJECT}. Rule: the checks run lake there. Fix: run the checker from a complete Lean project."
    result = run(["lake", "build", "WrongVariants"])
    error_lines = [int(match.group(1)) for match in ERROR_LINE.finditer(result.stdout + result.stderr)]
    ranges = wrong_theorem_ranges()
    unfailed = [name for name, first, last in ranges if not any(first <= line <= last for line in error_lines)]
    outcome = "exit %d, %d wrong theorems, not failing: %s" % (result.returncode, len(ranges), unfailed or "none")
    assert len(unfailed) <= len(ranges), f"{len(unfailed)} unfailed of {len(ranges)} wrong theorems. Fix: check the range logic."
    return "every deliberately wrong theorem fails", "build fails, each wrong theorem has an error", outcome, result.returncode != 0 and bool(ranges) and not unfailed


def main():
    checks = [check_toolchain_pin, check_toolchain, check_build, check_forbidden_constructs, check_axioms,
              *[lambda kind=kind: check_table(kind) for kind in TABLE_KINDS], check_wrong_variants]
    rows = [check() for check in checks]
    assert all(len(row) == 4 for row in rows), f"every check returns four fields, got {rows!r}. Fix: return name, expected, actual, passed."
    assert len(rows) == len(checks), f"{len(rows)} rows for {len(checks)} checks. Fix: do not skip a check."
    print("%-66s %-40s %s" % ("check", "expected", "actual"))
    for name, expected, actual, passed in rows:
        print("%-66s %-40s %s [%s]" % (name, expected, actual, "OK" if passed else "MISMATCH"))
    return 0 if all(passed for *_, passed in rows) else 1


if __name__ == "__main__":
    sys.exit(main())
