import math
import re
from dataclasses import replace

from cli_runner import run_cli
from lifecycle_site import TASK_NAME, SiteSpec, costing_runner, edit_world, make_site, ready_site, reach_every_arm, run_setup, validate_site, with_budget
from pytest_bdd import given, parsers, scenario, then, when

from willitharness import cli
from willitharness.lifecycle import Job, LifecycleRefused, PlanState, abort_plan, begin_run, lifecycle_dir, move_to, read_reach, read_resume, read_state, record_reachability, refresh_state, execute_plan, resume_if_stopped, start_running
from willitharness.plan import plan_fingerprint
from willitharness.world import world_changed
from willitharness.store import Cell, Record, RunState, append_record, latest_by_run, load_records, spent
from willitharness.vocabulary import Reach

BUDGET_FEATURE = "../../features/budget-and-resume.feature"
WORLD_FEATURE = "../../features/world-validation.feature"
STOPPING_BUDGET = 0.05
STOPPING_REPS = 100
RAISED_BUDGET = 0.10
RUN_ARGUMENTS = ["plan.json", "--agent", "fake"]
ROOMY_BUDGET = 1.0
DEFAULT_COST = 0.01
DEFAULT_RUN_CAP = 0.02
PATH_TO_STATE = {
    "Analyzed": (PlanState.COMPLETE, PlanState.ANALYZED),
}


@scenario(BUDGET_FEATURE, "No run starts before the plan is Running")
def test_no_run_starts_before_the_plan_is_running(world):
    assert world["refused"] and world["records"] == (), f"the start must be refused and leave no record, got {world}. Rule: L1. Fix: refuse a start unless the plan is Running."


@scenario(BUDGET_FEATURE, "Reachability must be recorded for every arm of the plan")
def test_reachability_must_be_recorded_for_every_arm_of_the_plan(world):
    assert world["exit_code"] == 1 and "arm D" in world["message"], f"the run must fail naming arm D, got {world['exit_code']} and {world['message']!r}. Rule: L1. Fix: name the missing arm."


@scenario(BUDGET_FEATURE, "A reachability result of Unknown still counts as recorded")
def test_a_reachability_result_of_unknown_still_counts_as_recorded(world):
    assert "Running" in world["states_seen"], f"the plan must be Running while it runs, saw {world['states_seen']}. Rule: L1. Fix: count Unknown as recorded."


@scenario(BUDGET_FEATURE, "The budget stops the plan")
def test_the_budget_stops_the_plan(world):
    assert world["exit_code"] == 4 and len(world["runs"]) == 4, f"4 runs and exit 4 expected, got {world['exit_code']} and {len(world['runs'])}. Rule: L2. Fix: reserve before each start."


@scenario(BUDGET_FEATURE, "A running plan that is never aborted finishes")
def test_a_running_plan_that_is_never_aborted_finishes(world):
    assert world["final"] in (PlanState.COMPLETE, PlanState.BUDGET_STOPPED), f"got {world['final']}. Rule: T2. Fix: end a Running plan in Complete or BudgetStopped."


@scenario(BUDGET_FEATURE, "A running plan that may be aborted ends in one of three states")
def test_a_running_plan_that_may_be_aborted_ends_in_one_of_three_states(world):
    assert world["final"] in (PlanState.COMPLETE, PlanState.BUDGET_STOPPED, PlanState.ABORTED), f"got {world['final']}. Rule: T2a. Fix: end in one of the three states."
    assert world["final"] is PlanState.ABORTED, f"the abort arrived during the run, so the plan must end Aborted, got {world['final']}"


@scenario(BUDGET_FEATURE, "An analyzed plan cannot be aborted")
def test_an_analyzed_plan_cannot_be_aborted(world):
    assert world["exit_code"] == 1 and world["state"] == "Analyzed", f"abort must fail and keep Analyzed, got {world['exit_code']} and {world['state']}. Rule: abort is possible only before Analyzed."


@scenario(BUDGET_FEATURE, "Abort records every in-flight run as unusable and charges RUN_CAP for it")
def test_abort_records_every_in_flight_run_as_unusable_and_charges_run_cap_for_it(world):
    assert math.isclose(spent(world["runs"]), 0.16), f"spend must be 0.16, got {spent(world['runs'])}. Rule: L2. Fix: charge RUN_CAP per in-flight run."


@scenario(BUDGET_FEATURE, "An aborted plan gets no verdict")
def test_an_aborted_plan_gets_no_verdict(world):
    assert world["exit_code"] == 1 and "no verdict" in world["message"], f"got {world['exit_code']} and {world['message']!r}. Rule: L5. Fix: refuse analyze on Aborted."


@scenario(BUDGET_FEATURE, "No verdict before the plan is Complete or BudgetStopped")
def test_no_verdict_before_the_plan_is_complete_or_budget_stopped(world):
    assert world["exit_code"] == 1 and "still running" in world["message"], f"got {world['exit_code']} and {world['message']!r}. Rule: L5. Fix: refuse analyze while Running."


@scenario(BUDGET_FEATURE, "A BudgetStopped plan resumes with a higher budget")
def test_L10_a_budget_stopped_plan_resumes_with_a_higher_budget(world):
    assert world["resumed"] is PlanState.RUNNING, f"the resume must end Running, got {world['resumed']}. Rule: L10. Fix: resume a BudgetStopped plan with a higher budget."
    assert world["reach_after"] == world["reach_before"] and world["reach_before"], f"reachability must be kept, got {world['reach_before']} then {world['reach_after']}"


@scenario(BUDGET_FEATURE, "A Complete plan cannot resume")
def test_L10_a_complete_plan_cannot_resume(world):
    assert world["exit_code"] == 1 and "nothing to resume" in world["message"], f"got {world['exit_code']} and {world['message']!r}. Rule: L10. Fix: refuse a resume from Complete."


@scenario(BUDGET_FEATURE, "A BudgetStopped plan with a changed world cannot resume")
def test_L10_a_budget_stopped_plan_with_a_changed_world_cannot_resume(world):
    assert world["exit_code"] == 1 and world_changed(world["site"].root, world["site"].world_dir), f"the resume must fail on a changed world, got {world['exit_code']}. Rule: L10. Fix: check the world hash."


@scenario(BUDGET_FEATURE, "A plan that differs from the stored plan in more than the budget cannot resume")
def test_L10_a_plan_that_differs_from_the_stored_plan_in_more_than_the_budget_cannot_resume(world):
    assert world["exit_code"] == 1 and "A-FP" in world["message"], f"got {world['exit_code']} and {world['message']!r}. Rule: A-FP. Fix: compare the fingerprint."


@scenario(BUDGET_FEATURE, "An analyzed plan cannot resume")
def test_L10_an_analyzed_plan_cannot_resume(world):
    assert world["exit_code"] == 1 and "plan is Analyzed" in world["message"], f"got {world['exit_code']} and {world['message']!r}. Rule: L10. Fix: refuse a resume after analyze."


@scenario(BUDGET_FEATURE, "A resume with a budget that is not higher is refused")
def test_L11_a_resume_with_a_budget_that_is_not_higher_is_refused(world):
    assert world["exit_code"] == 1 and "L11" in world["message"], f"got {world['exit_code']} and {world['message']!r}. Rule: L11. Fix: require a strictly higher budget."


@scenario(BUDGET_FEATURE, "A resumed plan is not marked as ended")
def test_L12_a_resumed_plan_is_not_marked_as_ended(world):
    assert read_resume(folder_in(world)).ended_by == "none", f"a Running plan is marked as ended: {read_resume(folder_in(world))}. Rule: L12. Fix: reset the ended marker on resume."
    assert world["resumed"] is PlanState.RUNNING, f"got {world['resumed']}"


@scenario(WORLD_FEATURE, "Runs do not start after a world change until the world is validated again")
def test_runs_do_not_start_after_a_world_change_until_the_world_is_validated_again(world):
    assert world["exit_code"] == 1 and world["runs"] == (), f"the run must fail and start nothing, got {world['exit_code']} and {world['runs']}. Rule: W3. Fix: block starts on a changed world."


@scenario(WORLD_FEATURE, "Runs refuse to start on an unvalidated world")
def test_runs_refuse_to_start_on_an_unvalidated_world(world):
    assert world["exit_code"] == 1 and world["runs"] == (), f"the run must fail and start nothing, got {world['exit_code']} and {world['runs']}. Rule: L1. Fix: refuse unvalidated worlds."


def folder_in(world):
    return lifecycle_dir(world["site"].root, world["site"].plan)


def spec_in(world, arm_count, budget, reps):
    return SiteSpec(arm_count=arm_count, budget_usd=budget, run_cap_usd=world.get("cap", DEFAULT_RUN_CAP), reps=reps, max_retries=0)


def observing_runner(world):
    cost_runner = costing_runner(world.get("cost", DEFAULT_COST))

    def runner(cell, rep, attempt):
        world.setdefault("states_seen", set()).add(read_state(folder_in(world)).value)
        if world.get("abort_arrives") and not world.get("aborted"):
            world["aborted"] = True
            abort_plan(world["site"].root, world["site"].plan)
        return cost_runner(cell, rep, attempt)

    return runner


def scenario_final_runs(world):
    return tuple(latest_by_run(load_records(folder_in(world))).values())


def lifecycle_stored_run(index, state, cost):
    return Record(f"A/{TASK_NAME}/{index}#{index}", "A", TASK_NAME, index, index, state, {"completed": True}, cost)


@given(parsers.parse("a plan with a fake agent that costs {cost:f} per run"))
def plan_with_fake_agent(world, cost):
    world["cost"] = cost
    world["states_seen"] = set()


@given(parsers.parse("RUN_CAP is {cap:f}"))
def run_cap_is(world, cap):
    world["cap"] = cap


@given(parsers.re(r'the plan state is "(?P<state>[A-Za-z]+)"'))
def plan_state_is_given(world, tmp_path, state):
    if state == "WorldValidated":
        world["site"] = make_site(tmp_path, spec_in(world, 2, ROOMY_BUDGET, 2))
        validate_site(world["site"])
        assert refresh_state(world["site"]).value == state, "the plan must reach WorldValidated"
        return
    world["site"] = ready_site(tmp_path, spec_in(world, 2, ROOMY_BUDGET, 2))
    start_running(world["site"])
    if state == "Aborted":
        abort_plan(world["site"].root, world["site"].plan)
    for step in PATH_TO_STATE.get(state, ()):
        move_to(folder_in(world), step)
    assert read_state(folder_in(world)).value == state, f"the plan must be {state}, got {read_state(folder_in(world))}"


@given(parsers.parse('a plan in the state "{state}" with a fair fake agent and no abort'))
def running_plan_with_fair_agent(world, tmp_path, state):
    world["site"] = ready_site(tmp_path, spec_in(world, 2, ROOMY_BUDGET, 2))
    start_running(world["site"])
    assert read_state(folder_in(world)).value == state, f"the plan must be {state}"


@given(parsers.parse('a plan in the state "{state}" with a fair fake agent'))
def running_plan_with_fair_agent_that_may_abort(world, tmp_path, state):
    world["site"] = ready_site(tmp_path, spec_in(world, 2, ROOMY_BUDGET, 40))
    start_running(world["site"])
    assert read_state(folder_in(world)).value == state, f"the plan must be {state}"


@given("an abort may arrive at any step")
def abort_may_arrive(world):
    world["abort_arrives"] = True


@given("the world is validated")
def world_is_validated(world, tmp_path):
    world["site"] = make_site(tmp_path, spec_in(world, 4, ROOMY_BUDGET, 1))
    validate_site(world["site"])


@given(parsers.parse("reachability is recorded for {recorded:d} of {total:d} arms"))
def reachability_for_some_arms(world, recorded, total):
    arms = world["site"].plan.arms
    assert len(arms) == total, f"the plan holds {len(arms)} arms, the scenario says {total}"
    for arm in arms[:recorded]:
        record_reachability(world["site"], arm.label, Reach.LOADED)


@given(parsers.parse('reachability is recorded as "{reach}" for every arm'))
def reachability_for_every_arm(world, reach):
    reach_every_arm(world["site"], Reach(reach))


@given(parsers.parse("a budget of {budget:f} and {runs:d} planned runs"))
def budget_and_planned_runs(world, tmp_path, budget, runs):
    world["site"] = ready_site(tmp_path, spec_in(world, 1, budget, runs))


@given(parsers.parse("{count:d} runs are in flight and the recorded spend is {amount:f}"))
def runs_in_flight_with_spend(world, tmp_path, count, amount):
    world["site"] = ready_site(tmp_path, spec_in(world, 1, ROOMY_BUDGET, 10))
    start_running(world["site"])
    append_record(folder_in(world), lifecycle_stored_run(1, RunState.RECORDED_USABLE, amount))
    for index in range(2, count + 2):
        append_record(folder_in(world), lifecycle_stored_run(index, RunState.STARTED, 0.0))


@given("a plan whose world hash changed after validation")
def world_changed_after_validation(world, tmp_path):
    world["site"] = ready_site(tmp_path, spec_in(world, 2, ROOMY_BUDGET, 2))
    edit_world(world["site"])


@given("a plan whose world was never checked")
def world_never_checked(world, tmp_path):
    world["site"] = make_site(tmp_path, spec_in(world, 2, ROOMY_BUDGET, 2))


@when("I try to start a run")
def try_to_start_a_run(world):
    try:
        begin_run(folder_in(world), Job(Cell("A", TASK_NAME), 1, 1))
        world["refused"] = False
    except LifecycleRefused:
        world["refused"] = True
    world["records"] = load_records(folder_in(world))


@when("I run the plan")
def run_the_plan(world, monkeypatch, capsys):
    monkeypatch.chdir(world["site"].root)
    world["exit_code"] = cli.run_plan_command(RUN_ARGUMENTS, {"fake": observing_runner(world)}, {})
    world["message"] = capsys.readouterr().err
    world["runs"] = scenario_final_runs(world)


@when("I run the plan to the end")
def run_the_plan_to_the_end(world):
    world["final"] = execute_plan(run_setup(world["site"]), observing_runner(world))


@when("I abort the plan")
def abort_the_plan(world, monkeypatch, capsys):
    monkeypatch.chdir(world["site"].root)
    world["exit_code"], _, world["message"] = run_cli(capsys, ["abort", "plan.json"])
    world["state"] = read_state(folder_in(world)).value
    world["runs"] = scenario_final_runs(world)


@when("I run analyze")
def run_analyze(world, monkeypatch, capsys):
    monkeypatch.chdir(world["site"].root)
    world["exit_code"], _, world["message"] = run_cli(capsys, ["analyze", "plan.json"])


@then("the start is refused")
def the_start_is_refused(world):
    assert world["refused"], "a start before Running must be refused. Rule: L1. Fix: check the state before a start."


@then("no run record exists")
def no_run_record_exists(world):
    assert world["records"] == (), f"no record may exist, got {world['records']}"


@then("the message names the arm with no reachability result")
def message_names_the_arm(world):
    assert "arm D" in world["message"], f"the message must name arm D, got {world['message']!r}"


@then(parsers.parse('the plan state becomes "{state}"'))
def plan_state_becomes(world, state):
    assert state in world["states_seen"], f"the plan never became {state}, saw {world['states_seen']}"


@then(parsers.parse("exactly {count:d} runs start, because a run starts only while spent plus reserved plus {cap:f} is at most {budget:f}"))
def exactly_runs_start(world, count, cap, budget):
    assert len(world["runs"]) == count, f"expected {count} runs, got {len(world['runs'])}. Rule: L2, a start needs spent plus reserved plus RUN_CAP within {budget}. Fix: reserve before each start."


@then(parsers.parse("the recorded spend is {amount:f}"))
def recorded_spend_is(world, amount):
    assert math.isclose(spent(world["runs"]), amount), f"expected spend {amount}, got {spent(world['runs'])}"


@then(parsers.re(r'the plan state is "(?P<state>[A-Za-z]+)"'))
def plan_state_is_then(world, state):
    assert read_state(folder_in(world)).value == state, f"expected {state}, got {read_state(folder_in(world))}"


@then(parsers.re(r"the plan state is (?P<states>\"[A-Za-z]+\"(?:, \"[A-Za-z]+\")* or \"[A-Za-z]+\")"))
def plan_state_is_one_of(world, states):
    allowed = re.findall(r'"([A-Za-z]+)"', states)
    assert world["final"].value in allowed, f"expected one of {allowed}, got {world['final']}"


@then(parsers.parse("the exit code is {code:d}"))
def exit_code_is(world, code):
    assert world["exit_code"] == code, f"expected exit code {code}, got {world['exit_code']}"


@then(parsers.parse('the {count:d} runs are recorded as "{state}"'))
def runs_recorded_as(world, count, state):
    flown = [run for run in world["runs"] if math.isclose(run.cost_usd, DEFAULT_RUN_CAP)]
    assert [run.state.value for run in flown] == [state] * count, f"expected {count} runs as {state}, got {flown}"


@then(parsers.parse("the spend is {amount:f}, because RUN_CAP {cap:f} is charged for each"))
def spend_is(world, amount, cap):
    assert math.isclose(spent(world["runs"]), amount), f"expected spend {amount}, got {spent(world['runs'])}"


@then("no new run is started")
def no_new_run_is_started(world):
    assert world["runs"] == (), f"no run may start, got {world['runs']}"


@then("no run is started")
def no_run_is_started(world):
    assert world["runs"] == (), f"no run may start, got {world['runs']}"


def stopped_world(world, tmp_path):
    world["site"] = ready_site(tmp_path, spec_in(world, 1, STOPPING_BUDGET, STOPPING_REPS))
    outcome = execute_plan(run_setup(world["site"]), observing_runner(world))
    assert outcome is PlanState.BUDGET_STOPPED, f"the plan must stop at the budget, got {outcome}"
    world["reach_before"] = read_reach(folder_in(world))


def resume_with(world, budget):
    site = with_budget(world["site"], budget)
    try:
        resume_if_stopped(site)
        world["resumed"] = start_running(site)
        world["exit_code"] = 0
        world["message"] = ""
    except LifecycleRefused as refusal:
        world["resumed"] = None
        world["exit_code"] = cli.EXIT_DOMAIN_FAILURE
        world["message"] = str(refusal)
    world["reach_after"] = read_reach(folder_in(world))


@given(parsers.parse('the plan state is "BudgetStopped" with a budget of {budget:f}'))
def budget_stopped_with_budget(world, tmp_path, budget):
    assert math.isclose(budget, STOPPING_BUDGET), f"the scenario budget {budget} must stop the plan, expected {STOPPING_BUDGET}"
    stopped_world(world, tmp_path)


@given('the plan state is "BudgetStopped"')
def budget_stopped(world, tmp_path):
    stopped_world(world, tmp_path)
    assert read_state(folder_in(world)) is PlanState.BUDGET_STOPPED, f"got {read_state(folder_in(world))}"


@given('the plan state is "Complete"')
def complete_plan(world, tmp_path):
    world["site"] = ready_site(tmp_path, spec_in(world, 1, ROOMY_BUDGET, 2))
    execute_plan(run_setup(world["site"]), observing_runner(world))
    assert read_state(folder_in(world)) is PlanState.COMPLETE, f"got {read_state(folder_in(world))}"


@given('the plan state is "BudgetStopped" and the plan is marked as ended by the budget')
def budget_stopped_and_ended(world, tmp_path):
    stopped_world(world, tmp_path)
    assert read_resume(folder_in(world)).ended_by == "BudgetStopped", f"got {read_resume(folder_in(world))}"


@given("the world hash is unchanged since validation")
def world_hash_unchanged(world):
    assert not world_changed(world["site"].root, world["site"].world_dir), f"the world {world['site'].world_dir} changed since validation"


@given("the plan is identical except for budget_usd")
def plan_identical_except_budget(world):
    assert plan_fingerprint(with_budget(world["site"], RAISED_BUDGET).plan) == read_resume(folder_in(world)).fingerprint, f"the plan {world['site'].plan.name} differs from the stored fingerprint {read_resume(folder_in(world)).fingerprint}"


@given("the world hash changed since validation")
def world_hash_changed(world):
    edit_world(world["site"])
    assert world_changed(world["site"].root, world["site"].world_dir), f"the edit of {world['site'].world_dir} left the world hash unchanged"


@given("the plan fingerprint differs from the stored fingerprint")
def fingerprint_differs(world):
    world["site"] = replace(world["site"], plan=replace(world["site"].plan, reps=world["site"].plan.reps + 1))
    assert plan_fingerprint(world["site"].plan) != read_resume(folder_in(world)).fingerprint, f"reps {world['site'].plan.reps} left the plan matching the stored fingerprint {read_resume(folder_in(world)).fingerprint}"


@given("a BudgetStopped plan that I analyzed")
def analyzed_budget_stopped_plan(world, tmp_path):
    stopped_world(world, tmp_path)
    move_to(folder_in(world), PlanState.ANALYZED)
    assert read_state(folder_in(world)) is PlanState.ANALYZED, f"got {read_state(folder_in(world))}"


@when(parsers.parse("I resume the plan with a budget of {budget:f}"))
def resume_with_budget(world, budget):
    resume_with(world, budget)


@when("I resume the plan with a higher budget")
def resume_with_higher_budget(world):
    resume_with(world, RAISED_BUDGET)


@then("the reachability results are kept")
def reachability_kept(world):
    assert world["reach_after"] == world["reach_before"], f"reachability changed from {world['reach_before']} to {world['reach_after']}"
    assert world["reach_after"], "the plan must hold reachability results"


@then(parsers.re(r"the plan is (?:no longer|not) marked as ended"))
def plan_not_marked_as_ended(world):
    assert read_resume(folder_in(world)).ended_by == "none", f"the plan is marked as ended: {read_resume(folder_in(world))}"
    assert read_state(folder_in(world)) is PlanState.RUNNING, f"got {read_state(folder_in(world))}"


@then("the message says the world must be validated again")
def message_says_validate_again(world):
    assert "must be validated again" in world["message"], f"got {world['message']!r}"


@then(parsers.parse("the budget stays {budget:f}"))
def budget_stays(world, budget):
    assert math.isclose(read_resume(folder_in(world)).budget_usd, budget), f"the stored budget is {read_resume(folder_in(world)).budget_usd}, expected {budget}"
