import shutil
from pathlib import Path
from typing import NamedTuple

from pytest_bdd import given, parsers, scenarios, then, when

from willitharness import claude_agent, cli, fakeagent
from willitharness.analysis import PlanFacts, analyze_effect
from willitharness.arms import remove_section
from willitharness.decision import decide
from willitharness.fakeagent import Behavior, Location
from willitharness.plan import MIN_PROBE_RUNS
from willitharness.probe import PROMPT_TEMPLATE, ProbeRun, loo_arm_valid, parse_run, probe
from willitharness.vocabulary import EffectResult, GuardResult, NoiseStatus, Reach, Verdict

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "probe"
SEED = 11
NON_TARGET_LABEL = "Reference code"
LOO_SECTION = "Working here as an agent"
LOO_LABEL = "C"

scenarios("../../features/reachability.feature")


def usable_run(target_hit=True, control_hit=False):
    return ProbeRun(usable=True, target_hit=target_hit, control_hit=control_hit)


class Script(NamedTuple):
    label: str
    hits: int
    total: int


def probe_in(world, location, script):
    runs = []
    for index in range(script.total):
        recall = 1.0 if index < script.hits else 0.0
        transcript = fakeagent.run_agent(Behavior(SEED, recall), location, script.label, index)
        runs.append(parse_run(transcript, world["target"], world["control"]))
    world["result"] = probe(runs)
    world["message"] = world["result"].message


@given(parsers.parse("MIN_PROBE_RUNS is {value:d}"))
def min_probe_runs_is(value):
    assert MIN_PROBE_RUNS == value, f"MIN_PROBE_RUNS is {MIN_PROBE_RUNS}, the feature says {value}"


@given(parsers.parse('a target token "{token}" planted in the rule file of the rule arm'))
def target_token(world, token):
    world["target"] = token


@given(parsers.parse('a control token "{token}" planted nowhere'))
def control_token(world, token):
    world["control"] = token


@given(parsers.parse("a probe with {usable:d} usable runs on the rule arm"))
def probe_with_usable_runs(world, usable):
    world["runs"] = [usable_run() for _ in range(usable)]


@given(parsers.parse("a probe with {total:d} runs where {unusable:d} run is unusable"))
def probe_with_unusable_run(world, total, unusable):
    good = [usable_run() for _ in range(total - unusable)]
    world["runs"] = good + [ProbeRun(usable=False, target_hit=False, control_hit=False) for _ in range(unusable)]


@given(parsers.parse("a probe where the control token appears in {hits:d} of {total:d} runs"))
def probe_with_control_hits(world, hits, total):
    world["runs"] = [usable_run(target_hit=False, control_hit=index < hits) for index in range(total)]


@given(parsers.parse("the target token appears in {hits:d} of {total:d} runs"))
def target_hits_in_runs(world, hits, total):
    assert len(world["runs"]) == total, f"the scenario says {total} runs, the world holds {len(world['runs'])}"
    world["runs"] = [usable_run(index < hits, run.control_hit) for index, run in enumerate(world["runs"])]


@when("I classify the probe")
def classify_the_probe(world):
    world["result"] = probe(world["runs"])
    world["message"] = world["result"].message


@when(parsers.parse("I run the probe command with {runs:d} runs"))
def run_the_probe_command(world, runs, tmp_path, capsys):
    shutil.copytree(FIXTURES / "agents-only", tmp_path / "work")
    code = cli.main([
        "probe", "--agent", "fake", "--directory", str(tmp_path / "work"), "--boundary", str(tmp_path / "work"),
        "--runs", str(runs), "--seed", str(SEED), "--target-token", world["target"], "--control-token", world["control"],
    ])
    world["exit_code"] = code
    world["message"] = capsys.readouterr().err


@then(parsers.parse('reachability is "{name}"'))
def reachability_is(world, name):
    assert world["result"].reach == Reach(name), f"expected {name}, got {world['result']}"


@given(parsers.parse("a fake agent that reports the target token in {hits:d} of {total:d} runs"))
def fake_agent_reporting(world, hits, total, tmp_path):
    shutil.copytree(FIXTURES / "agents-only", tmp_path / "work")
    world["location"] = Location(tmp_path / "work", tmp_path / "work")
    world["hits"], world["total"] = hits, total


@when("I run the probe")
def run_the_probe(world):
    probe_in(world, world["location"], Script(fakeagent.DEFAULT_LABEL, world["hits"], world["total"]))


@given(parsers.parse('a fixture "{name}" with a CLAUDE.md in the parent directory and an AGENTS.md in the child directory'))
def ancestor_fixture(world, name, tmp_path):
    shutil.copytree(FIXTURES / name, tmp_path / name)
    root = tmp_path / name
    assert (root / "CLAUDE.md").is_file() and (root / "child" / "AGENTS.md").is_file(), f"fixture {name} is incomplete"
    world["location"] = Location(root / "child", root)


@when("I run the probe in the child directory with the fake agent that follows the fallback rule")
def run_in_child_directory(world):
    probe_in(world, world["location"], Script(fakeagent.DEFAULT_LABEL, MIN_PROBE_RUNS, MIN_PROBE_RUNS))


@given(parsers.parse('the LOO arm built by removing the section "{section}"'))
def loo_arm_built(world, section, tmp_path):
    assert section == LOO_SECTION, f"the fixture holds the section {LOO_SECTION!r}, the feature names {section!r}"
    source = (FIXTURES / "loo-source" / "AGENTS.md").read_text()
    arm = tmp_path / "loo-arm"
    arm.mkdir()
    (arm / "AGENTS.md").write_text(remove_section(source, section))
    world["location"] = Location(arm, arm)


@given("a non-target token planted in another section of the harness")
def non_target_token(world):
    text = (world["location"].directory / "AGENTS.md").read_text()
    assert NON_TARGET_LABEL + ":" in text, f"the LOO arm lost its other section: {text!r}"
    world["target"] = text.split(NON_TARGET_LABEL + ":")[1].split()[0]


@when("I probe the LOO arm for the non-target token")
def probe_the_loo_arm(world):
    probe_in(world, world["location"], Script(NON_TARGET_LABEL, MIN_PROBE_RUNS, MIN_PROBE_RUNS))


@then(parsers.parse('the non-target token is "{name}"'))
def non_target_is(world, name):
    assert world["result"].reach == Reach(name), f"expected {name}, got {world['result']}"


@then("the LOO arm is valid")
def loo_arm_is_valid(world):
    assert loo_arm_valid(world["result"].reach), f"the LOO arm probe gave {world['result']}"


@given(parsers.parse('the LOO arm probe result for the non-target token is "{name}"'))
def loo_probe_result(world, name):
    world["loo_probe"] = Reach(name)


@given(parsers.parse('the rule arm has reachability "{name}"'))
def rule_arm_reachability(world, name):
    world["rule_reach"] = Reach(name)


@when("I analyze the plan")
def analyze_the_plan(world):
    rule_reach = world.get("rule_reach", Reach.LOADED)
    loo_probe = world.get("loo_probe", Reach.LOADED)
    facts = PlanFacts(True, NoiseStatus.NOISE_OK, loo_probe, rule_reach)
    analysis = analyze_effect(facts, Verdict.FIRST_HIGHER, LOO_LABEL)
    world["analysis"] = analysis
    world["message"] = analysis.message or ""
    world["decision"] = decide(rule_reach, analysis.effect, GuardResult.GUARD_UNTESTED)
    world["loo_probe"] = loo_probe


@then("the LOO arm is invalid")
def loo_arm_is_invalid(world):
    assert not loo_arm_valid(world["loo_probe"]), f"the LOO arm probe {world['loo_probe']} must be invalid"


@then(parsers.parse('the effect result is "{name}"'))
def effect_result_is(world, name):
    assert world["analysis"].effect == EffectResult(name), f"expected {name}, got {world['analysis']}"


@then("no effect verdict is emitted")
def no_effect_verdict(world):
    assert world["analysis"].verdict is None, f"expected no verdict, got {world['analysis']}"


@then(parsers.parse('the decision is "{name}"'))
def decision_is(world, name):
    assert world["decision"].value == name, f"expected {name}, got {world['decision']}"


@given(parsers.parse('a fixture "{name}" with an AGENTS.md and no CLAUDE.md in any parent directory'))
def agents_only_fixture(world, name, tmp_path):
    shutil.copytree(FIXTURES / name, tmp_path / name)
    root = tmp_path / name
    parents = [folder for folder in [root, *root.parents] if (folder / "CLAUDE.md").exists()]
    assert not parents, f"the fixture must have no CLAUDE.md in any parent directory, found one in {parents}"
    world["location"] = Location(root, root)


@when("I run the probe in that directory with the real agent")
def run_the_probe_with_the_real_agent(world):
    prompt = PROMPT_TEMPLATE.format(label=fakeagent.DEFAULT_LABEL)
    runs = []
    for _ in range(MIN_PROBE_RUNS):
        lines = claude_agent.ask_claude(world["location"].directory, prompt, claude_agent.DEFAULT_MODEL, claude_agent.DEFAULT_RUN_BUDGET_USD)
        runs.append(parse_run(lines, world["target"], world["control"]))
    world["result"] = probe(runs)
    world["message"] = world["result"].message
