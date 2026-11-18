import json
import shutil
from pathlib import Path

import pytest

import trace_check

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACT_ID_COUNT = 43
REMOVED_ID = "S2"


def run_gate(capsys, arguments=()):
    code = trace_check.main(list(arguments))
    return code, capsys.readouterr().out


def copy_features_without(tmp_path, identifier):
    target = tmp_path / "features"
    shutil.copytree(REPO_ROOT / "features", target)
    for path in target.glob("*.feature"):
        path.write_text(path.read_text().replace("@" + identifier, "@removed"))
    return target


def test_a_range_expands_to_every_id_in_it():
    assert trace_check.expand_group("V1 to V3") == ["V1", "V2", "V3"], "a range must include both ends"


def test_a_list_mixes_singles_hyphenated_ids_and_ranges():
    expanded = trace_check.expand_group("S1, DI-1, W1 to W2, T2a")
    assert expanded == ["S1", "DI-1", "W1", "W2", "T2a"], f"unexpected expansion {expanded}"


def test_a_backwards_range_is_rejected():
    with pytest.raises(AssertionError) as raised:
        trace_check.expand_group("V3 to V1")
    assert "runs backwards" in str(raised.value), f"unexpected message {str(raised.value)!r}"


def test_a_word_that_is_not_an_id_is_rejected():
    with pytest.raises(AssertionError) as raised:
        trace_check.expand_group("V1, banana")
    assert "not a contract ID" in str(raised.value), f"unexpected message {str(raised.value)!r}"


def test_the_contract_table_expands_to_forty_three_ids():
    required = trace_check.required_places((REPO_ROOT / "docs" / "contract.md").read_text())
    assert len(required) == CONTRACT_ID_COUNT, f"expected {CONTRACT_ID_COUNT} IDs, got {sorted(required)}"
    assert required["L9"] == {"features", "tla"}, f"L9 must need features and TLA+, got {required['L9']}"


def test_a_test_named_for_d10_does_not_cover_d1():
    sources = {"tests": {"D10_replace_only_when_justified"}}
    assert not trace_check.is_present("D1", "tests", sources), f"D10 must not count as D1 in {sources}"
    assert trace_check.is_present("D10", "tests", sources), f"D10 must count as D10 in {sources}"


def test_the_repository_passes_the_gate(capsys):
    code, output = run_gate(capsys)
    assert code == trace_check.EXIT_COVERED, f"the repo must pass; output {output!r}"
    assert "all %d IDs covered" % CONTRACT_ID_COUNT in output, f"unexpected output {output!r}"


def test_an_id_removed_from_the_features_fails_the_gate(tmp_path, capsys):
    features = copy_features_without(tmp_path, REMOVED_ID)
    code, output = run_gate(capsys, ["--features", str(features)])
    assert code == trace_check.EXIT_GAPS, f"expected exit {trace_check.EXIT_GAPS}, got {code}; output {output!r}"
    assert "trace-check: missing %s in features" % REMOVED_ID in output, f"unexpected output {output!r}"


def test_a_pending_entry_that_is_now_covered_fails_the_gate(tmp_path, capsys):
    pending = tmp_path / "pending.json"
    entries = json.loads((REPO_ROOT / "scripts" / "gates" / "trace_pending.json").read_text())
    pending.write_text(json.dumps(entries + [{"id": "V1", "place": "tests"}]))
    code, output = run_gate(capsys, ["--pending", str(pending)])
    assert code == trace_check.EXIT_GAPS, f"expected exit {trace_check.EXIT_GAPS}, got {code}; output {output!r}"
    assert "pending entry V1 in tests is now covered" in output, f"unexpected output {output!r}"
