import pytest

import docs_freshness
from files import write_tree

CONTRACT = "# willitharness: domain contract (v0.5)\n\nplan CI-01 settled it. W1 to W3 was the old range.\n\n## 8. Traceability\n| ID group | Where it must appear |\n|---|---|\n| V1 to V2, W1 to W2 | BDD features, tests |\n\n## 9. Out of scope\n"
BACKLOG = "3 tasks in dependency order (contract v0.5).\n\nSummary:\n| Milestone | Tasks | Count |\n|---|---|---|\n| M0 skeleton | T01 to T02 | 2 |\n| M1 more | T03 | 1 |\n\n## M0. Skeleton\n### T01. a\n### T02. b\n## M1. More\n### T03. c\n"
MILESTONES = "| G0.1 | cmd | out | bad |\n| G0.2 (@live) | cmd | out | bad |\n"
ISSUES = "| ID | Gap |\n|---|---|\n| CI-01 | gap |\n| CI-02 | gap |\n"
CLI = 'USAGE = (\n    "usage: willitharness plan check <plan.json> "\n    "| willitharness probe --agent fake|claude --runs N"\n)\n'
MAKEFILE = "check: test zanity\n\ntest:\n\tx\n\nzanity:\n\tx\n\npilot:\n\tx\n"
FEATURE = "Feature: f\n  Scenario: one\n  Scenario Outline: two\n"
GOOD_FILES = {
    "docs/contract.md": CONTRACT,
    "docs/plan/07-task-backlog.md": BACKLOG,
    "docs/plan/03-milestones-and-checkpoints.md": MILESTONES,
    "docs/plan/contract-issues.md": ISSUES,
    "src/willitharness/cli.py": CLI,
    "Makefile": MAKEFILE,
    "features/a.feature": FEATURE,
    "scripts/gates/mutant_modules/a.py": "TESTS = ()\n",
    "README.md": "# tool\n`make check` runs the tests and zanity.\n",
}


def errors_for(tmp_path, overrides):
    write_tree(tmp_path, {**GOOD_FILES, **overrides})
    return docs_freshness.docs_freshness_errors(tmp_path)


def single_error(tmp_path, text):
    errors = errors_for(tmp_path, {"docs/plan/README.md": text})
    assert len(errors) == 1, f"{text!r} must give one error, got {errors}"
    return errors[0]


def test_a_good_tree_has_no_errors(tmp_path):
    errors = errors_for(tmp_path, {"docs/plan/README.md": "Contract: v0.5 (4 IDs). `make pilot`. `willitharness probe --agent fake`.\n"})
    assert errors == [], f"a good tree must pass, got {errors}"


def test_facts_come_from_the_sources(tmp_path):
    write_tree(tmp_path, GOOD_FILES)
    facts = docs_freshness.read_facts(tmp_path)
    assert facts["contract_version"] == "0.5" and facts["id_count"] == 4 and facts["world_rule_count"] == 2, f"contract facts wrong: {facts}"
    assert (facts["task_count"], facts["milestone_count"], facts["gate_count"], facts["live_gate_count"]) == (3, 2, 2, 1), f"count facts wrong: {facts}"
    assert (facts["feature_count"], facts["scenario_count"], facts["mutant_module_count"], facts["issue_count"]) == (1, 2, 1, 2), f"count facts wrong: {facts}"
    assert facts["make_targets"] == {"check", "test", "zanity", "pilot"} and facts["check_dependencies"] == ["test", "zanity"], f"make facts wrong: {facts}"
    assert facts["commands"] == {"plan check": set(), "probe": {"--agent", "--runs"}}, f"command facts wrong: {facts['commands']}"


def test_a_stale_contract_version_is_reported(tmp_path):
    error = single_error(tmp_path, "Contract: v0.2.\n")
    assert "'Contract: v0.2' but the source says contract_version = 0.5" in error, f"{error!r} lacks the expected text"


def test_a_stale_id_count_is_reported(tmp_path):
    error = single_error(tmp_path, "all 43 IDs covered\n")
    assert "id_count = 4" in error, f"{error!r} lacks the expected text"


def test_a_stale_world_range_is_reported(tmp_path):
    error = single_error(tmp_path, "World validation W1 to W3\n")
    assert "world_rule_count = 2" in error, f"{error!r} lacks the expected text"


def test_a_stale_table_row_is_reported(tmp_path):
    errors = errors_for(tmp_path, {"docs/plan/README.md": "| Backlog tasks | 50 (T01 to T50) |\n"})
    assert len(errors) == 2, f"the count and the last task are both stale, got {errors}"
    assert all("task_count = 3" in error for error in errors), f"got {errors}"


def test_an_id_list_that_misses_an_id_is_reported(tmp_path):
    error = single_error(tmp_path, "| Contract IDs covered | 4 (V1 to V2, W1) |\n")
    assert "differ from the contract by ['W2']" in error, f"{error!r} lacks the expected text"


def test_an_issue_the_contract_resolved_is_not_open(tmp_path):
    errors = errors_for(tmp_path, {"docs/plan/README.md": "CI-01 (open) and CI-02 (open)\n"})
    assert len(errors) == 1, f"only CI-01 is resolved, got {errors}"
    assert "calls CI-01 open" in errors[0], f"got {errors[0]}"


def test_a_not_yet_statement_is_reported_only_when_code_exists(tmp_path):
    error = single_error(tmp_path, "No code exists yet.\n")
    assert "holds code" in error, f"{error!r} lacks the expected text"
    assert docs_freshness.read_facts(tmp_path)["has_code"] is True, f"the fixture tree under {tmp_path} holds a package module"


def test_not_yet_errors_stay_silent_without_code():
    errors = docs_freshness.not_yet_errors("README.md", "No code exists yet.\n", {"has_code": False})
    assert errors == [], f"a repository without code may say so, got {errors}"
    assert docs_freshness.not_yet_errors("README.md", "fine\n", {"has_code": True}) == [], "a clean text must pass"


def test_an_unknown_command_is_reported(tmp_path):
    error = single_error(tmp_path, "run `willitharness init <dir>`\n")
    assert "documents `willitharness init`" in error, f"{error!r} lacks the expected text"


def test_an_unknown_flag_is_reported(tmp_path):
    error = single_error(tmp_path, "run `willitharness probe --agent fake --turbo`\n")
    assert "flags ['--turbo']" in error, f"{error!r} lacks the expected text"


def test_an_unknown_make_target_is_reported(tmp_path):
    error = single_error(tmp_path, "run `make deploy`\n")
    assert "`make deploy`" in error, f"{error!r} lacks the expected text"


def test_a_make_check_sentence_must_name_every_dependency(tmp_path):
    errors = errors_for(tmp_path, {"README.md": "`make check` runs the tests.\n"})
    assert len(errors) == 1 and "leaves out ['zanity']" in errors[0], f"got {errors}"


def test_a_make_check_dependency_without_a_phrase_fails_loudly(tmp_path):
    with pytest.raises(AssertionError, match="CHECK_PHRASES has no phrase") as raised:
        errors_for(tmp_path, {"Makefile": MAKEFILE.replace("check: test zanity", "check: test zanity novel")})
    assert "novel" in str(raised.value), f"the failure must name the dependency, got {raised.value}"
    assert raised.type is AssertionError, f"expected an assertion failure, got {raised.type}"


def test_a_missing_referenced_file_is_reported(tmp_path):
    error = single_error(tmp_path, "see `docs/gone.md`\n")
    assert "points at docs/gone.md" in error, f"{error!r} lacks the expected text"


def test_a_gate_row_naming_a_missing_script_is_reported(tmp_path):
    row = "| G0.3 | `uv run python scripts/gates/missing.py` | out | bad |\n"
    errors = errors_for(tmp_path, {"docs/plan/03-milestones-and-checkpoints.md": MILESTONES + row})
    assert len(errors) == 1 and "points at scripts/gates/missing.py" in errors[0], f"a missing script must fail, got {errors}"
    assert errors[0].startswith("docs/plan/03-milestones-and-checkpoints.md:3"), f"the error must cite the row, got {errors[0]}"


def test_a_gate_row_naming_a_missing_test_path_or_module_is_reported(tmp_path):
    rows = "| G0.4 | `uv run pytest tests/missing_test.py` | out | bad |\n| G0.5 | `uv run python -m willitharness.missing` | out | bad |\n"
    errors = errors_for(tmp_path, {"docs/plan/03-milestones-and-checkpoints.md": MILESTONES + rows})
    assert len(errors) == 2, f"both rows must fail, got {errors}"
    assert "points at tests/missing_test.py" in errors[0] and "runs module willitharness.missing" in errors[1], f"got {errors}"


def test_existing_scripts_tests_and_modules_pass(tmp_path):
    rows = "| G0.3 | `uv run pytest tests/test_fixture.py -m live` | out | bad |\n| G0.4 | `uv run python -m willitharness.cli` | out | bad |\n| G0.5 | `uv run python scripts/gates/trace_check.py` | out | bad |\n"
    files = {"src/willitharness/cli.py": CLI, "tests/test_fixture.py": "x = 1\n", "scripts/gates/trace_check.py": "x = 1\n", "docs/plan/03-milestones-and-checkpoints.md": MILESTONES + rows}
    assert errors_for(tmp_path, files) == [], "real paths and modules must pass"
    assert docs_freshness.read_facts(tmp_path)["task_ids"] == {"T01", "T02", "T03"}, "task ids come from the backlog headings"


def test_a_not_built_marker_exempts_its_row_and_its_task_section(tmp_path):
    backlog = BACKLOG.replace("### T03. c", "### T03. c not built (T03)").replace("### T02. b", "### T02. b not built (T02)") + "- run `scripts/gates/later.sh` and `willitharness report <plan>`\n"
    row = "| G0.3 | `not built (T02)` run `scripts/gates/later.sh` | out | bad |\n"
    files = {"docs/plan/07-task-backlog.md": backlog, "docs/plan/03-milestones-and-checkpoints.md": MILESTONES + row}
    assert errors_for(tmp_path, files) == [], "a marked row and a marked task section may name what does not exist"
    assert docs_freshness.planned_lines(backlog) == {11: "T02", 13: "T03", 14: "T03"}, "the marked headings and the lines under them are planned"


def test_text_after_an_unmarked_heading_is_checked(tmp_path):
    backlog = BACKLOG.replace("### T03. c", "### T03. c not built (T03)") + "## M2. Next\n- run `scripts/gates/later.sh`\n"
    errors = errors_for(tmp_path, {"docs/plan/07-task-backlog.md": backlog})
    assert len(errors) == 1 and "points at scripts/gates/later.sh" in errors[0], f"a new heading ends the planned section, got {errors}"
    assert errors[0].startswith("docs/plan/07-task-backlog.md:15"), f"got {errors[0]}"


def test_a_marker_without_a_task_id_or_with_an_unknown_one_is_reported(tmp_path):
    unmarked = single_error(tmp_path, "| G1.1 | not built | out | bad |\n")
    assert "says 'not built' without a task id" in unmarked, f"{unmarked!r} lacks the expected text"
    unknown = single_error(tmp_path, "| G1.1 | `not built (T99)` | out | bad |\n")
    assert "marks a row not built for T99" in unknown, f"{unknown!r} lacks the expected text"


def test_a_reference_beside_the_document_and_a_glob_pass(tmp_path):
    errors = errors_for(tmp_path, {"docs/plan/README.md": "see `../contract.md`, `docs/contract.md` and `docs/*.md`\n"})
    assert errors == [], f"a relative file and a glob must pass, got {errors}"


def test_a_summary_row_with_the_wrong_count_is_reported(tmp_path):
    errors = errors_for(tmp_path, {"docs/plan/07-task-backlog.md": BACKLOG.replace("T01 to T02 | 2", "T01 to T02 | 3")})
    assert any("spans 2" in error for error in errors), f"got {errors}"
    assert any("add up to 4 tasks" in error for error in errors), f"got {errors}"


def test_a_header_count_that_differs_from_the_headings_fails_loudly(tmp_path):
    with pytest.raises(AssertionError, match="holds 3 task headings") as raised:
        errors_for(tmp_path, {"docs/plan/07-task-backlog.md": BACKLOG.replace("3 tasks in", "9 tasks in")})
    assert "says 9 tasks" in str(raised.value), f"the failure must quote the header, got {raised.value}"
    assert raised.type is AssertionError, f"expected an assertion failure, got {raised.type}"


@pytest.mark.parametrize("path", ["docs/research/old.md", "docs/contract-v0.1.md"])
def test_historical_documents_are_not_checked(tmp_path, path):
    errors = errors_for(tmp_path, {path: "Contract: v0.1 (43 IDs). W1 to W3.\n"})
    assert errors == [], f"{path} is exempt, got {errors}"
    assert docs_freshness.HISTORICAL_REASON, "the exemption must say why"


README_TABLE = "# tool\n`make check` runs the tests and zanity.\n\n| Path | What |\n|---|---|\n| `docs/plan/` | Plans. |\n| `.githooks/pre-push` | The push hook. |\n| `src/willitharness/` | The package. |\n\nRun `pytest` and read `Makefile`.\n"
README_TREE = {"README.md": README_TABLE, ".githooks/pre-push": "#!/bin/sh\n"}


def readme_errors(tmp_path, readme, extra=None):
    return errors_for(tmp_path, {**README_TREE, **(extra or {}), "README.md": readme})


def test_a_readme_whose_table_paths_exist_has_no_errors(tmp_path):
    errors = readme_errors(tmp_path, README_TABLE)
    assert errors == [], f"directories and scripts that exist must pass, got {errors}"


def test_a_missing_directory_in_the_readme_table_is_reported_with_value_rule_and_fix(tmp_path):
    errors = readme_errors(tmp_path, README_TABLE + "| `formal/tla/` | The model. |\n")
    assert len(errors) == 1, f"one missing directory must give one error, got {errors}"
    row_line = README_TABLE.count("\n") + 1
    assert errors[0].startswith(f"README.md:{row_line} points at formal/tla/, which does not exist."), f"the line and value are missing in {errors[0]!r}"
    assert "Rule:" in errors[0] and "Fix:" in errors[0], f"the error needs a Rule and a Fix, got {errors[0]!r}"


def test_a_missing_script_without_a_suffix_is_reported(tmp_path):
    errors = readme_errors(tmp_path, README_TABLE.replace(".githooks/pre-push", ".githooks/pre-pus"))
    assert len(errors) == 1 and ".githooks/pre-pus" in errors[0], f"a typo in an extensionless script must be reported, got {errors}"


def test_a_missing_make_target_in_the_readme_is_reported(tmp_path):
    errors = readme_errors(tmp_path, README_TABLE + "Run `make deploy` to publish.\n")
    assert len(errors) == 1 and "make deploy" in errors[0], f"a make target the Makefile lacks must be reported, got {errors}"


def test_a_slashed_word_that_is_not_a_repo_path_is_left_alone(tmp_path):
    errors = readme_errors(tmp_path, README_TABLE + "Branches are named `type/slug`.\n")
    assert errors == [], f"a token whose first segment is not in the tree and has no trailing slash is not a path claim, got {errors}"


def test_an_unknown_directory_with_a_trailing_slash_is_a_path_claim(tmp_path):
    errors = readme_errors(tmp_path, README_TABLE + "Notes live in `notes/`.\n")
    assert len(errors) == 1 and "notes/" in errors[0], f"a trailing slash makes the token a directory claim, got {errors}"


@pytest.mark.parametrize("token", ["`src/missing::case`", "`scripts/*`", "`/tmp/elsewhere`", "`docs/<name>`", "`src/--flag`", "`docs/KEY=value`", "`docs/${HOME}`", "`docs/a|b`"])
def test_tokens_that_are_not_plain_paths_are_not_checked(tmp_path, token):
    errors = readme_errors(tmp_path, README_TABLE + f"See {token}.\n")
    assert errors == [], f"{token} is not a plain path and must not be checked, got {errors}"


def test_a_not_built_marker_exempts_a_readme_row(tmp_path):
    marked_backlog = {"docs/plan/07-task-backlog.md": BACKLOG.replace("### T01. a", "### T01. a not built (T01)")}
    errors = readme_errors(tmp_path, README_TABLE + "| `formal/tla/` | The model, not built (T01). |\n", marked_backlog)
    assert errors == [], f"a row marked not built is exempt, got {errors}"


def test_a_marker_for_a_task_the_backlog_no_longer_marks_is_reported(tmp_path):
    errors = readme_errors(tmp_path, README_TABLE + "| `formal/tla/` | The model, not built (T01). |\n")
    stale = [error for error in errors if "has no 'not built (T01)' marker" in error]
    assert len(stale) == 1, f"a marker for a built task must give one stale error, got {errors}"
    assert "Rule:" in stale[0] and "Fix:" in stale[0], f"the error must state a rule and a fix, got {stale[0]!r}"


def test_other_documents_are_not_held_to_the_readme_path_rule(tmp_path):
    errors = errors_for(tmp_path, {**README_TREE, "docs/plan/README.md": "Models live in `formal/tla/`.\n"})
    assert errors == [], f"only the README is checked for directories, got {errors}"


def test_a_missing_script_with_a_suffix_is_reported_once(tmp_path):
    errors = readme_errors(tmp_path, README_TABLE + "Run `scripts/missing/tool.py` first.\n")
    assert len(errors) == 1 and "scripts/missing/tool.py" in errors[0], f"the reference check and the path check must not both report it, got {errors}"


WORLD = 'STORE_DIR = ".willitharness"\n'


def test_a_runtime_folder_the_code_defines_is_accepted_in_every_documented_form(tmp_path):
    readme = "# tool\n`.willitharness/` holds runs. Delete with `rm -r .willitharness` or `rm -r .willitharness/<plan>`.\n"
    errors = errors_for(tmp_path, {"README.md": readme, "src/willitharness/world.py": WORLD})
    assert errors == [], f"the runtime folder must be accepted, got {errors}"
    assert docs_freshness.RUNTIME_PATHS == (".willitharness",), f"the runtime paths are {docs_freshness.RUNTIME_PATHS}"


def test_a_runtime_folder_the_code_no_longer_defines_is_reported(tmp_path):
    readme = "# tool\nDelete with `rm -r .willitharness`.\n"
    errors = errors_for(tmp_path, {"README.md": readme, "src/willitharness/world.py": 'STORE_DIR = ".other"\n'})
    assert len(errors) == 1 and "names the runtime folder .willitharness" in errors[0], f"got {errors}"
    missing = errors_for(tmp_path, {"README.md": readme})
    assert len(missing) == 1, f"a missing source file must also be reported, got {missing}"
