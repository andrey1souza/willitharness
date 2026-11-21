#!/usr/bin/env python3
"""Walk the TLA+ model with TLC and replay every walk against the lifecycle code.

TLC takes seeded random walks of TraceWalk.tla. Each walk lists the model state after
every action. The replay applies each action to the real lifecycle and compares the
plan state, the per-cell counters, the money, the budget and the reachability results.
It also tries the actions the model forbids and requires the code to refuse them.
Exit code 1 on the first divergence, which is printed with seed, walk, step and both states.
"""
import argparse
import importlib
import json
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import check_models
from willitharness.paths import inside

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
IMPORT_DIRECTORIES = ("tests/support", "scripts/gates")
sys.path[:0] = [str(inside(REPO_ROOT, directory)) for directory in IMPORT_DIRECTORIES]
trace_fixtures = importlib.import_module("trace_fixtures")
trace_replay = importlib.import_module("trace_replay")

WALK_MODULE = "TraceWalk"
SCENARIOS = ("resume_world", "unusable", "resume_abort")
REPLAY_WALKS = {"resume_world": 40, "unusable": 40, "resume_abort": 400}
FIXTURE_WALKS = {"resume_world": 8, "unusable": 8, "resume_abort": 400}
DEPTHS = {"resume_world": 18, "unusable": 18, "resume_abort": 18}
SEED = 20261119
WALK_PREFIX = "WALK "
TERMINATED = "Terminated"
TLC_TIMEOUT_SECONDS = 300
TLC_HEAP = "-Xmx1g"
CONSTANT_LINE = re.compile(r"^\s+(\w+) = (\d+)\s*$")
EXIT_OK = 0
EXIT_FAILED = 1


def tlc_unavailable(jar, java):
    assert isinstance(jar, Path), f"tlc_unavailable needs the jar as a Path, got {jar!r}. Fix: pass a Path."
    assert java, "tlc_unavailable needs a java path. Fix: pass --java or use the default."
    if not jar.is_file():
        return f"the TLA tools jar {jar} is absent. Fix: download tla2tools.jar from the pinned tlaplus release."
    if not Path(java).is_file():
        return f"java {java} is absent. Fix: install a JDK or pass --java."
    return check_models.jar_error(jar, check_models.TLA_JAR_SHA256)


def walk_cfg(scenario, depth):
    assert depth >= 2, f"depth {depth} is below 2. Rule: a walk holds the initial state and one step. Fix: pass a deeper walk."
    text = check_models.read_text(f"{scenario}.cfg")
    lines = check_models.constants_block(text).splitlines()
    constants = [line for line in lines if line.startswith("    ")]
    cfg = "INIT WalkInit\nNEXT WalkNext\nCONSTANTS\n" + "\n".join(constants) + f"\n    WalkDepth = {depth - 1}\nINVARIANT\n    Export\n"
    assert "WalkDepth" in cfg and "Export" in cfg, f"the walk cfg for {scenario} lost WalkDepth or Export: {cfg!r}"
    return cfg


def constants_of(scenario):
    assert scenario, "constants_of needs a scenario name. Fix: pass a formal/tla cfg name."
    found = {}
    for line in check_models.read_text(f"{scenario}.cfg").splitlines():
        match = CONSTANT_LINE.match(line)
        if match:
            found[match.group(1)] = int(match.group(2))
    assert {"Reps", "MaxRetries", "RunCap", "Budget"} <= set(found), f"{scenario}.cfg lacks a numeric constant the replay needs: {found}"
    return found


def parse_walks(output):
    assert isinstance(output, str), f"TLC output must be text, got {type(output).__name__}. Fix: decode it."
    walks = []
    for line in output.splitlines():
        if line.startswith(f'"{WALK_PREFIX}'):
            walk = [state for state in json.loads(json.loads(line)[len(WALK_PREFIX):]) if state["act"][0] != TERMINATED]
            if walk not in walks:
                walks.append(walk)
    assert all(walk for walk in walks), f"TLC printed an empty walk among {len(walks)} walks. Rule: a walk holds the initial state. Fix: check Export in TraceWalk.tla."
    return walks


def run_walks(scenario, jar, java, header):
    assert jar.is_file(), f"the TLA tools jar {jar} does not exist. Fix: pass --jar."
    assert header["walks"] >= 1 and header["depth"] >= 2, f"header {header} asks for no walk. Fix: use 1 walk or more and depth 2 or more."
    with tempfile.TemporaryDirectory(prefix="willitharness-walk-") as directory:
        work = Path(directory)
        for name in (*trace_fixtures.MODEL_FILES,):
            (work / name).write_text(check_models.read_text(name))
        (work / "walk.cfg").write_text(walk_cfg(scenario, header["depth"]))
        command = [java, "-XX:+UseParallelGC", TLC_HEAP, "-cp", str(jar), "tlc2.TLC", "-workers", "1", "-simulate", f"num={header['walks']}", "-depth", str(header["depth"]),
                   "-seed", str(header["seed"]), "-deadlock", "-metadir", str(work / "states"), "-config", "walk.cfg", f"{WALK_MODULE}.tla"]
        done = subprocess.run(command, cwd=work, capture_output=True, text=True, timeout=TLC_TIMEOUT_SECONDS)
    assert done.returncode == 0, f"TLC failed on the walk of {scenario}: {(done.stdout + done.stderr)[-600:]}. Fix: check TraceWalk.tla against {scenario}.cfg."
    walks = parse_walks(done.stdout)
    assert walks, f"TLC printed no walk for {scenario}. Rule: a replay needs walks. Fix: check that Export in TraceWalk.tla prints at WalkDepth."
    return walks


def header_for(scenario, walks, jar):
    assert walks >= 1, f"{walks} walks asked. Fix: ask for 1 or more."
    assert jar.is_file(), f"the TLA tools jar {jar} does not exist. Fix: pass --jar."
    header = {"scenario": scenario, "seed": SEED, "walks": walks, "depth": DEPTHS[scenario], "tlc_jar_sha256": check_models.TLA_JAR_SHA256,
              "model_sha256": trace_fixtures.model_digest(REPO_ROOT, scenario), "constants": constants_of(scenario)}
    assert set(header) == set(trace_fixtures.HEADER_KEYS), f"the header keys {set(header)} differ from {trace_fixtures.HEADER_KEYS}"
    return header


def record_fixtures(jar, java):
    assert jar.is_file(), f"the TLA tools jar {jar} does not exist. Fix: pass --jar."
    assert java, "record_fixtures needs a java path. Fix: pass --java."
    for scenario in SCENARIOS:
        header = header_for(scenario, FIXTURE_WALKS[scenario], jar)
        walks = run_walks(scenario, jar, java, header)
        path = inside(REPO_ROOT, f"{trace_fixtures.FIXTURE_DIRECTORY}/{scenario}.json")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"header": header, "walks": walks}, separators=(",", ":")) + "\n")
        print(f"recorded {path.relative_to(REPO_ROOT)}: {len(walks)} walks")
    return EXIT_OK


def replay_all(jar, java, seed):
    assert jar.is_file(), f"the TLA tools jar {jar} does not exist. Fix: pass --jar."
    assert java, "replay_all needs a java path. Fix: pass --java."
    started = time.monotonic()
    walk_count = step_count = probe_count = 0
    every_walk = []
    for scenario in SCENARIOS:
        header = {**header_for(scenario, REPLAY_WALKS[scenario], jar), "seed": seed}
        walks = run_walks(scenario, jar, java, header)
        every_walk += walks
        result = trace_replay.replay_walks(walks, header)
        walk_count += result.walks
        step_count += result.steps
        probe_count += result.probes
        print(f"{scenario}: {result.walks} walks, {result.steps} states compared, {result.probes} refusal probes")
        if result.divergence:
            print(trace_replay.describe(result.divergence))
            return EXIT_FAILED
    gaps = trace_replay.coverage_errors(every_walk)
    print(f"total: {walk_count} walks, {step_count} states compared, {probe_count} refusal probes, {time.monotonic() - started:.1f} s")
    for gap in gaps:
        print(f"coverage: {gap}")
    return EXIT_FAILED if gaps else EXIT_OK


def main(argv):
    assert isinstance(argv, list), f"main needs a list of arguments, got {argv!r}. Fix: pass sys.argv[1:]."
    assert all(isinstance(item, str) for item in argv), f"every argument must be text, got {argv!r}"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jar", type=Path, default=check_models.DEFAULT_JAR)
    parser.add_argument("--java", default=check_models.DEFAULT_JAVA)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--record", action="store_true", help="rewrite the fixtures under fixtures/traces")
    arguments = parser.parse_args(argv)
    unavailable = tlc_unavailable(arguments.jar, arguments.java)
    if unavailable:
        print(unavailable, file=sys.stderr)
        return EXIT_FAILED
    return record_fixtures(arguments.jar, arguments.java) if arguments.record else replay_all(arguments.jar, arguments.java, arguments.seed)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
