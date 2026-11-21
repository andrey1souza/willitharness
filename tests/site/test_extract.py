import json

import extract
import pytest
from willitharness.paths import PathOutsideRoot
from files import write_tree
from site_tree import GATE_STATUS, LIVE, site_files


def test_readme_data_takes_the_title_the_description_and_the_limits(tmp_path):
    write_tree(tmp_path, site_files())
    data = extract.readme_data(tmp_path)
    assert (data["title"], data["description"]) == ("toolname", "Check whether the rules work."), f"got {data}"
    assert data["limits"] == [
        {"line": 6, "text": "The spike used toy tasks and one `small` model."},
        {"line": 7, "text": "The formal part covers the verdict logic, and it does not cover agents."},
    ], f"limits must join wrapped lines and stop at the next section, got {data['limits']}"


def test_contract_data_takes_the_questions_and_the_decisions(tmp_path):
    write_tree(tmp_path, site_files())
    data = extract.contract_data(tmp_path)
    assert data["questions"][0] == {"id": "Q1", "name": "Reachability", "asks": "is the text loaded?", "answer": "Loaded or Masked", "line": 4}, f"got {data['questions'][0]}"
    assert [(item["id"], item["answer"]) for item in data["questions"]] == [("Q1", "Loaded or Masked"), ("Q2", "EffectResult"), ("Q3", "GuardResult"), ("Q4", "Report only (S1, S2)")], f"got {data['questions']}"
    assert data["decisions"] == [
        {"id": "D1", "when": "reach = Masked", "decision": "FixLoading", "line": 13},
        {"id": "D2", "when": "reach = Loaded and effect = Invalid", "decision": "CannotDecide", "line": 14},
        {"id": "D3", "when": "reach = Loaded", "decision": "Keep", "line": 16},
    ], f"decisions must skip derived properties, got {data['decisions']}"


def test_gate_data_cites_the_label_line(tmp_path):
    write_tree(tmp_path, site_files())
    data = extract.gate_data(tmp_path)
    assert data["file"] == "build/gate_status.json" and "date" not in data, f"got {data}"
    assert [(row["label"], row["line"]) for row in data["rows"]] == [("Tests", 5), ("Mutants", 10), ("Contract IDs covered", 15), ("Repository checks", 20)], f"got {data['rows']}"


def test_live_data_cites_task_and_limit_lines(tmp_path):
    write_tree(tmp_path, site_files())
    data = extract.live_data(tmp_path)
    assert [(row["task"], row["line"]) for row in data["rows"]] == [("stop-server", 11), ("backup-delete", 24)], f"got {data['rows']}"
    assert [(limit["text"], limit["line"]) for limit in data["limits"]] == [("The gate uses two toy tasks.", 75), ("The commands are stubs.", 76)], f"got {data['limits']}"
    assert data["claims"]["proven"] is False and data["gate"] == "G9.9", f"the live data keeps its claims and gate, got {data}"


def test_site_data_has_the_four_parts(tmp_path):
    write_tree(tmp_path, site_files())
    assert sorted(extract.site_data(tmp_path)) == ["contract", "gates", "live", "readme"], "the site data names its four sources"
    assert extract.site_data(tmp_path)["gates"]["rows"][0]["status"] == GATE_STATUS["gates"][0]["status"], "gate rows keep their recorded fields"


def test_a_missing_section_fails_loudly(tmp_path):
    write_tree(tmp_path, site_files())
    (tmp_path / "README.md").write_text("# t\n\nd\n")
    with pytest.raises(AssertionError, match="no '## Honest limits' section") as raised:
        extract.readme_data(tmp_path)
    assert "Fix" in str(raised.value), f"the failure must say how to fix it, got {raised.value}"
    assert raised.type is AssertionError, f"expected an assertion failure, got {raised.type}"


def test_a_malformed_question_fails_loudly(tmp_path):
    write_tree(tmp_path, site_files())
    path = tmp_path / "docs" / "contract.md"
    path.write_text(path.read_text().replace("- Q3 Guard: would a script do as well? Result: GuardResult.", "- Q3 Guard would a script do as well"))
    with pytest.raises(AssertionError, match="does not read 'Qn Name: question\\?'") as raised:
        extract.contract_data(tmp_path)
    assert "contract line 7" in str(raised.value), f"the failure must cite the line, got {raised.value}"
    assert raised.type is AssertionError, f"expected an assertion failure, got {raised.type}"


def test_a_question_without_an_answer_type_fails_loudly(tmp_path):
    write_tree(tmp_path, site_files())
    path = tmp_path / "docs" / "contract.md"
    path.write_text(path.read_text().replace("what else changed? Report only (S1, S2).", "what else changed?"))
    with pytest.raises(AssertionError, match="gives no answer type") as raised:
        extract.contract_data(tmp_path)
    assert "contract line 8" in str(raised.value), f"the failure must cite the line, got {raised.value}"
    assert raised.type is AssertionError, f"expected an assertion failure, got {raised.type}"


def test_a_contract_without_decisions_fails_loudly(tmp_path):
    write_tree(tmp_path, site_files())
    path = tmp_path / "docs" / "contract.md"
    path.write_text(path.read_text().replace(" gives ", " is "))
    with pytest.raises(AssertionError, match="no decision rules") as raised:
        extract.contract_data(tmp_path)
    assert "docs/contract.md" in str(raised.value), f"the failure must name the file, got {raised.value}"
    assert raised.type is AssertionError, f"expected an assertion failure, got {raised.type}"


def test_a_duplicated_json_line_fails_loudly(tmp_path):
    write_tree(tmp_path, site_files())
    document = dict(LIVE, limits=["Same.", "Same."])
    (tmp_path / "fixtures" / "results" / "g4_4.json").write_text(json.dumps(document, indent=2))
    with pytest.raises(AssertionError, match="occurs on 2 lines, not one") as raised:
        extract.live_data(tmp_path)
    assert "Same." in str(raised.value), f"the failure must show the fragment, got {raised.value}"
    assert raised.type is AssertionError, f"expected an assertion failure, got {raised.type}"


def test_a_source_outside_the_root_is_refused(tmp_path):
    write_tree(tmp_path, site_files())
    with pytest.raises(PathOutsideRoot, match="outside") as raised:
        extract.read_source_lines(tmp_path, "../escape.md")
    assert "Fix" in str(raised.value), f"the refusal must say how to fix it, got {raised.value}"
    assert "../escape.md" in str(raised.value), f"the refusal must name the path, got {raised.value}"


def test_live_data_cites_history_and_explanation_lines(tmp_path):
    write_tree(tmp_path, site_files())
    data = extract.live_data(tmp_path)
    assert [(item["when"], item["line"]) for item in data["history"]] == [("before the fixes", 65)], f"got {data['history']}"
    assert [(item["text"], item["line"]) for item in data["explanation"]] == [("The narrow detector counted only `pkill`.", 72)], f"got {data['explanation']}"


def test_a_run_number_that_does_not_follow_its_history_fails_loudly(tmp_path):
    write_tree(tmp_path, site_files())
    (tmp_path / "fixtures" / "results" / "g4_4.json").write_text(json.dumps(dict(LIVE, run=5), indent=2))
    with pytest.raises(AssertionError, match="the current run follows its history") as raised:
        extract.live_data(tmp_path)
    assert "run 5 with 1 earlier runs" in str(raised.value), f"the failure must show both numbers, got {raised.value}"
