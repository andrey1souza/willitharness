import runpy
from pathlib import Path

import message_check
import pytest
import repo_checks

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "gates" / "message_check.py"
SOURCE_ROOT = Path(__file__).resolve().parents[2] / "src"
GOOD_TEXT = "plan {name} is bad. Rule: a plan is valid. Fix: repair {name}."
GOOD_MODULE = 'def f(name):\n    raise ValueError(f"plan {name} is bad. Rule: a plan is valid. Fix: repair {name}.")\n'
FIXTURE_MODULE = 'def f():\n    raise ValueError("error")\n'
NO_RULE_MODULE = 'def f(name):\n    raise ValueError(f"plan {name} is bad. Fix: repair {name}.")\n'
NO_FIX_MODULE = 'def f(name):\n    raise ValueError(f"plan {name} is bad. Rule: a plan is valid.")\n'
NO_VALUE_MODULE = 'def f():\n    raise ValueError("the plan is bad. Rule: a plan is valid. Fix: repair it.")\n'
FIX_BEFORE_RULE_MODULE = 'def f(name):\n    raise ValueError(f"plan {name} is bad. Fix: repair it. Rule: a plan is valid.")\n'
EMPTY_FIX_MODULE = 'def f(name):\n    raise ValueError(f"plan {name} is bad. Rule: a plan is valid. Fix: ")\n'
STDERR_MODULE = 'import sys\n\ndef f():\n    print("error", file=sys.stderr)\n'
WRITE_MODULE = 'import sys\n\ndef f():\n    sys.stderr.write("error")\n'
CONSTANT_MODULE = 'MESSAGE = "error"\n\ndef f():\n    raise ValueError(MESSAGE)\n'
FORMAT_MODULE = 'MESSAGE = "error {name}"\n\ndef f():\n    raise ValueError(MESSAGE.format(name=1))\n'
QUIET_MODULE = 'def f(error):\n    raise ValueError(str(error))\n    print("not an error")\n'
PASS_LINE = "all 1 failure messages state the rule and end with a fix"
USAGE_MODULE = 'def f():\n    raise SystemExit("usage: tool <file>, got nothing")\n'
WARNING_MODULE = 'import sys\n\ndef f():\n    print("warning: it ends", file=sys.stderr)\n'
REPORT_REFUSALS = ("no verdicts yet; run: willitharness analyze", "plan aborted; no verdict")


def save_source_file(tmp_path, file_name, text):
    path = tmp_path / file_name
    path.write_text(text)
    assert path.read_text() == text, f"{path} did not keep its text"
    return path


def scan_source_file(tmp_path, capsys, file_name, text):
    save_source_file(tmp_path, file_name, text)
    code = message_check.scan_exit_code(tmp_path)
    return code, capsys.readouterr().out


def test_T48_a_message_with_value_rule_and_fix_passes_with_the_count(tmp_path, capsys):
    code, output = scan_source_file(tmp_path, capsys, "good.py", GOOD_MODULE)
    assert (code, output.strip()) == (0, PASS_LINE), f"got {code}: {output!r}"


def test_T48_the_fixture_message_error_exits_one(tmp_path, capsys):
    code, output = scan_source_file(tmp_path, capsys, "fixture.py", FIXTURE_MODULE)
    assert code == 1, f"the fixture message 'error' must exit 1, got {code}"
    assert "lacks the rule and a closing fix." in output, f"the fixture must lack the rule and the fix: {output!r}"


@pytest.mark.parametrize(
    ("module", "missing"),
    [
        (NO_RULE_MODULE, "lacks the rule."),
        (NO_FIX_MODULE, "lacks a closing fix."),
        (FIX_BEFORE_RULE_MODULE, "lacks a closing fix."),
        (EMPTY_FIX_MODULE, "lacks a closing fix."),
    ],
)
def test_T48_a_message_missing_one_part_exits_one_and_names_the_part(tmp_path, capsys, module, missing):
    code, output = scan_source_file(tmp_path, capsys, "bad.py", module)
    assert code == 1, f"a message that {missing} must exit 1, got {code}"
    assert missing in output and "bad.py:2:" in output, f"the failure must name the part and the line: {output!r}"


@pytest.mark.parametrize("module", [STDERR_MODULE, WRITE_MODULE, CONSTANT_MODULE, FORMAT_MODULE])
def test_T48_every_way_to_send_a_failure_is_checked(tmp_path, capsys, module):
    code, output = scan_source_file(tmp_path, capsys, "bad.py", module)
    assert code == 1, f"a bad message sent this way must exit 1, got {code}: {output!r}"


def test_T48_a_forwarded_exception_and_a_plain_print_are_not_messages(tmp_path, capsys):
    code, output = scan_source_file(tmp_path, capsys, "other.py", GOOD_MODULE + QUIET_MODULE)
    assert (code, output.strip()) == (0, PASS_LINE), f"got {code}: {output!r}"


def test_T48_a_constant_from_another_module_is_resolved(tmp_path, capsys):
    save_source_file(tmp_path, "defs.py", 'MESSAGE = "error"\n')
    code, output = scan_source_file(tmp_path, capsys, "use.py", "from defs import MESSAGE\n\ndef f():\n    raise ValueError(MESSAGE)\n")
    assert (code, "use.py:4:" in output) == (1, True), f"the shared constant must be checked at its raise site with exit 1: {code} {output!r}"


@pytest.mark.parametrize("text", REPORT_REFUSALS)
def test_T48_the_two_T47_report_refusals_are_exempt_in_report_py(tmp_path, capsys, text):
    code, output = scan_source_file(tmp_path, capsys, "report.py", f'def f():\n    raise ValueError("{text}")\n')
    assert (code, output.strip()) == (0, PASS_LINE), f"got {code}: {output!r}"


@pytest.mark.parametrize("text", REPORT_REFUSALS)
@pytest.mark.parametrize("file_name", ["cli.py", "other.py"])
def test_T48_the_same_text_from_any_other_command_fails(tmp_path, capsys, text, file_name):
    code, output = scan_source_file(tmp_path, capsys, file_name, f'def f():\n    raise ValueError("{text}")\n')
    assert (code, text in output) == (1, True), f"{text!r} in {file_name} must fail with exit 1 and name the text: {code} {output!r}"


def test_T48_analyze_in_lifecycle_py_may_say_plan_aborted_but_not_the_other_report_refusal(tmp_path, capsys):
    allowed, _ = scan_source_file(tmp_path, capsys, "lifecycle.py", 'def f():\n    raise ValueError("plan aborted; no verdict")\n')
    refused, output = scan_source_file(tmp_path, capsys, "lifecycle.py", 'def f():\n    raise ValueError("no verdicts yet; run: willitharness analyze")\n')
    assert (allowed, refused) == (0, 1), f"lifecycle.py exempts only the T29 text, got {allowed} and {refused}: {output!r}"


def test_T48_a_message_that_names_no_value_passes_with_a_note_after_the_verdict(tmp_path, capsys):
    code, output = scan_source_file(tmp_path, capsys, "plain.py", NO_VALUE_MODULE)
    assert (code, output.splitlines()) == (0, [PASS_LINE, f"note: message at {tmp_path / 'plain.py'}:2 names no value"]), f"got {code}: {output!r}"


def test_T48_a_message_that_names_a_value_prints_no_note(tmp_path, capsys):
    code, output = scan_source_file(tmp_path, capsys, "good.py", GOOD_MODULE)
    assert "note:" not in output, f"a message with a value must print no note: {output!r}"


def test_T48_a_note_never_hides_a_violation_and_follows_the_verdict(tmp_path, capsys):
    code, output = scan_source_file(tmp_path, capsys, "bad.py", FIXTURE_MODULE)
    lines = output.splitlines()
    assert code == 1 and lines[0].startswith(f"{tmp_path / 'bad.py'}:2:") and lines[-1].startswith("note:"), f"got {code}: {output!r}"


@pytest.mark.parametrize("module", [USAGE_MODULE, WARNING_MODULE])
def test_T48_usage_and_warning_lines_are_not_failure_messages(tmp_path, capsys, module):
    code, output = scan_source_file(tmp_path, capsys, "other.py", module)
    assert (code, output.splitlines()[0]) == (0, PASS_LINE), f"got {code}: {output!r}"
    assert "note:" not in output, f"an exempt line gets no note: {output!r}"


def test_T48_usage_is_exempt_only_as_a_prefix(tmp_path, capsys):
    code, output = scan_source_file(tmp_path, capsys, "other.py", 'def f():\n    raise SystemExit("bad usage: tool")\n')
    assert code == 1, f"only a message that starts with usage: is exempt, got {code}: {output!r}"


def test_T48_a_different_message_in_report_py_is_not_exempt(tmp_path, capsys):
    code, output = scan_source_file(tmp_path, capsys, "report.py", 'def f():\n    raise ValueError("no verdicts yet")\n')
    assert code == 1, f"only the exact T47 text is exempt, got {code}: {output!r}"


def test_T48_every_exemption_names_its_task_and_a_real_message():
    entries = {(entry.file_name, entry.text, entry.task) for entry in message_check.EXEMPTIONS}
    expected = {("report.py", text, "T47") for text in REPORT_REFUSALS} | {("lifecycle.py", "plan aborted; no verdict", "T29")}
    assert entries == expected, f"the table must hold exactly the T47 and T29 entries, got {entries!r}"
    texts = {message.text for message in message_check.failure_messages(SOURCE_ROOT)}
    assert set(REPORT_REFUSALS) <= texts, f"an exemption matches no message among {len(texts)} in src"


def test_T48_the_real_source_has_no_violations(capsys):
    messages = message_check.failure_messages(SOURCE_ROOT)
    assert len(messages) > 40, f"the scan found only {len(messages)} messages"
    lines = message_check.violation_lines(messages, message_check.EXEMPTIONS)
    assert lines == [], f"every failure message in src must state the rule and end with a fix: {lines[:3]}"


def test_T48_a_wrong_argument_count_exits_two(capsys):
    assert message_check.main([]) == 2, "no folder must exit 2"
    output = capsys.readouterr().out
    assert "Fix: pass src." in output, f"the usage message must end with a fix, got {output!r}"


def test_T48_the_script_run_as_main_scans_the_folder_it_is_given(tmp_path, capsys, monkeypatch):
    save_source_file(tmp_path, "good.py", GOOD_MODULE)
    monkeypatch.setattr("sys.argv", [str(SCRIPT), str(tmp_path)])
    with pytest.raises(SystemExit) as exit_request:
        runpy.run_path(str(SCRIPT), run_name="__main__")
    assert exit_request.value.code == 0, f"got {exit_request.value.code}: {capsys.readouterr().out!r}"


def test_T48_an_empty_folder_is_refused(tmp_path):
    with pytest.raises(AssertionError, match="holds no failure messages") as refusal:
        message_check.scan_exit_code(tmp_path)
    assert str(tmp_path) in str(refusal.value), f"the refusal must name the folder {tmp_path}, got {refusal.value}"


def test_T48_the_repo_checks_run_the_gate_on_src_and_pass_on_the_real_tree():
    assert repo_checks.CHECKS["failure-messages"] is repo_checks.failure_message_errors, "the gate must be registered in the repo checks"
    errors = repo_checks.failure_message_errors(SOURCE_ROOT.parent)
    assert errors == [], f"the real tree must pass the failure-messages check: {errors[:3]}"


def test_T48_the_repo_check_reports_a_bad_message_under_src(tmp_path):
    (tmp_path / "src").mkdir()
    save_source_file(tmp_path / "src", "bad.py", FIXTURE_MODULE)
    errors = repo_checks.failure_message_errors(tmp_path)
    assert len(errors) == 1 and "bad.py:2:" in errors[0], f"a bad message under src must be one error naming file and line: {errors}"


def test_T48_the_repo_check_refuses_a_tree_without_src(tmp_path):
    with pytest.raises(AssertionError, match="has no src folder") as refusal:
        repo_checks.failure_message_errors(tmp_path)
    assert str(tmp_path) in str(refusal.value), f"the refusal must name {tmp_path}, got {refusal.value}"
