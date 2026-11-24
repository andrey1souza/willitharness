import json
from pathlib import Path

import plugin_checks
import repo_checks
from files import write_tree

REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST = "plugin/.claude-plugin/plugin.json"
SKILL = "plugin/skills/audit-rules/SKILL.md"
CLI = "src/willitharness/cli.py"
GOOD_MANIFEST = json.dumps({"name": "willitharness", "version": "0.0.0", "description": "Audit the rules of a repository."})
GOOD_SKILL = (
    "---\nname: audit-rules\ndescription: Audit the rules of a repository.\n---\n"
    "Run `willitharness audit DIR` on the repository of the user.\n"
    "Show the report. Never edit the repository of the user.\n"
    "Paid tests are a separate step. They are not built yet.\n"
)
GOOD_CLI = 'USAGE = "usage: willitharness audit DIR | willitharness plan check <plan.json>"\n'
LONG_SENTENCE = "Run the command and then read the whole report and then show it to the user and then wait for the user to answer.\n"


def plugin_errors_for(tmp_path, overrides=None):
    files = {MANIFEST: GOOD_MANIFEST, SKILL: GOOD_SKILL, CLI: GOOD_CLI}
    files.update(overrides or {})
    write_tree(tmp_path, {name: text for name, text in files.items() if text is not None})
    return plugin_checks.plugin_errors(tmp_path)


def test_a_good_plugin_passes(tmp_path):
    assert plugin_errors_for(tmp_path) == [], "the good plugin is the required shape"


def test_the_real_plugin_passes():
    assert plugin_checks.plugin_errors(REPO_ROOT) == [], "the shipped plugin must pass its own gate"


def test_a_manifest_that_is_not_json_is_reported(tmp_path):
    errors = plugin_errors_for(tmp_path, {MANIFEST: "{not json"})
    assert len(errors) == 1 and "not valid JSON" in errors[0], f"got {errors}"


def test_a_manifest_without_a_name_is_reported(tmp_path):
    errors = plugin_errors_for(tmp_path, {MANIFEST: json.dumps({"version": "1", "description": "d"})})
    assert len(errors) == 1 and "name" in errors[0], f"got {errors}"


def test_a_skill_without_frontmatter_is_reported(tmp_path):
    errors = plugin_errors_for(tmp_path, {SKILL: "Run `willitharness audit DIR`. Never edit. Paid tests wait.\n"})
    assert any("frontmatter" in error for error in errors), f"got {errors}"


def test_a_skill_whose_name_differs_from_its_folder_is_reported(tmp_path):
    errors = plugin_errors_for(tmp_path, {SKILL: GOOD_SKILL.replace("name: audit-rules", "name: other")})
    assert len(errors) == 1 and "folder" in errors[0], f"got {errors}"


def test_a_skill_that_names_a_command_the_cli_lacks_is_reported(tmp_path):
    errors = plugin_errors_for(tmp_path, {CLI: 'USAGE = "usage: willitharness plan check <plan.json>"\n'})
    assert len(errors) == 1 and "audit" in errors[0], f"got {errors}"


def test_a_skill_that_does_not_name_the_command_is_reported(tmp_path):
    errors = plugin_errors_for(tmp_path, {SKILL: GOOD_SKILL.replace("willitharness audit DIR", "the tool")})
    assert any("willitharness audit" in error for error in errors), f"got {errors}"


def test_a_skill_without_the_never_edit_rule_is_reported(tmp_path):
    errors = plugin_errors_for(tmp_path, {SKILL: GOOD_SKILL.replace("Never edit", "Do not touch")})
    assert any("Never edit" in error for error in errors), f"got {errors}"


def test_a_skill_that_hides_the_paid_step_is_reported(tmp_path):
    errors = plugin_errors_for(tmp_path, {SKILL: GOOD_SKILL.replace("Paid tests", "Other tests")})
    assert any("Paid tests" in error for error in errors), f"got {errors}"


def test_a_sentence_over_twenty_words_is_reported(tmp_path):
    errors = plugin_errors_for(tmp_path, {SKILL: GOOD_SKILL + LONG_SENTENCE})
    assert len(errors) == 1 and "words" in errors[0], f"got {errors}"


def test_a_missing_plugin_is_reported(tmp_path):
    errors = plugin_errors_for(tmp_path, {MANIFEST: None})
    assert len(errors) == 1 and "missing" in errors[0], f"got {errors}"


def test_the_plugin_check_is_part_of_the_repository_checks():
    missing = [name for name in plugin_checks.CHECKS if name not in repo_checks.CHECKS]
    assert missing == [], f"repo_checks.CHECKS must run {missing}"
