import json

import hook_checks
import repo_checks
import workflow_checks
from files import write_tree

TABLE_HEAD = "# Mistakes\n\n## Mistakes caught by a rule\n\n| Mistake | Category | Rule | Test |\n|---|---|---|---|\n"
TABLE_TAIL = "\n## Mistakes with no rule yet\n"
GOOD_ROW = "| m | c | r | `tests/gates/test_x.py::test_x` |\n"
TEST_FILE = "def test_x():\n    assert True\n"
FILE_CHECKS = {name: check for name, check in repo_checks.CHECKS.items() if name not in ("mutant-tables", "mutant-platforms", "trace-pending", "paid-gate-target", "no-tracked-generated", "contract-sentences", "docs_freshness", "readme-data-statement", "integrate-source-never-forces", "pr-text-self-contained", "failure-messages", "result-detector", *workflow_checks.CHECKS, *hook_checks.CHECKS)}
GOOD_README = (
    "# t\n\n## Limits of isolation\n"
    "Effect runs use Claude's own sandbox and have no network. Guard runs use macOS `sandbox-exec` and their network is open. The Linux sandbox path is untested.\n"
    "Run only plans you have read. Isolation is not a security boundary against a hostile plan.\n"
    "The `claude` process itself is not confined.\n\n## Next\n"
)
PENDING_GOOD = '[{"id": "S1", "place": "tests", "reason": "later"}]'


def valid_files(rows):
    return {
        "docs/mistakes-to-rules.md": TABLE_HEAD + rows + TABLE_TAIL,
        "tests/gates/test_x.py": TEST_FILE,
        ".gitignore": "build/\n.testmondata*\n",
        "zanity.toml": '# disable = ["example"]\n[infer]\nconcurrency = 8\n',
        "docs/plan/01.md": "Run pytest tests/bdd.\n",
        "README.md": GOOD_README,
    }


def test_a_valid_tree_passes_the_file_checks(tmp_path):
    write_tree(tmp_path, valid_files(GOOD_ROW))
    failures = repo_checks.run_checks(tmp_path, FILE_CHECKS)
    assert failures == [], f"a valid tree must pass, got {failures}"


def test_a_failing_check_is_named_in_the_failures(tmp_path):
    files = valid_files(GOOD_ROW)
    files[".gitignore"] = "build/\n"
    write_tree(tmp_path, files)
    failures = repo_checks.run_checks(tmp_path, FILE_CHECKS)
    assert len(failures) == len(repo_checks.WATCHER_FILES), f"expected one failure per watcher file, got {failures}"
    assert all(failure.startswith("gitignore:") for failure in failures), f"the failing check must be named, got {failures}"


def test_the_repository_passes_every_check(capsys):
    code = repo_checks.main([])
    output = capsys.readouterr().out
    assert code == repo_checks.EXIT_PASSED, f"the repository must pass its own checks; output {output!r}"
    assert f"{len(repo_checks.CHECKS)} checks passed" in output, f"unexpected output {output!r}"


def test_a_row_naming_a_missing_test_function_is_reported(tmp_path):
    row = "| m | c | r | `tests/gates/test_x.py::test_gone` |\n"
    write_tree(tmp_path, valid_files(row))
    errors = repo_checks.mistakes_table_errors(tmp_path)
    assert errors == ["row names tests/gates/test_x.py::test_gone, which is not in the file"], f"got {errors}"


def test_a_row_naming_a_missing_test_file_is_reported(tmp_path):
    row = "| m | c | r | `tests/gates/test_gone.py::test_x` |\n"
    write_tree(tmp_path, valid_files(row))
    errors = repo_checks.mistakes_table_errors(tmp_path)
    assert errors == ["row names tests/gates/test_gone.py, which does not exist"], f"got {errors}"


def test_a_row_with_no_test_reference_is_reported(tmp_path):
    write_tree(tmp_path, valid_files("| m | c | r | none |\n"))
    errors = repo_checks.mistakes_table_errors(tmp_path)
    assert len(errors) == 1 and errors[0].startswith("row has no test reference"), f"got {errors}"


def test_a_table_with_no_rows_is_reported(tmp_path):
    write_tree(tmp_path, valid_files(""))
    errors = repo_checks.mistakes_table_errors(tmp_path)
    assert errors == ["the caught-mistakes table has no rows"], f"got {errors}"


def test_a_valid_table_has_no_errors(tmp_path):
    write_tree(tmp_path, valid_files(GOOD_ROW))
    errors = repo_checks.mistakes_table_errors(tmp_path)
    assert errors == [], f"a valid table must have no errors, got {errors}"


def test_a_gitignore_without_the_watcher_files_is_reported(tmp_path):
    write_tree(tmp_path, {".gitignore": "build/\n"})
    errors = repo_checks.gitignore_errors(tmp_path)
    assert len(errors) == len(repo_checks.WATCHER_FILES), f"every watcher file must be reported, got {errors}"


def test_a_gitignore_with_the_wildcard_has_no_errors(tmp_path):
    write_tree(tmp_path, {".gitignore": ".testmondata*\n"})
    errors = repo_checks.gitignore_errors(tmp_path)
    assert errors == [], f"the wildcard must cover every watcher file, got {errors}"


def test_a_zanity_baseline_file_is_reported(tmp_path):
    write_tree(tmp_path, {"zanity-baseline.json": json.dumps({"findings": [{}]})})
    errors = repo_checks.baseline_errors(tmp_path)
    assert len(errors) == 1 and "zanity-baseline.json exists" in errors[0], f"got {errors}"


def test_a_tree_without_a_zanity_baseline_has_no_errors(tmp_path):
    write_tree(tmp_path, {"zanity.toml": "[infer]\n"})
    errors = repo_checks.baseline_errors(tmp_path)
    assert errors == [], f"no baseline file must pass, got {errors}"


def test_a_path_disable_in_the_zanity_config_is_reported(tmp_path):
    write_tree(tmp_path, {"zanity.toml": '[paths."tests/"]\ndisable = ["filesystem-in-test"]\n'})
    errors = repo_checks.zanity_config_errors(tmp_path)
    assert len(errors) == 1 and "in tests/" in errors[0], f"got {errors}"


def test_a_global_disable_in_the_zanity_config_is_reported(tmp_path):
    write_tree(tmp_path, {"zanity.toml": '[rules]\ndisable = ["recursion"]\n'})
    errors = repo_checks.zanity_config_errors(tmp_path)
    assert len(errors) == 1 and "everywhere" in errors[0], f"got {errors}"


def test_commented_or_empty_disable_lists_are_not_reported(tmp_path):
    write_tree(tmp_path, {"zanity.toml": '[rules]\ndisable = [\n  # "recursion",\n]\n[paths."tests/"]\ndisable = []\n'})
    errors = repo_checks.zanity_config_errors(tmp_path)
    assert errors == [], f"an empty list disables nothing, got {errors}"


def test_the_retired_behave_command_in_a_plan_file_is_reported(tmp_path):
    write_tree(tmp_path, {"docs/plan/03.md": "Run `behave features/x.feature`.\n"})
    errors = repo_checks.plan_command_errors(tmp_path)
    assert len(errors) == 1 and "03.md" in errors[0], f"got {errors}"


def test_a_missing_plan_directory_is_reported(tmp_path):
    errors = repo_checks.plan_command_errors(tmp_path)
    assert len(errors) == 1 and "holds no plan files" in errors[0], f"got {errors}"


def test_a_mutant_target_that_occurs_twice_or_changes_nothing_is_reported(tmp_path):
    write_tree(tmp_path, {"src/a.py": "x = 1\ny = 1\n"})
    table = (("two", "src/a.py", "1", "2"), ("same", "src/a.py", "x = 1", "x = 1"))
    errors = repo_checks.mutant_table_errors(tmp_path, {"demo": ((), table)})
    assert errors == [
        "demo/two: target occurs 2 times in src/a.py",
        "demo/same: the replacement equals the target",
    ], f"got {errors}"


def test_a_unique_mutant_target_has_no_errors(tmp_path):
    write_tree(tmp_path, {"src/a.py": "x = 1\ny = 2\n"})
    errors = repo_checks.mutant_table_errors(tmp_path, {"demo": ((), (("one", "src/a.py", "x = 1", "x = 3"),))})
    assert errors == [], f"a unique target must pass, got {errors}"


def test_a_valid_pending_file_has_no_errors(tmp_path):
    write_tree(tmp_path, {"scripts/gates/trace_pending.json": PENDING_GOOD})
    errors = repo_checks.pending_errors(tmp_path)
    assert errors == [], f"a complete entry must pass, got {errors}"


def test_a_pending_entry_without_a_reason_is_reported(tmp_path):
    write_tree(tmp_path, {"scripts/gates/trace_pending.json": '[{"id": "S1", "place": "tests"}]'})
    errors = repo_checks.pending_errors(tmp_path)
    assert len(errors) == 1 and "needs id, place and reason" in errors[0], f"got {errors}"


def test_a_pending_entry_with_an_unknown_place_or_an_empty_reason_is_reported(tmp_path):
    entries = '[{"id": "S1", "place": "nowhere", "reason": "x"}, {"id": "S2", "place": "tests", "reason": ""}]'
    write_tree(tmp_path, {"scripts/gates/trace_pending.json": entries})
    errors = repo_checks.pending_errors(tmp_path)
    assert len(errors) == 2, f"both entries must be reported, got {errors}"


def test_a_tracked_generated_file_is_reported():
    errors = repo_checks.generated_errors_among(["formal/tla/generated/Mutant_L1.tla", "formal/tla/WillItHarness.tla"])
    assert len(errors) == 1, f"only the generated file must be reported, got {errors}"
    assert "formal/tla/generated/Mutant_L1.tla" in errors[0], f"the error must name the file, got {errors}"


def test_files_outside_the_generated_folder_are_not_reported():
    errors = repo_checks.generated_errors_among(["formal/tla/WillItHarness.tla", "formal/tla/generated_notes.md", "src/x.py"])
    assert errors == [], f"only files under formal/tla/generated/ count, got {errors}"
    assert repo_checks.generated_errors_among([]) == [], "an empty list has nothing to report"


MAKEFILE_GOOD = ".PHONY: check live pilot\n\ncheck: test zanity\n\nlive:\n\tuv run python scripts/gates/run_live.py\n\npilot:\n\tuv run python scripts/gates/pilot_live.py\n"


def test_a_makefile_with_the_pilot_target_outside_check_and_live_passes(tmp_path):
    write_tree(tmp_path, {"Makefile": MAKEFILE_GOOD})
    assert repo_checks.paid_target_errors(tmp_path) == [], "the pilot target outside check and live is allowed"
    assert "paid-gate-target" in repo_checks.CHECKS, "the check is registered"


def test_a_check_target_that_depends_on_the_pilot_is_reported(tmp_path):
    write_tree(tmp_path, {"Makefile": MAKEFILE_GOOD.replace("check: test zanity", "check: test pilot")})
    errors = repo_checks.paid_target_errors(tmp_path)
    assert len(errors) == 1 and errors[0].startswith("make check reaches the paid pilot gate"), f"unexpected errors {errors}"


def test_a_live_recipe_that_runs_the_pilot_script_is_reported(tmp_path):
    live = "live:\n\tuv run python scripts/gates/run_live.py\n\tuv run python scripts/gates/pilot_live.py\n"
    write_tree(tmp_path, {"Makefile": MAKEFILE_GOOD.replace("live:\n\tuv run python scripts/gates/run_live.py\n", live)})
    errors = repo_checks.paid_target_errors(tmp_path)
    assert len(errors) == 1 and errors[0].startswith("make live reaches the paid pilot gate"), f"unexpected errors {errors}"


def test_a_makefile_without_the_pilot_target_is_reported(tmp_path):
    write_tree(tmp_path, {"Makefile": "check: test\n\nlive:\n\techo live\n"})
    errors = repo_checks.paid_target_errors(tmp_path)
    assert len(errors) == 1 and "has no pilot target" in errors[0], f"unexpected errors {errors}"

