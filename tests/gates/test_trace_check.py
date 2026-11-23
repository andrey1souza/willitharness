import json
from pathlib import Path

import pytest

import trace_check

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACT_ID_COUNT = 57
REMOVED_ID = "S2"
MINI_CONTRACT = (
    "## 8. Traceability\n| ID group | Where it must appear |\n|---|---|\n"
    "| V1 | BDD features |\n| S2 | BDD features, tests |\n\n## 9. Out of scope\n"
)
FEATURE_WITH_BOTH = "Feature: mini\n  @V1 @S2\n  Scenario: both\n"
FEATURE_WITHOUT_S2 = "Feature: mini\n  @V1\n  Scenario: one\n"
TEST_FOR_S2 = "def test_S2_holds():\n    assert True\n"


def run_gate(capsys, arguments=()):
    code = trace_check.main(list(arguments))
    return code, capsys.readouterr().out


def build_world(root, feature_text):
    files = {
        "contract.md": MINI_CONTRACT,
        "features/a.feature": feature_text,
        "tests/test_a.py": TEST_FOR_S2,
        "lean/A.lean": "theorem V1_holds : True := trivial\n",
        "tla/A.tla": "L1 == TRUE\n",
        "pending.json": "[]",
    }
    for name, text in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    return [
        "--contract", str(root / "contract.md"), "--features", str(root / "features"), "--tests", str(root / "tests"),
        "--lean", str(root / "lean"), "--tla", str(root / "tla"), "--pending", str(root / "pending.json"),
    ]


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


def test_a_contract_table_maps_each_id_to_the_places_its_row_names():
    required = trace_check.required_places(MINI_CONTRACT)
    assert required == {"V1": {"features"}, "S2": {"features", "tests"}}, f"unexpected places {required}"


def test_a_test_named_for_d10_does_not_cover_d1():
    sources = {"tests": {"D10_replace_only_when_justified"}}
    assert not trace_check.is_present("D1", "tests", sources), f"D10 must not count as D1 in {sources}"
    assert trace_check.is_present("D10", "tests", sources), f"D10 must count as D10 in {sources}"


def test_the_repository_passes_the_gate(capsys):
    code, output = run_gate(capsys)
    assert code == trace_check.EXIT_COVERED, f"the repo must pass; output {output!r}"
    assert "all %d IDs covered" % CONTRACT_ID_COUNT in output, f"unexpected output {output!r}"


def test_a_complete_mini_world_passes(tmp_path, capsys):
    arguments = build_world(tmp_path, FEATURE_WITH_BOTH)
    code, output = run_gate(capsys, arguments)
    assert code == trace_check.EXIT_COVERED, f"a complete world must pass; output {output!r}"
    assert "all 2 IDs covered" in output, f"unexpected output {output!r}"


def test_an_id_removed_from_the_features_fails_the_gate(tmp_path, capsys):
    arguments = build_world(tmp_path, FEATURE_WITHOUT_S2)
    code, output = run_gate(capsys, arguments)
    assert code == trace_check.EXIT_GAPS, f"expected exit {trace_check.EXIT_GAPS}, got {code}; output {output!r}"
    assert "trace-check: missing %s in features" % REMOVED_ID in output, f"unexpected output {output!r}"


def test_a_pending_entry_that_is_now_covered_fails_the_gate(tmp_path, capsys):
    arguments = build_world(tmp_path, FEATURE_WITH_BOTH)
    (tmp_path / "pending.json").write_text(json.dumps([{"id": "V1", "place": "features"}]))
    code, output = run_gate(capsys, arguments)
    assert code == trace_check.EXIT_GAPS, f"expected exit {trace_check.EXIT_GAPS}, got {code}; output {output!r}"
    assert "pending entry V1 in features is now covered" in output, f"unexpected output {output!r}"


def test_a_pending_file_that_is_not_a_list_is_rejected():
    with pytest.raises(AssertionError) as raised:
        trace_check.parse_pending('{"id": "V1"}')
    assert "must hold a list" in str(raised.value), f"unexpected message {str(raised.value)!r}"


def test_a_test_name_inside_a_string_does_not_cover_an_id(tmp_path):
    (tmp_path / "test_a.py").write_text('TEXT = "def test_S2_fake():\\n    pass"\n\n\ndef test_V1_real():\n    assert True\n')
    names = trace_check.collected_test_names(tmp_path)
    assert names == {"V1_real"}, f"only the real function may count, got {names}"
