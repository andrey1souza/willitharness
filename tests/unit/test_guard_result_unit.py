import dataclasses

import pytest
from guard_site import BLOCKED_COPY, bash, guard_rules, plan_of, arm_records, write_call

from willitharness.counts import Counts
from willitharness.guard_result import completed_verdict, guard_reading
from willitharness.plan import KIND_REQUIRED, Detector
from willitharness.store import RunState
from willitharness.vocabulary import Coverage, GuardResult, Verdict

ROLES = {"D": "guard_only", "B": "rule"}
BLOCKED_ONLY = (bash(BLOCKED_COPY),)


def calls_for(records, calls):
    return {record.run_id: calls for record in records if record.arm == "D"}


def reading(completed, calls, runs=20, plan=None):
    records = arm_records("D", completed[0], runs) + arm_records("B", completed[1], runs)
    return guard_reading(plan or plan_of(ROLES), records, calls_for(records, calls), guard_rules())


def test_G1_a_guard_with_a_usable_message_that_completes_as_often_matches_the_rule():
    found = reading((20, 19), BLOCKED_ONLY)
    assert found.result is GuardResult.GUARD_MATCHES_RULE, f"unexpected reading {found}"
    assert (found.completed, found.coverage, found.bypass) == (Verdict.INCONCLUSIVE, Coverage.FULL, Counts(0, 20)), f"unexpected reading {found}"


def test_G1_a_guard_that_completes_5_of_20_against_17_of_20_is_worse():
    found = reading((5, 17), BLOCKED_ONLY)
    assert found.completed is Verdict.FIRST_LOWER, f"unexpected verdict {found.completed}"
    assert found.result is GuardResult.GUARD_WORSE, f"unexpected result {found.result}"


def test_G1_a_bypass_in_any_run_makes_the_guard_worse():
    records = arm_records("D", 20, 20) + arm_records("B", 19, 20)
    calls = calls_for(records, BLOCKED_ONLY)
    calls["D/backup/1#1"] = (bash(BLOCKED_COPY), write_call("b.json"))
    found = guard_reading(plan_of(ROLES), records, calls, guard_rules())
    assert found.bypass == Counts(1, 20), f"unexpected bypass {found.bypass}"
    assert found.result is GuardResult.GUARD_WORSE, f"unexpected result {found.result}"


def test_G1_a_violating_command_the_guard_lets_pass_makes_coverage_partial_and_the_guard_worse():
    partial = reading((20, 19), (bash("pgrep -x a"),), plan=plan_of(ROLES, action="pgrep"))
    assert partial.coverage is Coverage.PARTIAL, f"pgrep -x passes the guard, got {partial.coverage}"
    assert partial.result is GuardResult.GUARD_WORSE, f"unexpected result {partial.result}"


def test_G1_a_guard_that_saw_no_violating_command_is_untested():
    found = reading((20, 19), (bash("ls"),))
    assert found.coverage is Coverage.NONE_SEEN, f"unexpected coverage {found.coverage}"
    assert found.result is GuardResult.GUARD_UNTESTED, f"unexpected result {found.result}"


def test_G1_too_few_guard_runs_is_untested():
    found = reading((4, 4), BLOCKED_ONLY, runs=4)
    assert found.completed is Verdict.INCONCLUSIVE_SMALL_N, f"unexpected verdict {found.completed}"
    assert found.result is GuardResult.GUARD_UNTESTED, f"unexpected result {found.result}"


def test_G1_a_plan_with_no_guard_arm_is_untested():
    plan = plan_of({"B": "rule", "C": "leave_one_out"})
    records = arm_records("B", 19, 20) + arm_records("C", 19, 20)
    found = guard_reading(plan, records, {}, guard_rules())
    assert found.result is GuardResult.GUARD_UNTESTED, f"unexpected result {found.result}"
    assert (found.completed, found.bypass) == (None, Counts(0, 0)), f"unexpected reading {found}"


def test_G1_a_plan_with_no_rule_arm_has_no_completed_verdict():
    plan = plan_of({"D": "guard_only", "C": "leave_one_out"})
    records = arm_records("D", 20, 20)
    verdict = completed_verdict(plan, records)
    result = guard_reading(plan, records, calls_for(records, BLOCKED_ONLY), guard_rules()).result
    assert verdict is None, f"no rule arm means no comparison, got {verdict}"
    assert result is GuardResult.GUARD_UNTESTED, f"no comparison is untested, got {result}"


def test_G1_a_plan_with_a_required_detector_has_no_violating_commands():
    plan = dataclasses.replace(plan_of(ROLES), rule=dataclasses.replace(plan_of(ROLES).rule, detector=Detector(KIND_REQUIRED, ("cp",), "first_edit")))
    found = reading((20, 19), BLOCKED_ONLY, plan=plan)
    assert found.coverage is Coverage.NONE_SEEN, f"a required action is not blocked, got {found.coverage}"
    assert found.result is GuardResult.GUARD_UNTESTED, f"unexpected result {found.result}"


def test_G1_an_unusable_guard_run_is_left_out_of_the_bypass_rate():
    records = arm_records("D", 20, 20) + arm_records("B", 19, 20)
    unusable = dataclasses.replace(records[0], state=RunState.RECORDED_UNUSABLE, usable={})
    records = (unusable, *records[1:])
    calls = calls_for(records, BLOCKED_ONLY)
    found = guard_reading(plan_of(ROLES), records, calls, guard_rules())
    assert found.bypass == Counts(0, 19), f"unexpected bypass {found.bypass}"
    assert found.result is GuardResult.GUARD_MATCHES_RULE, f"unexpected result {found.result}"


def test_G1_a_usable_guard_run_without_calls_is_refused_with_the_fix():
    records = arm_records("D", 20, 20) + arm_records("B", 19, 20)
    with pytest.raises(AssertionError) as raised:
        guard_reading(plan_of(ROLES), records, {}, guard_rules())
    message = str(raised.value)
    assert "Fix: pass the calls of every run" in message, f"unexpected message {message!r}"
    assert "D/backup/1#1" in message, f"the message must name the missing run D/backup/1#1, got {message!r}"
