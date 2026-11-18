import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
EXIT_COVERED = 0
EXIT_GAPS = 1
SECTION_HEADING = "## 8. Traceability"
NEXT_HEADING = "## 9."
RANGE = re.compile(r"^([A-Z]+)(\d+) to ([A-Z]+)(\d+)$")
SINGLE = re.compile(r"^[A-Z]+-?\d+[a-z]?$")
FEATURE_TAG = re.compile(r"(?<!\S)@([A-Za-z0-9-]+)")
TEST_NAME = re.compile(r"def test_([A-Za-z0-9_]+)\(")
PLACE_KEYWORDS = {"features": "BDD", "tests": "tests", "lean": "Lean", "tla": "TLA+"}


def expand_group(text):
    assert text.strip(), "expand_group got an empty ID group. Rule: every row of the table names IDs. Fix: fill the first cell."
    identifiers = []
    for part in text.split(","):
        item = part.strip()
        matched = RANGE.match(item)
        if matched:
            prefix, start, other_prefix, end = matched.groups()
            assert prefix == other_prefix, f"range {item!r} mixes prefixes {prefix} and {other_prefix}. Fix: split it into two ranges."
            assert int(start) <= int(end), f"range {item!r} runs backwards. Fix: write the smaller number first."
            identifiers.extend(f"{prefix}{number}" for number in range(int(start), int(end) + 1))
        else:
            assert SINGLE.match(item), f"{item!r} is not a contract ID. Rule: IDs look like V1, DI-1 or T2a. Fix: correct the table cell."
            identifiers.append(item)
    assert len(set(identifiers)) == len(identifiers), f"group {text!r} repeats an ID: {identifiers}"
    return identifiers


def required_places(contract_text):
    assert SECTION_HEADING in contract_text, f"the contract has no {SECTION_HEADING!r}. Fix: restore the traceability section."
    section = contract_text.split(SECTION_HEADING, 1)[1].split(NEXT_HEADING, 1)[0]
    rows = [line for line in section.splitlines() if line.startswith("| ") and "---" not in line][1:]
    assert rows, "the traceability table has no rows. Fix: restore the table."
    required = {}
    for row in rows:
        group, where = [cell.strip() for cell in row.strip("|").split("|")[:2]]
        places = {place for place, keyword in PLACE_KEYWORDS.items() if keyword in where}
        assert places, f"row {group!r} names no known place in {where!r}. Fix: use BDD, tests, Lean or TLA+."
        for identifier in expand_group(group):
            assert identifier not in required, f"ID {identifier} appears in two rows of the table"
            required[identifier] = places
    return required


def feature_tags(directory):
    assert directory.is_dir(), f"{directory} is not a directory. Fix: pass the features directory."
    tags = set()
    for path in directory.glob("*.feature"):
        for line in path.read_text().splitlines():
            if line.strip().startswith("@"):
                tags.update(FEATURE_TAG.findall(line))
    assert tags, f"{directory} holds no feature tags. Fix: pass the features directory."
    return tags


def collected_test_names(directory):
    assert directory.is_dir(), f"{directory} is not a directory. Fix: pass the tests directory."
    names = set()
    for path in directory.rglob("*.py"):
        names.update(TEST_NAME.findall(path.read_text()))
    assert names, f"{directory} holds no tests. Fix: pass the tests directory."
    return names


def lean_text(directory):
    assert directory.is_dir(), f"{directory} is not a directory. Fix: pass the Lean directory."
    parts = [path.read_text() for path in directory.rglob("*.lean") if ".lake" not in path.parts]
    assert parts, f"{directory} holds no Lean files. Fix: pass the Lean directory."
    return "\n".join(parts)


def tla_text(directory):
    assert directory.is_dir(), f"{directory} is not a directory. Fix: pass the TLA+ directory."
    parts = [path.read_text() for path in directory.glob("*.tla")]
    assert parts, f"{directory} holds no TLA+ files. Fix: pass the TLA+ directory."
    return "\n".join(parts)


def is_present(identifier, place, sources):
    assert place in PLACE_KEYWORDS, f"unknown place {place!r}. Fix: use one of {sorted(PLACE_KEYWORDS)}."
    assert SINGLE.match(identifier), f"{identifier!r} is not a contract ID"
    if place == "features":
        return identifier in sources["features"]
    if place == "tests":
        prefix = identifier.replace("-", "_")
        return any(name == prefix or name.startswith(prefix + "_") for name in sources["tests"])
    if place == "lean":
        return re.search(rf"\b(?:theorem|lemma|def)\s+{identifier.replace('-', '')}_", sources["lean"]) is not None
    return re.search(rf"^{identifier}\s*==", sources["tla"], re.MULTILINE) is not None


def main(argv):
    assert isinstance(argv, list), f"main needs a list of arguments, got {argv!r}. Fix: pass sys.argv[1:]."
    assert all(isinstance(item, str) for item in argv), f"every argument must be text, got {argv!r}"
    parser = argparse.ArgumentParser(prog="trace_check")
    parser.add_argument("--contract", type=Path, default=REPO_ROOT / "docs" / "contract.md")
    parser.add_argument("--features", type=Path, default=REPO_ROOT / "features")
    parser.add_argument("--tests", type=Path, default=REPO_ROOT / "tests")
    parser.add_argument("--lean", type=Path, default=REPO_ROOT / "formal" / "lean")
    parser.add_argument("--tla", type=Path, default=REPO_ROOT / "formal" / "tla")
    parser.add_argument("--pending", type=Path, default=REPO_ROOT / "scripts" / "gates" / "trace_pending.json")
    arguments = parser.parse_args(argv)
    required = required_places(arguments.contract.read_text())
    sources = {
        "features": feature_tags(arguments.features),
        "tests": collected_test_names(arguments.tests),
        "lean": lean_text(arguments.lean),
        "tla": tla_text(arguments.tla),
    }
    pending = {(entry["id"], entry["place"]) for entry in json.loads(arguments.pending.read_text())}
    missing = {
        (identifier, place)
        for identifier, places in required.items()
        for place in places
        if not is_present(identifier, place, sources)
    }
    new_gaps = sorted(missing - pending)
    stale = sorted(pending - missing)
    for identifier, place in new_gaps:
        print(f"trace-check: missing {identifier} in {place}")
    for identifier, place in stale:
        print(f"trace-check: pending entry {identifier} in {place} is now covered; remove it from {arguments.pending.name}")
    if new_gaps or stale:
        return EXIT_GAPS
    waiting = ", ".join(f"{identifier} ({place})" for identifier, place in sorted(pending))
    suffix = f"; pending: {waiting}" if pending else ""
    print(f"trace-check: all {len(required)} IDs covered{suffix}")
    return EXIT_COVERED


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
