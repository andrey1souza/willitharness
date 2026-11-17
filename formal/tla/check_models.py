#!/usr/bin/env python3
"""Run TLC on every willitharness model and check what each one must say.

Scenarios must pass. Probes must be violated, which proves their state is reachable.
Mutants must be violated on exactly the invariant they break, which proves the
invariant can fail. Exit code 1 on any mismatch.
"""
import argparse
import re
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
GENERATED = HERE / "generated"
SPEC_MODULE = "WillItHarness"
PROBES_MODULE = "Probes"
DEFAULT_JAR = Path.home() / ".cache/tlalings/tla2tools.jar"
DEFAULT_JAVA = "/opt/homebrew/opt/openjdk/bin/java"
TLC_HEAP = "-Xmx1g"
TLC_WORKERS = "2"
TLC_TIMEOUT_SECONDS = 240
TAIL_LINES = 8
TEMPORAL = "TEMPORAL"
PASS = "pass"
VIOLATION = "violation"

SCENARIOS = ("nominal", "budget_tight", "unusable", "unknown_reach", "abort", "world_change", "two_tasks")

PROBES = (
    ("NeverBudgetStopped", "budget_tight"),
    ("NeverReported", "nominal"),
    ("NeverUnusableRun", "unusable"),
    ("NeverTimeout", "unusable"),
    ("NeverExtraAttempt", "unusable"),
    ("NeverAttemptCapReached", "unusable"),
    ("NeverNoiseOk", "nominal"),
    ("NeverNoiseTooHigh", "nominal"),
    ("NeverNoiseUnmeasured", "budget_tight"),
    ("NeverNoPairReported", "nominal"),
    ("NeverEffectReported", "nominal"),
    ("NeverWithheldForUnknown", "unknown_reach"),
    ("NeverAborted", "abort"),
    ("NeverAbortAfterVerdict", "abort"),
    ("NeverReachMasked", "nominal"),
    ("NeverWorldChanged", "world_change"),
    ("NeverStartBlockedByWorld", "world_change"),
)

MUTANTS = (
    ("L1", "nominal", "property",
     '    /\\ planState \\in {"WorldValidated", "ReachabilityChecked", "Running"}', "L1"),
    ("L1w", "world_change", "property", "    /\\ TRUE", "L1"),
    ("L2", "budget_tight", "invariant", "BudgetAllows == TRUE", "L2"),
    ("L3", "unusable", "property",
     '    /\\ unusable\' = [unusable EXCEPT ![c] = IF o = "unusable" THEN @ + 1 ELSE IF @ > 0 THEN @ - 1 ELSE @]', "L3"),
    ("L4", "nominal", "invariant", "               /\\ usable[c] < Reps", "L4"),
    ("L5", "nominal", "invariant", '    /\\ planState \\in {"Running", "Analyzed"}', "L5"),
    ("L6", "unusable", "invariant",
     "    /\\ reportedN' = [a \\in Arms |-> UsableCount(a) + UnusableCount(a)]", "L6"),
    ("L7", "unknown_reach", "invariant", '    IF FALSE THEN "Withheld"', "L7"),
    ("L8", "nominal", "invariant", '    ELSE IF TRUE THEN "Reported"', "L8"),
    ("L9", "unusable", "invariant", "               /\\ TRUE", "L9"),
)


@dataclass(frozen=True)
class Run:
    name: str
    module: str
    module_text: str
    cfg_text: str
    expected: str
    expected_property: str = ""


@dataclass(frozen=True)
class Result:
    verdict: str
    property_name: str
    generated: int
    distinct: int
    seconds: float
    tail: str


def read_text(name):
    return (HERE / name).read_text()


def constants_block(cfg_text):
    kept = []
    for line in cfg_text.splitlines():
        if line.startswith(("INVARIANT", "PROPERT")):
            break
        kept.append(line)
    return "\n".join(kept) + "\n"


def cfg_checking(scenario, kind, name):
    keyword = "INVARIANT" if kind == "invariant" else "PROPERTY"
    return constants_block(read_text(f"{scenario}.cfg")) + f"{keyword}\n    {name}\n"


def mutate(source, mutant_id, new_line):
    marker = f"(* MUT:{mutant_id} *)"
    lines = source.splitlines(keepends=True)
    hits = [index for index, line in enumerate(lines) if marker in line]
    assert len(hits) == 1, f"marker {marker} appears on {len(hits)} lines"
    lines[hits[0]] = new_line + "\n"
    mutated = "".join(lines)
    header = f"---- MODULE {SPEC_MODULE} ----"
    assert mutated.count(header) == 1, "module header not found exactly once"
    mutated = mutated.replace(header, f"---- MODULE Mutant_{mutant_id} ----")
    assert mutated != source, f"mutant {mutant_id} changed nothing"
    return mutated


def build_runs():
    spec_text = read_text(f"{SPEC_MODULE}.tla")
    runs = [Run(f"scenario {name}", SPEC_MODULE, spec_text, read_text(f"{name}.cfg"), PASS) for name in SCENARIOS]
    runs.append(Run("scenario abort: T2 fails when abort is allowed", SPEC_MODULE, spec_text,
                    cfg_checking("abort", "property", "T2"), VIOLATION, TEMPORAL))
    probes_text = read_text(f"{PROBES_MODULE}.tla")
    for name, scenario in PROBES:
        runs.append(Run(f"probe {name} in {scenario}", PROBES_MODULE, probes_text,
                        cfg_checking(scenario, "invariant", name), VIOLATION, name))
    for mutant_id, scenario, kind, new_line, broken in MUTANTS:
        module = f"Mutant_{mutant_id}"
        runs.append(Run(f"mutant {mutant_id} in {scenario}", module, mutate(spec_text, mutant_id, new_line),
                        cfg_checking(scenario, kind, broken), VIOLATION, broken))
    return runs


def parse_output(output):
    counts = re.search(r"([\d,]+) states generated, ([\d,]+) distinct states found", output)
    generated, distinct = (int(group.replace(",", "")) for group in counts.groups()) if counts else (0, 0)
    if "No error has been found" in output:
        return PASS, "", generated, distinct
    named = re.search(r"(?:Invariant|Action property) (\w+) is violated", output)
    if named:
        return VIOLATION, named.group(1), generated, distinct
    if "Temporal properties were violated" in output:
        return VIOLATION, TEMPORAL, generated, distinct
    return "error", "", generated, distinct


def keep_generated(run):
    if run.expected == PASS and run.module == SPEC_MODULE:
        return
    GENERATED.mkdir(exist_ok=True)
    slug = re.sub(r"[^A-Za-z0-9]+", "_", run.name).strip("_")
    (GENERATED / f"{slug}.cfg").write_text(run.cfg_text)
    if run.module.startswith("Mutant_"):
        (GENERATED / f"{run.module}.tla").write_text(run.module_text)


def execute(run, jar, java):
    keep_generated(run)
    with tempfile.TemporaryDirectory(prefix="willitharness-tlc-") as directory:
        work = Path(directory)
        (work / f"{SPEC_MODULE}.tla").write_text(read_text(f"{SPEC_MODULE}.tla"))
        (work / f"{run.module}.tla").write_text(run.module_text)
        (work / "run.cfg").write_text(run.cfg_text)
        command = [java, "-XX:+UseParallelGC", TLC_HEAP, "-cp", str(jar), "tlc2.TLC", "-workers", TLC_WORKERS,
                   "-metadir", str(work / "states"), "-config", "run.cfg", f"{run.module}.tla"]
        started = time.monotonic()
        try:
            done = subprocess.run(command, cwd=work, capture_output=True, text=True, timeout=TLC_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            return Result("timeout", "", 0, 0, time.monotonic() - started, "")
        output = done.stdout + done.stderr
    verdict, property_name, generated, distinct = parse_output(output)
    tail = "\n".join(output.strip().splitlines()[-TAIL_LINES:])
    return Result(verdict, property_name, generated, distinct, time.monotonic() - started, tail)


def matches(run, result):
    if result.verdict != run.expected:
        return False
    return run.expected == PASS or result.property_name == run.expected_property


def describe_expected(run):
    return run.expected if run.expected == PASS else f"violation of {run.expected_property}"


def describe_result(result):
    return result.verdict if result.verdict != VIOLATION else f"violation of {result.property_name}"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jar", type=Path, default=DEFAULT_JAR)
    parser.add_argument("--java", default=DEFAULT_JAVA)
    parser.add_argument("--only", default="", help="run only runs whose name contains this text")
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args()
    runs = [run for run in build_runs() if args.only in run.name]
    if args.list:
        print("\n".join(run.name for run in runs))
        return 0
    assert args.jar.is_file(), f"the TLA tools jar {args.jar} does not exist"
    failures = 0
    print(f"{'run':52} {'expected':26} {'got':26} {'states':>8} {'distinct':>8} {'secs':>6}  ok")
    for run in runs:
        result = execute(run, args.jar, args.java)
        good = matches(run, result)
        failures += not good
        print(f"{run.name:52} {describe_expected(run):26} {describe_result(result):26} "
              f"{result.generated:8d} {result.distinct:8d} {result.seconds:6.1f}  {'yes' if good else 'NO'}")
        if not good and result.tail:
            print(result.tail)
    print(f"{len(runs) - failures} of {len(runs)} runs matched what they must say")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
