import json

import pytest
import status

LOG = (
    "7 passed in 1.00s\n== analysis\nkilled   a\nmutants killed: 3/3\n== arms\nmutants killed: 2/2\n"
    "trace-check: all 49 IDs covered; pending: DI-1 (lean)\nrepo-checks: 22 checks passed\n"
    "1291 passed in 12.34s\n"
)


def test_gate_rows_come_from_the_log():
    rows = status.gate_rows(LOG)
    assert rows == [
        {"label": "Tests", "status": "passed", "result": "1291 passed"},
        {"label": "Mutants", "status": "passed", "result": "5 of 5 mutants killed"},
        {"label": "Contract IDs covered", "status": "passed", "result": "49 covered"},
        {"label": "Repository checks", "status": "passed", "result": "22 checks passed"},
    ], f"rows must sum the mutant lines and quote the others, got {rows}"
    assert [row["label"] for row in rows] == list(status.GATE_LABELS), "labels follow GATE_LABELS"


def test_a_survivor_marks_the_mutants_failed():
    rows = status.gate_rows(LOG.replace("mutants killed: 2/2", "mutants killed: 1/2"))
    assert rows[1] == {"label": "Mutants", "status": "failed", "result": "4 of 5 mutants killed"}, f"got {rows[1]}"
    assert rows[0]["status"] == "passed", "tests still pass"


def test_a_failed_test_marks_the_tests_failed():
    rows = status.gate_rows(LOG.replace("1291 passed in 12.34s", "2 failed, 1289 passed in 12.34s"))
    assert rows[0]["status"] == "failed", f"a failing test must show failed, got {rows[0]}"
    assert rows[1]["status"] == "passed", "mutants still pass"


def test_the_document_holds_command_date_and_rows():
    document = status.status_document(LOG, "2026-01-02")
    assert document["command"] == "make check" and document["date"] == "2026-01-02", f"got {document}"
    assert len(document["gates"]) == 4, f"four gates are recorded, got {document['gates']}"


@pytest.mark.parametrize("missing", ["trace-check: all 49 IDs covered", "repo-checks: 22 checks passed"])
def test_a_log_without_a_gate_line_fails_loudly(missing):
    with pytest.raises(AssertionError, match="no line matching") as raised:
        status.gate_rows(LOG.replace(missing, "nothing"))
    assert "Fix" in str(raised.value), f"the failure must say how to fix it, got {raised.value}"
    assert raised.type is AssertionError, f"expected an assertion failure, got {raised.type}"


def test_an_empty_log_fails_loudly():
    with pytest.raises(AssertionError, match="the log is empty") as raised:
        status.gate_rows("  \n")
    assert "Fix" in str(raised.value), f"the failure must say how to fix it, got {raised.value}"
    assert raised.type is AssertionError, f"expected an assertion failure, got {raised.type}"


def test_a_log_without_a_pytest_line_fails_loudly():
    with pytest.raises(AssertionError, match="no line matching") as raised:
        status.gate_rows(LOG.replace("7 passed in 1.00s\n", "").replace("1291 passed", "nothing"))
    assert "passed" in str(raised.value), f"the failure must show the pattern, got {raised.value}"
    assert raised.type is AssertionError, f"expected an assertion failure, got {raised.type}"


def test_a_log_without_mutants_fails_loudly():
    with pytest.raises(AssertionError, match="no 'mutants killed") as raised:
        status.gate_rows("trace-check: all 49 IDs covered\nrepo-checks: 22 checks passed\n1 passed\n")
    assert "make check log" in str(raised.value), f"the failure must say how to fix it, got {raised.value}"
    assert raised.type is AssertionError, f"expected an assertion failure, got {raised.type}"


def test_main_writes_the_status_file(tmp_path):
    log = tmp_path / "check.log"
    output = tmp_path / "out.json"
    log.write_text(LOG)
    code = status.main(["--log", str(log), "--output", str(output)])
    assert code == status.EXIT_WRITTEN, f"a good log must write the file, got exit {code}"
    assert json.loads(output.read_text())["gates"][0]["result"] == "1291 passed", f"got {output.read_text()}"


def test_main_refuses_a_log_that_is_not_real_output(tmp_path, capsys):
    log = tmp_path / "check.log"
    output = tmp_path / "out.json"
    log.write_text("nothing useful\n")
    code = status.main(["--log", str(log), "--output", str(output)])
    assert code == status.EXIT_UNPARSED and not output.exists(), f"a bad log must write nothing, got exit {code}"
    printed = capsys.readouterr().out
    assert "status: " in printed, f"the refusal must be printed, got {printed!r}"
