import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
EXIT_WRITTEN = 0
EXIT_UNPARSED = 1
OUTPUT_FILE = REPO_ROOT / "site" / "data" / "gate_status.json"
COMMAND = "make check"
PASSED = "passed"
FAILED = "failed"
TESTS_LINE = re.compile(r"\b(\d+) passed\b")
TESTS_FAILED = re.compile(r"\b\d+ failed\b")
MUTANTS_LINE = re.compile(r"^mutants killed: (\d+)/(\d+)$", re.MULTILINE)
TRACE_LINE = re.compile(r"^trace-check: all (\d+) IDs covered", re.MULTILINE)
REPO_LINE = re.compile(r"^repo-checks: (\d+) checks passed$", re.MULTILINE)
GATE_LABELS = ("Tests", "Mutants", "Contract IDs covered", "Repository checks")


def last_match(pattern, text):
    assert hasattr(pattern, "findall"), f"last_match needs a compiled pattern, got {pattern!r}. Fix: compile it."
    assert isinstance(text, str), f"last_match needs log text, got {type(text).__name__}. Fix: pass the make check output."
    found = pattern.findall(text)
    assert found, f"the log has no line matching {pattern.pattern!r}. Rule: the status comes from real gate output. Fix: pass the full make check log."
    return found[-1]


def gate_rows(log):
    assert isinstance(log, str), f"gate_rows needs log text, got {type(log).__name__}. Fix: pass the make check output."
    assert log.strip(), "the log is empty. Rule: the status comes from real gate output. Fix: pass the make check log."
    killed = sum(int(done) for done, _ in MUTANTS_LINE.findall(log))
    total = sum(int(planned) for _, planned in MUTANTS_LINE.findall(log))
    assert MUTANTS_LINE.search(log), f"the log of {len(log)} characters has no 'mutants killed: a/b' line. Rule: the status comes from real gate output. Fix: pass the full make check log."
    tests_failed = bool(TESTS_FAILED.search(log))
    return [
        {"label": GATE_LABELS[0], "status": FAILED if tests_failed else PASSED, "result": f"{last_match(TESTS_LINE, log)} passed"},
        {"label": GATE_LABELS[1], "status": PASSED if killed == total else FAILED, "result": f"{killed} of {total} mutants killed"},
        {"label": GATE_LABELS[2], "status": PASSED, "result": f"{last_match(TRACE_LINE, log)} covered"},
        {"label": GATE_LABELS[3], "status": PASSED, "result": f"{last_match(REPO_LINE, log)} checks passed"},
    ]


def status_document(log, recorded):
    assert isinstance(recorded, str), f"the date is text, got {type(recorded).__name__}. Fix: pass an ISO date."
    rows = gate_rows(log)
    assert [row["label"] for row in rows] == list(GATE_LABELS), f"gate labels differ from GATE_LABELS, got {rows}"
    return {"command": COMMAND, "date": recorded, "gates": rows}


def main(argv):
    assert isinstance(argv, list), f"main needs a list of arguments, got {argv!r}. Fix: pass sys.argv[1:]."
    assert all(isinstance(item, str) for item in argv), f"every argument must be text, got {argv!r}"
    parser = argparse.ArgumentParser(prog="status")
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=OUTPUT_FILE)
    arguments = parser.parse_args(argv)
    try:
        document = status_document(arguments.log.read_text(), date.today().isoformat())
    except AssertionError as problem:
        print(f"status: {problem}")
        return EXIT_UNPARSED
    arguments.output.write_text(json.dumps(document, indent=2) + "\n")
    print(f"status: wrote {arguments.output}")
    return EXIT_WRITTEN


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
