from analysis_site import LOO_LABEL, REPEAT_LABEL, RULE_LABEL, TARGET, TASK, CellShape, analyze_site, filled_cells, site_with_state
from pytest_bdd import given, parsers, scenarios, then, when

from willitharness.decision import decide
from willitharness.lifecycle import PlanState
from willitharness.store import Cell
from willitharness.vocabulary import GuardResult, Reach

scenarios("../../../features/warnings.feature")

SATURATED_AND_DENIED = {
    Cell(LOO_LABEL, TASK): CellShape(20, 0),
    Cell(REPEAT_LABEL, TASK): CellShape(20, 0),
    Cell(RULE_LABEL, TASK): CellShape(12, 0, denied=12),
}


@given(parsers.parse('arm "{arm}" has {n:d} usable runs in task "{task}" for "{outcome}"'))
def arm_with_usable_runs(world, arm, n, task, outcome):
    assert (task, outcome) == (TASK, TARGET), f"the support site names {TASK} and {TARGET}"
    world["cells"][Cell(arm, task)] = CellShape(n, 0)


@given(parsers.parse("a cell of {n:d} runs where each run has at least 1 permission denial"))
def cell_with_every_run_denied(world, n):
    world["cells"][Cell(RULE_LABEL, TASK)] = CellShape(n, 0, denied=n)


@given(parsers.parse("a cell of {n:d} runs where {denied:d} runs have a denial and 1 run has none"))
def cell_with_one_run_clean(world, n, denied):
    assert denied == n - 1, f"the feature leaves exactly one run without a denial: {denied} of {n}"
    world["cells"][Cell(RULE_LABEL, TASK)] = CellShape(n, 0, denied=denied)


@given(parsers.parse('the LOO arm has k = {k:d} of 20 for "attempted_violation"'))
def loo_arm_with_k(world, k):
    world["cells"][Cell(LOO_LABEL, TASK)] = CellShape(20, k)
    world["cells"][Cell(REPEAT_LABEL, TASK)] = CellShape(20, k)


@given(parsers.parse('arm "first" has {k1:d} of 20 and arm "second" has {k2:d} of 20'))
def first_and_second_arms(world, k1, k2):
    world["cells"].update(
        {Cell(LOO_LABEL, TASK): CellShape(20, k1), Cell(REPEAT_LABEL, TASK): CellShape(20, k1), Cell(RULE_LABEL, TASK): CellShape(20, k2)}
    )


@then(parsers.parse('the verdict is "{name}"'))
def verdict_is(world, name):
    assert any(f"verdict {name};" in line for line in world["lines"] if line.startswith(TARGET)), f"got {world['lines']}"


@then(parsers.parse('the reason says "{text}" when it is shown'))
def reason_says_when_shown(world, text):
    shown = [line for line in world["lines"] if line.startswith("AtBound")]
    assert all(text in line for line in shown), f"got {shown}"


@given("the same counts with and without warnings enabled")
def same_counts_both_ways(world):
    world["cells"] = dict(SATURATED_AND_DENIED)


@when("I analyze the plan and decide", target_fixture="analyses")
def analyze_and_decide(world, tmp_path):
    site = site_with_state(tmp_path, world["roles"], (filled_cells(world["roles"], world["cells"]), PlanState.COMPLETE))
    analyses = {flag: analyze_site(site, False, flag) for flag in (True, False)}
    world["decisions"] = {
        flag: [decide(Reach.LOADED, row.effect, GuardResult.GUARD_UNTESTED) for row in analysis.rows if row.effect is not None]
        for flag, analysis in analyses.items()
    }
    return analyses


@then("the verdict is the same")
def verdict_is_the_same(analyses):
    assert analyses[True].warnings and not analyses[False].warnings, f"the check needs warnings on one side: {analyses}"
    assert analyses[True].rows == analyses[False].rows, f"warnings changed a row: {analyses}"


@then("the decision is the same")
def decision_is_the_same(world):
    assert world["decisions"][True] == world["decisions"][False] != [], f"got {world['decisions']}"
