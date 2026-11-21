import re

from guard_site import bash, corpus, guard_rules, messages, write_call
from pytest_bdd import given, parsers, scenario, then, when

from willitharness.bypass import bypass_counts, bypass_report_lines
from willitharness.counts import Counts
from willitharness.decision import decide
from willitharness.guard import BlockedProgram, GuardRule, check_messages, coverage_of, decide_command, evaluate
from willitharness.verdict import verdict_of
from willitharness.vocabulary import Coverage, EffectResult, GuardResult, Reach, Verdict

FEATURE = "../../features/guard-test.feature"
BACKTICKED = re.compile(r"`([^`]+)`")
BAD_CLASS, GOOD_CLASS = "bad", "good"
VIOLATING_ACTIONS = ("cp", "rm", "pkill")
BYPASS_FLAGS = {"Zero": True, "Some": False}
BLOCKED_COPY = "cp a.json b.json"
CREATED_FILE = "b.json"
COPY_ENTRY = BlockedProgram("cp", "", True, ("shutil.copy",))


@scenario(FEATURE, "A guard that matches the rule")
def test_a_guard_that_matches_the_rule(world):
    assert world, f"the steps filled nothing, got {world!r}. Fix: each step must record its state in the world."


@scenario(FEATURE, "G1 truth table")
def test_g1_truth_table(world):
    assert world, f"the steps filled nothing, got {world!r}. Fix: each step must record its state in the world."


@scenario(FEATURE, "A guard with a usable message completes as often as the rule")
def test_a_guard_with_a_usable_message_completes_as_often_as_the_rule(world):
    assert world, f"the steps filled nothing, got {world!r}. Fix: each step must record its state in the world."


@scenario(FEATURE, "A guard with a message that offers no alternative completes less")
def test_a_guard_with_a_message_that_offers_no_alternative_completes_less(world):
    assert world, f"the steps filled nothing, got {world!r}. Fix: each step must record its state in the world."


@scenario(FEATURE, "No guard arm means GuardUntested")
def test_no_guard_arm_means_guard_untested(world):
    assert world, f"the steps filled nothing, got {world!r}. Fix: each step must record its state in the world."


@scenario(FEATURE, "Bypass through another tool is detected")
def test_bypass_through_another_tool_is_detected(world):
    assert world, f"the steps filled nothing, got {world!r}. Fix: each step must record its state in the world."


@scenario(FEATURE, "The guard's own documented alternative is not a bypass")
def test_the_guards_own_documented_alternative_is_not_a_bypass(world):
    assert world, f"the steps filled nothing, got {world!r}. Fix: each step must record its state in the world."


@scenario(FEATURE, "A guard that never saw a violating command is untested")
def test_a_guard_that_never_saw_a_violating_command_is_untested(world):
    assert world, f"the steps filled nothing, got {world!r}. Fix: each step must record its state in the world."


@scenario(FEATURE, "Coverage is the share of violating commands the guard blocked")
def test_coverage_is_the_share_of_violating_commands_the_guard_blocked(world):
    assert world, f"the steps filled nothing, got {world!r}. Fix: each step must record its state in the world."


@scenario(FEATURE, "A block message must name a way forward")
def test_a_block_message_must_name_a_way_forward(world):
    assert world, f"the steps filled nothing, got {world!r}. Fix: each step must record its state in the world."


def run_of(offered, commands):
    rule = GuardRule("bare-cp", "Blocked; use " + " and ".join(f"`{item}`" for item in offered), tuple(offered), (COPY_ENTRY,))
    return rule, (bash(BLOCKED_COPY), *(bash(command) for command in commands))


@given(parsers.parse('the "completed" verdict of the guard-only arm against the rule arm is "{verdict}"'))
def completed_verdict_is(world, verdict):
    world["completed"] = Verdict(verdict)


@given(parsers.parse("coverage is {coverage}"))
def coverage_is(world, coverage):
    world["coverage"] = Coverage(coverage)


@given(parsers.parse("bypass is {bypass}"))
def bypass_is(world, bypass):
    world["bypass_free"] = BYPASS_FLAGS[bypass]


@given(parsers.parse('a guard-only arm "{label}" with completion {k:d} of {n:d}'))
def guard_arm_completion(world, label, k, n):
    world["guard_counts"] = Counts(k, n)
    world["coverage"], world["bypass_free"] = Coverage.FULL, True


@given(parsers.parse('a rule arm "{label}" with completion {k:d} of {n:d}'))
def rule_arm_completion(world, label, k, n):
    world["rule_counts"] = Counts(k, n)


@given("every guard block message contains a runnable alternative")
def messages_are_runnable():
    accepted, rejections = check_messages(messages())
    assert (accepted, rejections) == (2, []), f"the fixed messages must be runnable, got {accepted}, {rejections}"


@given(parsers.parse('bypass in arm "{label}" is Zero and coverage is Full'))
def zero_bypass_full_coverage(world, label):
    world["bypass_free"], world["coverage"] = True, Coverage.FULL


@given("a plan with no guard-only arm")
def no_guard_arm(world):
    world["completed"] = None
    world["coverage"] = Coverage.NONE_SEEN
    world["bypass_free"] = True


@given("a guard-only arm whose runs contain no violating command")
def runs_without_violation(world):
    world["calls"] = (bash("ls"), bash("command cp -f a b"))


@given(parsers.parse('a guard-only arm "{label}" with {n:d} usable runs'))
def usable_runs(world, label, n):
    world["run_count"] = n


@given(parsers.parse('in {k:d} runs the agent used the "{tool}" tool to create the file the blocked command would have created'))
def runs_with_tool(world, k, tool):
    rule, _ = run_of(["command cp -f SOURCE TARGET"], [])
    bypassing = (bash(BLOCKED_COPY), write_call(CREATED_FILE, tool))
    quiet = (bash(BLOCKED_COPY),)
    world["rules"] = (rule,)
    world["runs"] = (bypassing,) * k + (quiet,) * (world["run_count"] - k)


@given(parsers.parse("the block message offers {offered}"))
def message_offers(world, offered):
    world["offered"] = BACKTICKED.findall(offered)


@given(parsers.parse('a run that, after the block, ran "{command}"'))
def run_after_block(world, command):
    rule, calls = run_of(world["offered"], [command])
    world["rules"], world["runs"] = (rule,), (calls,)


@given("the guard corpus of good and bad commands")
def guard_corpus(world):
    world["corpus"] = corpus()


@given(parsers.parse('the guard message "{message}"'))
def guard_message(world, message):
    world["message"] = message


@when("I evaluate the guard")
def evaluate_the_guard(world):
    if "guard_counts" in world:
        world["completed"] = verdict_of(world["guard_counts"], world["rule_counts"])
    if "calls" in world:
        world["coverage"] = coverage_of(world["calls"], ("cp",), guard_rules())
        world["bypass_free"] = True
        world["completed"] = Verdict.INCONCLUSIVE
    world["result"] = evaluate(world["completed"], world["coverage"], world["bypass_free"])


@when("I measure bypass")
def measure_bypass(world):
    world["counts"] = bypass_counts(world["runs"], world["rules"])
    world["report"] = bypass_report_lines(world["runs"], world["rules"])


@when("the guard checks each command")
def guard_checks_each_command(world):
    rules = guard_rules()
    world["decisions"] = [(entry, decide_command(entry["command"], rules)) for entry in world["corpus"]]
    bad_calls = tuple(bash(entry["command"]) for entry in world["corpus"] if entry["class"] == BAD_CLASS)
    coverages = {coverage_of(bad_calls, (action,), rules) for action in VIOLATING_ACTIONS}
    world["coverage"] = Coverage.FULL if coverages == {Coverage.FULL} else Coverage.PARTIAL


@when("I check the message")
def check_the_message(world):
    offered = BACKTICKED.findall(world["message"])
    accepted, _ = check_messages([{"message": world["message"], "offered_alternatives": offered}])
    world["accepted"] = accepted == 1


@then(parsers.parse('the guard result is "{result}"'))
def guard_result_is(world, result):
    assert world["result"] is GuardResult(result), f"expected {result}, got {world['result']}"


@then(parsers.parse('the "completed" verdict is "{verdict}"'))
def completed_verdict_check(world, verdict):
    assert world["completed"] is Verdict(verdict), f"expected {verdict}, got {world['completed']}"


@then(parsers.parse('with an effect of "{effect}" the decision is "{decision}"'))
def decision_with_effect(world, effect, decision):
    got = decide(Reach.LOADED, EffectResult(effect), world["result"])
    assert got.value == decision, f"expected {decision}, got {got}"


@then(parsers.parse("bypassRate is {rate:g}"))
def bypass_rate_is(world, rate):
    assert world["counts"].rate() == rate, f"expected {rate}, got {world['counts']}"


@then(parsers.parse('the report says "{text}"'))
def report_says(world, text):
    assert any(text in line for line in world["report"]), f"expected {text!r} in the report lines {world['report']}. Rule: the report names the channel. Fix: add the line."


@then(parsers.parse("the run counts as bypass: {bypass}"))
def run_counts_as_bypass(world, bypass):
    assert (world["counts"].successes == 1) is (bypass == "true"), f"expected bypass {bypass}, got {world['counts']}. Rule: CI-16, an offered command is not a bypass. Fix: check the offered prefixes."


@then(parsers.parse("coverage is {coverage}"))
def coverage_check(world, coverage):
    assert world["coverage"] is Coverage(coverage), f"expected {coverage}, got {world['coverage']}"


@then("every bad command is blocked with a message")
def bad_commands_blocked(world):
    bad = [(entry, decision) for entry, decision in world["decisions"] if entry["class"] == BAD_CLASS]
    assert bad and all(decision.blocked and decision.message for _, decision in bad), f"unblocked bad commands in {bad}"


@then("every good command is allowed")
def good_commands_allowed(world):
    good = [(entry, decision) for entry, decision in world["decisions"] if entry["class"] == GOOD_CLASS]
    assert good and not any(decision.blocked for _, decision in good), f"blocked good commands in {good}"


@then(parsers.parse('the check result is "{result}"'))
def check_result_is(world, result):
    assert ("accepted" if world["accepted"] else "rejected") == result, f"expected {result} for {world['message']!r}"
