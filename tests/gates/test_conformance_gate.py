import json
from pathlib import Path

import pytest

from willitharness import conformance

GOLDEN = Path(__file__).resolve().parents[2] / "formal" / "lean"
CHANGED_VALUE = "ChangedByTheTest"
RESULT_KEY_BY_KIND = {"decision": "decision", "effect": "effect", "probe": "result", "guard": "guard"}
CASES_BY_KIND = {"decision": 45, "effect": 12, "probe": 140, "guard": 20}


def table_path(kind):
    return GOLDEN / conformance.FILE_BY_KIND[kind]


def changed_copy(kind, tmp_path):
    rows = json.loads(table_path(kind).read_text())
    rows[0][RESULT_KEY_BY_KIND[kind]] = CHANGED_VALUE
    target = tmp_path / conformance.FILE_BY_KIND[kind]
    target.write_text(json.dumps(rows))
    return target


@pytest.mark.parametrize("kind", sorted(CASES_BY_KIND))
def test_a_table_file_path_conforms_and_prints_the_case_count(kind, capsys):
    code = conformance.main([kind, str(table_path(kind))])
    output = capsys.readouterr().out
    expected = f"{kind} table conforms: {CASES_BY_KIND[kind]} cases"
    assert code == conformance.CONFORMS_EXIT_CODE, f"expected exit 0, got {code}; output {output!r}"
    assert expected in output, f"expected {expected!r}, got {output!r}"


@pytest.mark.parametrize("kind", sorted(CASES_BY_KIND))
def test_a_copy_with_one_result_changed_exits_one_and_names_the_case(kind, tmp_path, capsys):
    target = changed_copy(kind, tmp_path)
    code = conformance.main([kind, str(target)])
    errors = capsys.readouterr().err
    assert code == conformance.MISMATCH_EXIT_CODE, f"expected exit 1, got {code}; stderr {errors!r}"
    assert errors.startswith(kind), f"the message must start with the table kind {kind!r}, got {errors!r}"


def test_a_missing_table_file_is_reported_with_the_path(tmp_path):
    missing = tmp_path / "nothing.json"
    with pytest.raises(AssertionError) as raised:
        conformance.main(["probe", str(missing)])
    assert str(missing) in str(raised.value), f"the message must name {missing}, got {str(raised.value)!r}"


def test_a_copy_with_a_valid_but_wrong_classification_names_both_answers(tmp_path, capsys):
    rows = json.loads(table_path("probe").read_text())
    original = rows[0]["result"]
    wrong = "Loaded" if original != "Loaded" else "Masked"
    rows[0]["result"] = wrong
    target = tmp_path / "probe_table.json"
    target.write_text(json.dumps(rows))
    code = conformance.main(["probe", str(target)])
    errors = capsys.readouterr().err
    assert code == conformance.MISMATCH_EXIT_CODE, f"expected exit 1, got {code}; stderr {errors!r}"
    assert f"lean={wrong} python={original}" in errors, f"expected both answers named, got {errors!r}"
