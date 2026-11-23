from pathlib import Path

import guard_repro
import pilot_live
import pytest
from guard_site import messages, pkill_fixture_rule, repro_arm_rules
from hook_calls import run_script

from willitharness.counts import Counts
from willitharness.guard import check_messages
from willitharness.plan import load_plan

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "gates" / "guard_repro.sh"
PILOT_OLD_MESSAGE = "Blocked by guard (pkill): never use pkill or pgrep -f; record each PID you start and kill only those PIDs"
USABLE_MORE = "usable message completes more than no-alternative message"
OLD_MORE = "no-alternative message completes more than usable message"
SAME_DIFFERS = "difference with the same message; the measurement is invalid"
NO_DIFFERENCE = "no difference"
WORST_CASE_OF_TWELVE_RUNS = 0.48


def never_called_factory(setup, model):
    raise AssertionError(f"a dry run must not build the live runner for {model!r}. Rule: a dry run never starts claude. Fix: choose the dry runner when --dry is set.")


def dry_run(capsys, arguments):
    code = guard_repro.main([*arguments, "--dry"], never_called_factory, guard_repro.SOURCES)
    return code, capsys.readouterr().out


def test_the_script_prints_no_difference_and_exits_one_for_the_same_message_in_both_arms():
    done = run_script(["sh", str(SCRIPT), "--dry", "--same-message"], REPO_ROOT)
    assert done.returncode == 1, f"the same message in both arms must exit 1, got {done.returncode} with {done.stdout!r} {done.stderr!r}"
    assert NO_DIFFERENCE in done.stdout.splitlines(), f"the output lacks the line 'no difference': {done.stdout!r}"
    assert "GATE G5.5 PASS" not in done.stdout, f"a dry run never prints the gate pass line: {done.stdout!r}"


def test_a_dry_run_with_two_messages_shows_the_usable_message_completing_more_and_exits_zero(capsys):
    code, out = dry_run(capsys, [])
    assert code == 0, f"two messages must reproduce in the dry run, got {code} with {out!r}"
    assert "OLD: completed 0 of 10, hook blocked 10 of 10" in out and "USABLE: completed 10 of 10, hook blocked 10 of 10" in out, f"unexpected counts in {out!r}"
    assert USABLE_MORE in out and "GATE" not in out, f"unexpected verdict in {out!r}"
    assert "dry run: nothing was spent and no claude ran" in out, f"a dry run says so: {out!r}"


def test_a_dry_run_with_the_same_message_has_equal_counts_and_exits_one(capsys):
    code, out = dry_run(capsys, ["--same-message"])
    assert code == 1, f"the same message must exit 1, got {code}"
    assert "OLD: completed 10 of 10" in out and "USABLE: completed 10 of 10" in out, f"both arms must complete alike, got {out!r}"


def test_the_usable_message_is_accepted_and_the_pilot_message_is_rejected_by_the_message_check():
    usable, old = repro_arm_rules("USABLE"), repro_arm_rules("OLD")
    assert (check_messages(usable)[0], check_messages(old)[0]) == (1, 0), f"the check must accept the usable rule and reject the old one: {check_messages(usable)} {check_messages(old)}"
    assert old[0]["message"] == PILOT_OLD_MESSAGE, f"the old arm must carry the pilot message, got {old[0]['message']!r}"


def test_the_usable_arm_holds_the_pkill_rule_of_the_guard_fixtures_and_the_arms_differ_only_in_the_message():
    fixture = pkill_fixture_rule()
    (usable,), (old,) = repro_arm_rules("USABLE"), repro_arm_rules("OLD")
    assert usable == fixture, f"the usable arm must hold the pkill rule of fixtures/guard/rules.json, got {usable}"
    message_keys = ("message", "offered_alternatives")
    assert {key: old[key] for key in old if key not in message_keys} == {key: fixture[key] for key in fixture if key not in message_keys}, f"the arms differ in more than the message: {old} against {fixture}"
    assert fixture["message"] in [entry["message"] for entry in messages()], f"the usable message {fixture['message']!r} must be one the G5.2 gate accepts"


@pytest.mark.parametrize("runs", ["13", "0", "-1"])
def test_a_run_count_above_the_cap_or_below_one_is_refused_before_anything_runs(capsys, runs):
    code, out = dry_run(capsys, ["--runs", runs])
    assert code == 2 and "Rule:" in out and "Fix:" in out, f"--runs {runs} must be refused with a rule and a fix, got {code} and {out!r}"
    assert "OLD:" not in out, f"nothing may run after a refusal: {out!r}"


def test_twelve_runs_per_arm_fit_the_cap_and_thirteen_do_not():
    assert guard_repro.check_runs(12) == pytest.approx(WORST_CASE_OF_TWELVE_RUNS), "12 runs x 2 arms x $0.02 is $0.48"
    with pytest.raises(pilot_live.SpendRefused) as raised:
        guard_repro.check_runs(13)
    assert "pass --runs 12 or fewer" in str(raised.value), f"the refusal must name the largest allowed count: {raised.value}"


@pytest.mark.parametrize(
    ("usable", "old", "same_message", "line"),
    [
        (Counts(10, 10), Counts(0, 10), False, USABLE_MORE),
        (Counts(0, 10), Counts(10, 10), False, OLD_MORE),
        (Counts(5, 10), Counts(5, 10), False, NO_DIFFERENCE),
        (Counts(10, 10), Counts(0, 3), False, NO_DIFFERENCE),
        (Counts(5, 10), Counts(5, 10), True, NO_DIFFERENCE),
        (Counts(10, 10), Counts(0, 10), True, SAME_DIFFERS),
    ],
)
def test_the_verdict_line_names_the_difference_or_says_there_is_none(usable, old, same_message, line):
    assert guard_repro.repro_verdict_line(usable, old, same_message) == line, f"{usable} against {old} (same message {same_message}) must read {line!r}"


@pytest.mark.parametrize(
    ("line", "hook_proven", "cost", "same_message", "code"),
    [
        (USABLE_MORE, True, 0.4, False, 0),
        (USABLE_MORE, False, 0.4, False, 1),
        (USABLE_MORE, True, 0.51, False, 1),
        (USABLE_MORE, True, 0.5, False, 0),
        (USABLE_MORE, True, 0.4, True, 1),
        (NO_DIFFERENCE, True, 0.4, False, 1),
        (OLD_MORE, True, 0.4, False, 1),
    ],
)
def test_the_gate_passes_only_for_a_proven_hook_a_usable_message_that_completes_more_and_a_cost_within_the_cap(line, hook_proven, cost, same_message, code):
    assert guard_repro.gate_exit_code(line, hook_proven, cost, same_message) == code, f"{line!r}, hook {hook_proven}, cost {cost}, same {same_message} must exit {code}"


def test_the_plan_has_two_guard_arms_one_task_no_retries_and_a_budget_equal_to_its_worst_case():
    plan = load_plan(guard_repro.repro_plan(10))
    assert [(arm.label, arm.role) for arm in plan.arms] == [("OLD", "guard_only"), ("USABLE", "guard_only")], f"unexpected arms {plan.arms}"
    assert (plan.reps, plan.max_retries, plan.run_cap_usd) == (10, 0, 0.02), f"unexpected spend limits in {plan}"
    assert plan.budget_usd == pytest.approx(0.4), f"the budget must equal 2 arms x 10 runs x $0.02, got {plan.budget_usd}"
    assert [task.completed_check.command for task in plan.tasks] == ["ps"], f"unexpected completed check {plan.tasks}"
