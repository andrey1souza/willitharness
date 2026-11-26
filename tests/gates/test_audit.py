import hashlib
import json
import re

from cli_runner import run_cli
from audit_fixtures import append_line, copy_audit_fixture, text_of
from files import write_tree

from willitharness.audit import PREDICTION_LABEL, build_audit
from willitharness.guard import guard_rule_of
from willitharness.load_report import build_load_report

AGENTS_ONLY = "agents-only"
MASKED = "masked"
EXIT_OK = 0
EXIT_REFUSED = 1
SECTIONS = ("## What loads", "## Rules", "## Predictions", "## Proposed changes", "## Limits")
GUARD_BLOCK = re.compile(r"```json\n(.*?)\n```", re.DOTALL)
DIFF_BLOCK = re.compile(r"```diff\n(.*?)\n```", re.DOTALL)
EXPECTED_CLASSES = (
    ("Run `scripts/check.sh` before every commit.", "enforced by a script"),
    ("Never use `pkill`", "command rule, testable candidate"),
    ("Use `git -C PATH`", "command rule, testable candidate"),
    ("Never use `git push --force`.", "command rule, testable candidate"),
    ("Always run `make test`", "command rule, testable candidate"),
    ("Run `scripts/lint-all.sh`", "not testable by behaviour"),
    ("Keep `README.md` short.", "not testable by behaviour"),
    ("Use `snake_case`", "not testable by behaviour"),
    ("`npm ci && npx tsc --noEmit`", "command rule, testable candidate"),
    ("Never push to `main`.", "command rule, testable candidate"),
    ("Write sentences of 20 words", "not testable by behaviour"),
    ("Name things by what they do", "not testable by behaviour"),
)
PKILL_ALTERNATIVES = ["ps -axo pid,command", "kill PID"]
PKILL_HOOK = {"hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": "python3 guard.py pkill"}]}]}}
UNIX_DIFF_NEW_FILE = "--- /dev/null\n+++ CLAUDE.md\n"


def file_hashes_of(root):
    files = sorted(path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file())
    return files, {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in files}


def write_extra_file(root):
    (root / "stray.txt").write_text("written by a helper\n")
    return root


def audit_copy(tmp_path, name):
    copy = copy_audit_fixture(tmp_path, name)
    return copy, build_audit(copy.resolve(), ceiling=copy.resolve())


def rule_rows(report):
    return [line for line in report.splitlines() if line.startswith("| ") and "|---" not in line and " Class " not in line]


def test_the_report_has_every_section_in_order_and_the_prediction_label(tmp_path):
    _, report = audit_copy(tmp_path, AGENTS_ONLY)
    positions = [report.index(section) for section in SECTIONS]
    assert positions == sorted(positions), f"sections out of order: {positions}"
    assert PREDICTION_LABEL == "predicted, not verified; a paid probe confirms it", f"the label changed to {PREDICTION_LABEL!r}"
    assert PREDICTION_LABEL in report, "the report must label its loading verdict"
    assert "instruction AGENTS.md:" in report, "the load report lines must appear"


def test_the_rules_table_lists_each_rule_with_its_class(tmp_path):
    _, report = audit_copy(tmp_path, AGENTS_ONLY)
    rows = rule_rows(report)
    assert len(rows) == len(EXPECTED_CLASSES), f"got {len(rows)} rows for {len(EXPECTED_CLASSES)} rules: {rows}. Fix: list every rule once."
    for (start, label), row in zip(EXPECTED_CLASSES, rows, strict=True):
        assert start in row and f"| {label} |" in row, f"expected {start!r} as {label!r}, got {row!r}"


def test_a_long_rule_is_shortened_in_the_table(tmp_path):
    write_tree(tmp_path, {"CLAUDE.md": "- " + "word " * 60 + "end.\n"})
    report = build_audit(tmp_path.resolve(), ceiling=tmp_path.resolve())
    assert "word end." not in report and "..." in rule_rows(report)[0], f"got {rule_rows(report)}"


def test_the_guard_proposal_is_valid_for_the_forbidden_command_only(tmp_path):
    _, report = audit_copy(tmp_path, AGENTS_ONLY)
    entries = [json.loads(block) for block in GUARD_BLOCK.findall(report)]
    assert [entry["name"] for entry in entries] == ["pkill"], f"only the pkill rule has a derivable entry, got {entries}"
    rule = guard_rule_of(entries[0])
    assert list(rule.offered_alternatives) == PKILL_ALTERNATIVES and rule.blocked[0].program == "pkill", f"got {rule}"
    assert "git push --force" in report and "no entry derivable" in report, "a forbidden command with no derivable entry is named"
    assert "the rule requires `git -C PATH`" in report, "a required command gets a note, not an entry"
    assert DIFF_BLOCK.findall(report) == [], "a loaded AGENTS.md needs no CLAUDE.md"


def test_a_hook_that_names_the_command_counts_as_an_enforcing_guard(tmp_path):
    write_tree(tmp_path, {"CLAUDE.md": "- Never use `pkill`.\n", ".claude/settings.json": json.dumps(PKILL_HOOK)})
    report = build_audit(tmp_path.resolve(), ceiling=tmp_path.resolve())
    assert GUARD_BLOCK.findall(report) == [], "a guard exists, so no entry is proposed"
    assert "| command rule, testable candidate |" in report, "the rule stays a testable candidate"


def test_a_hook_on_another_event_is_not_an_enforcing_guard(tmp_path):
    other = {"hooks": {"PostToolUse": PKILL_HOOK["hooks"]["PreToolUse"]}}
    write_tree(tmp_path, {"CLAUDE.md": "- Never use `pkill`.\n", ".claude/settings.json": json.dumps(other)})
    report = build_audit(tmp_path.resolve(), ceiling=tmp_path.resolve())
    assert len(GUARD_BLOCK.findall(report)) == 1, "only a PreToolUse hook can block a call"


def test_a_forbidden_command_with_one_option_gets_a_flag_pattern(tmp_path):
    write_tree(tmp_path, {"CLAUDE.md": "- Never run `pgrep -f`.\n"})
    report = build_audit(tmp_path.resolve(), ceiling=tmp_path.resolve())
    rule = guard_rule_of(json.loads(GUARD_BLOCK.findall(report)[0]))
    assert rule.blocked[0].program == "pgrep" and rule.blocked[0].flag_pattern, f"got {rule}"


def test_a_masked_agents_file_gets_a_claude_import_diff(tmp_path):
    copy, report = audit_copy(tmp_path, MASKED)
    diffs = DIFF_BLOCK.findall(report)
    assert len(diffs) == 1 and "+@AGENTS.md" in diffs[0] and "+++ CLAUDE.md" in diffs[0], f"got {diffs}"
    assert "AGENTS.md: predicted not loaded" in report, "the masked file is predicted not loaded"
    assert text_of(copy, "CLAUDE.md") == "# Project\n\n- Keep answers short.\n", "the proposal must not be applied"
    assert GUARD_BLOCK.findall(report) == [], "a rule in a file that does not load gets no guard entry"


def test_applying_the_proposed_diff_makes_the_agents_file_load(tmp_path):
    copy, _ = audit_copy(tmp_path, MASKED)
    before = "\n".join(build_load_report(copy.resolve(), ceiling=copy.resolve()))
    assert "AGENTS.md: not loaded: masked by CLAUDE.md" in before, f"the fixture must start masked, got {before!r}"
    append_line(copy, "CLAUDE.md", "@AGENTS.md\n")
    after = "\n".join(build_load_report(copy.resolve(), ceiling=copy.resolve()))
    assert "instruction AGENTS.md:" in after and "not loaded" not in after, f"got {after}"


def test_a_masked_agents_file_without_claude_file_in_the_project_gets_a_new_file_diff(tmp_path):
    write_tree(tmp_path / "project" / ".claude", {"CLAUDE.md": "- Keep it short.\n"})
    write_tree(tmp_path / "project", {"AGENTS.md": "- Keep it short.\n"})
    report = build_audit((tmp_path / "project").resolve(), ceiling=(tmp_path / "project").resolve())
    diffs = DIFF_BLOCK.findall(report)
    assert len(diffs) == 1 and diffs[0].startswith(UNIX_DIFF_NEW_FILE) and "+@AGENTS.md" in diffs[0], f"got {diffs}"


def test_a_repo_with_no_derivable_change_says_none(tmp_path):
    write_tree(tmp_path, {"CLAUDE.md": "- Keep it short.\n"})
    report = build_audit(tmp_path.resolve(), ceiling=tmp_path.resolve())
    proposals = report.split("## Proposed changes")[1].split("## Limits")[0]
    assert "None" in proposals and "```" not in proposals, f"got {proposals!r}"


def test_the_limits_say_the_scan_predicts_and_paid_tests_did_not_run(tmp_path):
    _, report = audit_copy(tmp_path, AGENTS_ONLY)
    limits = report.split("## Limits")[1]
    assert "predicts" in limits and "does not measure" in limits and "paid tests" in limits.lower() and "not run" in limits, f"got {limits!r}"


def test_the_audit_never_writes_to_the_repo(tmp_path, capsys):
    for name in (AGENTS_ONLY, MASKED):
        copy = copy_audit_fixture(tmp_path, name)
        before = file_hashes_of(copy)
        code, out, err = run_cli(capsys, ["audit", str(copy)])
        assert code == EXIT_OK and "## Limits" in out and err == "", f"got {code} {err!r}"
        assert file_hashes_of(copy) == before, f"the audit changed {name}: {before}"


def test_the_hash_check_can_fail_when_a_helper_writes_a_file(tmp_path):
    copy = copy_audit_fixture(tmp_path, AGENTS_ONLY)
    before = file_hashes_of(copy)
    write_extra_file(copy)
    assert file_hashes_of(copy) != before, f"the read-only check missed a written file in {copy}: {before}"
    (copy / "stray.txt").unlink()
    (copy / "AGENTS.md").write_text("changed\n")
    assert file_hashes_of(copy)[1] != before[1], f"the read-only check missed a changed file in {copy}: {before[1]}"


def test_a_missing_folder_is_refused_with_a_rule_and_a_fix(tmp_path, capsys):
    code, out, err = run_cli(capsys, ["audit", str(tmp_path / "missing")])
    assert code == EXIT_REFUSED and out == "" and "Rule:" in err and "Fix:" in err, f"got {code} {out!r} {err!r}"



HOOK_COMMAND = 'node "${CLAUDE_PLUGIN_ROOT}/hooks/guard-bash.mjs"'
PLUGIN_HOOKS = {"hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": HOOK_COMMAND}]}]}}
IMPORT_CORE = "import { deny } from './lib/guard-core.mjs';\n"
DENY_PKILL = "export const DENIED = ['pkill'];\n"
DENY_OTHER = "export const DENIED = ['rm'];\n"
PKILL_RULE = "- Never use `pkill`.\n"
GUARD_FILES = {"CLAUDE.md": PKILL_RULE, "plugin/hooks/hooks.json": json.dumps(PLUGIN_HOOKS), "plugin/hooks/guard-bash.mjs": IMPORT_CORE}


def guard_blocks_for(tmp_path, files):
    write_tree(tmp_path, files)
    report = build_audit(tmp_path.resolve(), ceiling=tmp_path.resolve())
    return GUARD_BLOCK.findall(report), report


def test_a_hook_whose_imported_code_names_the_command_is_a_guard(tmp_path):
    blocks, _ = guard_blocks_for(tmp_path, {**GUARD_FILES, "plugin/hooks/lib/guard-core.mjs": DENY_PKILL})
    assert blocks == [], f"the hook code denies pkill, so no entry is proposed, got {blocks}"


def test_a_hook_whose_code_does_not_name_the_command_gets_the_proposal(tmp_path):
    blocks, _ = guard_blocks_for(tmp_path, {**GUARD_FILES, "plugin/hooks/lib/guard-core.mjs": DENY_OTHER})
    assert len(blocks) == 1 and json.loads(blocks[0])["name"] == "pkill", f"got {blocks}"


def test_a_hook_script_that_names_the_command_itself_is_a_guard(tmp_path):
    files = {"CLAUDE.md": PKILL_RULE, ".claude/settings.json": json.dumps({"hooks": {"PreToolUse": [{"hooks": [{"type": "command", "command": "node $CLAUDE_PROJECT_DIR/tools/guard.mjs"}]}]}}), "tools/guard.mjs": "const blocked = ['pkill'];\n"}
    blocks, _ = guard_blocks_for(tmp_path, files)
    assert blocks == [], f"got {blocks}"


def test_imports_are_followed_one_level_only(tmp_path):
    files = {**GUARD_FILES, "plugin/hooks/lib/guard-core.mjs": "import './deeper.mjs';\n", "plugin/hooks/lib/deeper.mjs": DENY_PKILL}
    blocks, _ = guard_blocks_for(tmp_path, files)
    assert len(blocks) == 1, f"a file two imports away is not read, got {blocks}"


def test_code_of_a_hook_on_another_event_is_not_a_guard(tmp_path):
    other = {"hooks": {"PostToolUse": PLUGIN_HOOKS["hooks"]["PreToolUse"]}}
    blocks, _ = guard_blocks_for(tmp_path, {**GUARD_FILES, "plugin/hooks/hooks.json": json.dumps(other), "plugin/hooks/lib/guard-core.mjs": DENY_PKILL})
    assert len(blocks) == 1, f"got {blocks}"


def test_a_hook_script_outside_the_repo_is_never_read(tmp_path):
    repo = tmp_path / "repo"
    write_tree(tmp_path, {"outside.mjs": DENY_PKILL})
    hooks = {"hooks": {"PreToolUse": [{"hooks": [{"type": "command", "command": "node ../outside.mjs"}]}]}}
    blocks, _ = guard_blocks_for(repo, {"CLAUDE.md": PKILL_RULE, ".claude/settings.json": json.dumps(hooks)})
    assert len(blocks) == 1, f"got {blocks}"


def test_the_limits_say_hook_code_is_read_as_text_and_never_run(tmp_path):
    _, report = guard_blocks_for(tmp_path, {"CLAUDE.md": PKILL_RULE})
    limits = report.split("## Limits")[1]
    assert "Hook code is read as text" in limits and "never run" in limits, f"got {limits!r}"
