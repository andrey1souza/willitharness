import time
from functools import partial

import pytest

import mutants

SLOW_FIRST_SECONDS = 0.3
ROWS = tuple((f"mutant-{index}", "scripts/none.py", "a", "b") for index in range(6))
SURVIVING = {"mutant-1", "mutant-4"}
TESTS = ["scripts"]


class RecordingExecutor(mutants.ThreadPoolExecutor):
    sizes = []

    def __init__(self, max_workers):
        RecordingExecutor.sizes.append(max_workers)
        super().__init__(max_workers=max_workers)


def survives_when_planned(tests, mutant):
    if mutant[0] == ROWS[0][0]:
        time.sleep(SLOW_FIRST_SECONDS)
    return mutant[0] in SURVIVING


def run_rows(jobs, capsys, survives):
    RecordingExecutor.sizes = []
    killed = mutants.run_mutants(ROWS, jobs, partial(survives, TESTS), RecordingExecutor)
    return killed, capsys.readouterr().out


def printed_names(output):
    return [line.split(maxsplit=1)[1] for line in output.splitlines() if line.startswith(("killed", "SURVIVED"))]


def test_a_slow_first_mutant_does_not_reorder_the_printed_lines(capsys):
    killed, output = run_rows(4, capsys, survives_when_planned)
    assert printed_names(output) == [row[0] for row in ROWS], f"lines must follow the table order, got {output!r}"
    assert killed == len(ROWS) - len(SURVIVING), f"the killed count must follow the planned survivors, got {killed}"


def test_one_worker_and_many_workers_print_the_same_text_and_count(capsys):
    single = run_rows(1, capsys, survives_when_planned)
    many = run_rows(4, capsys, survives_when_planned)
    assert single == many, f"the result must not depend on the worker count: {single!r} and {many!r}"
    assert single[1].count("SURVIVED") == len(SURVIVING), f"every planned survivor must be reported, got {single[1]!r}"


def test_the_jobs_argument_sets_the_worker_count(capsys):
    run_rows(3, capsys, survives_when_planned)
    assert RecordingExecutor.sizes == [3], f"jobs must reach the executor, got {RecordingExecutor.sizes}"


def test_a_planted_crash_in_one_mutant_stops_the_gate(capsys):
    def crashes_on_the_third(tests, mutant):
        assert mutant[0] != ROWS[2][0], f"planted crash in {mutant[0]}"
        return False

    with pytest.raises(AssertionError) as raised:
        run_rows(4, capsys, crashes_on_the_third)
    assert "planted crash" in str(raised.value), f"the worker error must surface, got {raised.value}"


def test_a_run_where_every_mutant_dies_counts_all_of_them(capsys):
    killed, output = run_rows(4, capsys, lambda tests, mutant: False)
    assert killed == len(ROWS) and "SURVIVED" not in output, f"all must die, got {killed} and {output!r}"


def test_the_command_line_jobs_option_reaches_the_runner():
    seen = []
    code = mutants.main(["stats", "--jobs", "5"], "linux", lambda name, tests, jobs: seen.append((name, tests, jobs)) or mutants.EXIT_ALL_KILLED)
    assert seen == [("stats", None, 5)], f"--jobs must reach the runner, got {seen}"
    assert code == mutants.EXIT_ALL_KILLED, f"the runner's exit code must be the gate's, got {code}"


def test_without_the_jobs_option_the_default_worker_count_reaches_the_runner():
    seen = []
    mutants.main(["stats"], "linux", lambda name, tests, jobs: seen.append(jobs) or mutants.EXIT_ALL_KILLED)
    assert seen == [mutants.default_jobs(mutants.os.cpu_count())], f"the default must reach the runner, got {seen}"


@pytest.mark.parametrize("text", ["0", "-3", "two", ""])
def test_a_job_count_below_one_or_not_a_number_is_refused(text):
    with pytest.raises(SystemExit) as raised:
        mutants.main(["stats", "--jobs", text], "linux", lambda name, tests, jobs: mutants.EXIT_ALL_KILLED)
    assert raised.value.code == 2, f"--jobs {text!r} must be refused with exit 2, got {raised.value.code}"


def test_the_default_worker_count_follows_the_cpu_count_up_to_the_cap():
    assert mutants.default_jobs(2) == 2, "a small machine gets one worker per cpu"
    assert mutants.default_jobs(64) == mutants.MAX_DEFAULT_JOBS, "a large machine is capped"
    assert mutants.default_jobs(None) == mutants.SINGLE_JOB, "an unknown cpu count gives one worker"


def test_positive_int_accepts_whole_numbers_from_one():
    assert mutants.positive_int("1") == 1, "1 is the smallest worker count"
    assert mutants.positive_int("12") == 12, "a count above the default cap is allowed"
