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
        {"line": 35, "text": "The spike used toy tasks and one `small` model."},
        {"line": 36, "text": "The formal part covers the verdict logic, and it does not cover agents."},
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


def test_site_data_has_the_five_parts(tmp_path):
    write_tree(tmp_path, site_files())
    assert sorted(extract.site_data(tmp_path)) == ["contract", "gates", "live", "project", "readme"], "the site data names its five sources"
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


def test_readme_data_takes_the_summary_the_commands_the_quick_start_and_the_isolation_limits(tmp_path):
    write_tree(tmp_path, site_files())
    data = extract.readme_data(tmp_path)
    assert data["summary"] == {"line": 5, "text": "You write rules in `CLAUDE.md`. Do they load?"}, f"got {data['summary']}"
    assert data["commands"] == [
        {"line": 10, "command": "`toolname plan check <plan.json>`", "does": "Checks a plan.", "status": "works"},
        {"line": 11, "command": "`toolname decide`", "does": "Gives a decision.", "status": "not built (T43)"},
    ], f"got {data['commands']}"
    assert data["offline"]["lead"] == {"line": 14, "text": "The fake agent proves the plumbing. It measures nothing about a real agent."}, f"got {data['offline']['lead']}"
    assert data["offline"]["blocks"] == [
        {"line": 18, "label": "Install the tool.", "text": "uv sync\ntoolname plan check plan.json"},
        {"line": 27, "label": "Run the plan.", "text": "toolname run plan.json --runs 3"},
    ], f"only sh blocks count, output blocks are skipped; got {data['offline']['blocks']}"
    assert data["isolation"] == {"line": 31, "text": "Runs use a `sandbox`. The process is not confined."}, f"got {data['isolation']}"


def test_project_data_takes_the_repository_and_the_license_name(tmp_path):
    write_tree(tmp_path, site_files())
    assert extract.project_data(tmp_path) == {"file": "pyproject.toml", "license_file": "LICENSE", "repository": "https://example.org/toolname", "license": "MIT License"}, "the link comes from pyproject.toml and the name from the first LICENSE line"


def replaced_readme(tmp_path, old, new):
    write_tree(tmp_path, site_files())
    path = tmp_path / "README.md"
    assert old in path.read_text(), f"the fixture README lacks {old!r}"
    path.write_text(path.read_text().replace(old, new))


@pytest.mark.parametrize(
    ("old", "new", "message"),
    [
        ("## What works today\n", "## What runs today\n", "holds 0 '## What works today' headings"),
        ("| Command | What it does | Status |\n|---|---|---|\n| `toolname plan check <plan.json>` | Checks a plan. | works |\n| `toolname decide` | Gives a decision. | not built (T43) |\n", "", "needs a header, a separator and a row"),
        ("| `toolname plan check <plan.json>` | Checks a plan. | works |\n| `toolname decide` | Gives a decision. | not built (T43) |\n", "", "needs a header, a separator and a row"),
        ("| Command | What it does | Status |", "| Command | Does | Status |", "the command table head must be"),
        ("|---|---|---|", "| a | b | c |", "must be the separator"),
        ("| Checks a plan. | works |", "| Checks a plan. | done |", "has the status 'done'"),
        ("| Checks a plan. | works |", "| works |", "has 2 cells, not 3"),
        ("| Checks a plan. | works |", "|  | works |", "has an empty cell"),
        ("| Checks a plan. | works |", "| Checks a plan. | works", "ends with"),
        ("| Gives a decision. | not built (T43) |", "| Gives a decision. | not built |", "has the status 'not built'"),
        ("```sh", "```bash", "needs sh code blocks with commands"),
        ("```sh\nuv sync\ntoolname plan check plan.json\n```\n", "```sh\n```\n", "needs sh code blocks with commands"),
        ("```sh\ntoolname run plan.json --runs 3\n```\n", "```sh\ntoolname run plan.json --runs 3\n", "leaves a code block open"),
        ("Run the plan.\n```sh", "```sh", "opens a code block with no sentence before it"),
        ("## Try it offline\n", "## Try it online\n", "holds 0 '## Try it offline' headings"),
        ("## Limits of isolation\nRuns use a `sandbox`.\nThe process is not confined.\n", "## Limits of isolation\n", "holds no text"),
        ("## Limits of isolation\n", "## Isolation\n", "holds 0 '## Limits of isolation' headings"),
        ("You write rules in `CLAUDE.md`. Do they load?\n\n", "", "needs the description and one more paragraph"),
    ],
)
def test_a_missing_or_malformed_readme_block_fails_loudly(tmp_path, old, new, message):
    replaced_readme(tmp_path, old, new)
    with pytest.raises(AssertionError, match=message) as raised:
        extract.readme_data(tmp_path)
    assert "Fix" in str(raised.value), f"the failure must say how to fix it, got {raised.value}"
    assert raised.type is AssertionError, f"expected an assertion failure, got {raised.type}"


def test_a_repeated_heading_fails_loudly(tmp_path):
    replaced_readme(tmp_path, "## Working on it\n", "## Limits of isolation\n")
    with pytest.raises(AssertionError, match="holds 2 '## Limits of isolation' headings, not one") as raised:
        extract.readme_data(tmp_path)
    assert "Fix" in str(raised.value), f"the failure must say how to fix it, got {raised.value}"
    assert raised.type is AssertionError, f"expected an assertion failure, got {raised.type}"


@pytest.mark.parametrize(
    ("file", "text", "message"),
    [
        ("pyproject.toml", '[project]\nname = "x"\n\n[project.urls]\nRepository = "git@host:x"\n', "must be an https link"),
        ("pyproject.toml", '[project]\nname = "x"\n', "urls"),
        ("LICENSE", "\n", "opens with no license name"),
    ],
)
def test_a_missing_repository_or_license_fails_the_build_data(tmp_path, file, text, message):
    write_tree(tmp_path, site_files())
    (tmp_path / file).write_text(text)
    with pytest.raises((AssertionError, KeyError), match=message) as raised:
        extract.project_data(tmp_path)
    assert raised.type in (AssertionError, KeyError), f"expected an assertion or a missing key, got {raised.type}"
