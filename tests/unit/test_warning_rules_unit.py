from dataclasses import replace

import pytest
from analysis_site import COMPLETED, FULL_ROLES, TARGET, analyze_site, filled_cells, site_with_state

from willitharness.analysis import AnalysisInput, Row, analyze_plan
from willitharness.counts import Counts
from willitharness.lifecycle import PlanState, lifecycle_dir, read_reach
from willitharness.store import Cell, Record, RunState, append_record, load_records, run_id_of
from willitharness.vocabulary import EffectResult, NoiseStatus, Verdict
from willitharness.warning_rules import NO_WORLD_FACTS, WorldFacts, at_bound, cell_warnings, model_warnings, row_warnings, world_mix_lines, world_warnings


def row(outcome, first, second, verdict):
    return Row(outcome, "stop-server", "C", "B", False, Counts(*first), Counts(*second), NoiseStatus.NOISE_OK, verdict, EffectResult.NO_MEASURABLE_EFFECT, None)


@pytest.mark.parametrize("n, shown", [(0, True), (10, True), (12, True), (19, True), (20, False), (25, False)])
def test_W_LOWN_appears_below_twenty_usable_runs(n, shown):
    lines = cell_warnings({Cell("B", "stop-server"): Counts(0, n)}, frozenset())
    assert bool(lines) is shown, f"n {n} gave {lines}"
    assert not shown or lines == [f"W-LOWN: arm B, task stop-server has {n} usable runs; 20 are recommended"], f"got {lines}"


def test_W_DENIAL_names_the_denied_cell_only():
    counts = {Cell("B", "stop-server"): Counts(0, 20), Cell("C", "stop-server"): Counts(0, 20)}
    assert cell_warnings(counts, frozenset({Cell("B", "stop-server")})) == ["W-DENIAL: arm B, task stop-server: every run has a permission denial"], "one line for the denied cell"
    assert cell_warnings(counts, frozenset()) == [], "no denied cell, no line"


@pytest.mark.parametrize(
    "first, second, expected",
    [((0, 20), (0, 20), True), ((20, 20), (20, 20), True), ((0, 20), (1, 20), False), ((10, 20), (10, 20), False), ((0, 0), (0, 0), False), ((20, 20), (19, 20), False)],
)
def test_AtBound_needs_both_arms_at_zero_or_both_at_full(first, second, expected):
    assert at_bound(Counts(*first), Counts(*second)) is expected, f"{first} against {second}"
    assert at_bound(Counts(*second), Counts(*first)) is expected, f"AtBound is symmetric: {second} against {first} must give {expected}"


def test_saturated_needs_a_measured_loo_arm_with_no_violating_run_on_the_target_outcome():
    assert row_warnings([row(TARGET, (0, 20), (5, 20), Verdict.FIRST_LOWER)])[0].startswith("saturated: arm C, task stop-server"), "k = 0 of 20 is saturated"
    assert row_warnings([row(TARGET, (1, 20), (5, 20), Verdict.FIRST_LOWER)]) == [], "k = 1 is not saturated"
    assert row_warnings([row(TARGET, (0, 0), (5, 20), Verdict.INCONCLUSIVE_SMALL_N)]) == [], "an empty arm is not saturated"
    assert row_warnings([row(COMPLETED, (0, 20), (5, 20), Verdict.FIRST_LOWER)]) == [], "saturated speaks about the target outcome only"


def test_AtBound_is_reported_for_an_inconclusive_verdict_only():
    assert len(row_warnings([row(COMPLETED, (20, 20), (20, 20), Verdict.INCONCLUSIVE)])) == 1, "an inconclusive verdict at the bound warns"
    assert row_warnings([row(COMPLETED, (20, 20), (20, 20), None)]) == [], "no verdict, no AtBound reason"


def test_a_pooled_row_gives_the_pooled_warning_once():
    pooled = Row(TARGET, "all:pooled", "C", "B", True, Counts(5, 20), Counts(5, 20), NoiseStatus.NOISE_OK, Verdict.INCONCLUSIVE, EffectResult.NO_MEASURABLE_EFFECT, None)
    assert row_warnings([pooled, pooled]) == ["pooled: task clustering is ignored"], f"got {row_warnings([pooled, pooled])}"


def started_in_world(run_id, arm, world_hash):
    return Record(run_id, arm, "stop-server", 1, 1, RunState.STARTED, {}, 0.0, world_hash=world_hash)


def test_T62_a_cell_with_two_worlds_gets_one_warning_naming_it():
    records = (started_in_world("B/stop-server/1#1", "B", "aa"), started_in_world("B/stop-server/2#2", "B", "bb"), started_in_world("C/stop-server/1#1", "C", "aa"))
    assert world_warnings(records, NO_WORLD_FACTS) == ["W-WORLD: arm B, task stop-server has runs from 2 worlds; the runs do not share one validated world"], "only cell B mixes worlds"


def test_T62_cells_with_one_world_or_no_recorded_world_get_no_warning():
    records = (started_in_world("B/stop-server/1#1", "B", "aa"), started_in_world("B/stop-server/2#2", "B", "aa"), started_in_world("C/stop-server/1#1", "C", ""), started_in_world("C/stop-server/2#2", "C", "bb"))
    assert world_mix_lines(records) == [], "one hash per cell, and a record without a hash, are not a mix"


def test_T62_analyze_reports_a_cell_that_mixes_worlds_only_with_warnings_on(tmp_path):
    site = site_with_state(tmp_path, FULL_ROLES, (filled_cells(FULL_ROLES, {}), PlanState.COMPLETE))
    cell = Cell("B", "stop-server")
    for rep, world in ((21, "aa"), (22, "bb")):
        append_record(lifecycle_dir(site.root, site.plan), Record(run_id_of(cell, rep, 1), "B", "stop-server", rep, 1, RunState.RECORDED_USABLE, {TARGET: True, COMPLETED: True}, 0.01, {TARGET: False, COMPLETED: True}, 0, world))
    wanted = "W-WORLD: arm B, task stop-server has runs from 2 worlds; the runs do not share one validated world"
    shown, hidden = analyze_site(site, False, True).warnings, analyze_site(site, False, False).warnings
    assert wanted in shown, f"the mix {wanted!r} must be reported, got {shown}. Fix: add world_warnings to analyze_plan."
    assert hidden == (), f"warnings off must print none, got {hidden}. Rule: with_warnings controls every warning."


LEFT_WORLD = "W-WORLD: arm B, task stop-server has 1 runs that left the validated world aa; their world hash differs from the validated hash"
NO_HASH = "W-NOHASH: {n} runs carry no world hash; they were recorded before T62 and cannot show a mixed world"
ENDED_CHANGED = "W-WORLD: the plan ended while its world differed from the validated one; run willitharness world check and run the plan again before you trust it"


def test_T65_a_run_whose_hash_differs_from_the_validated_hash_left_the_validated_world():
    records = (started_in_world("B/stop-server/1#1", "B", "aa"), started_in_world("B/stop-server/2#2", "B", "bb"))
    mix = "W-WORLD: arm B, task stop-server has runs from 2 worlds; the runs do not share one validated world"
    assert world_warnings(records, WorldFacts("aa", False)) == [mix, LEFT_WORLD], "the mix line stays and only the run with hash bb left world aa"
    assert world_warnings(records[:1], WorldFacts("aa", False)) == [], "a run in the validated world does not warn"
    assert not any("left the validated world" in line for line in world_warnings(records, NO_WORLD_FACTS)), f"with no validated hash there is nothing to leave, got {world_warnings(records, NO_WORLD_FACTS)}"


def test_T65_runs_without_a_hash_are_counted_and_never_counted_as_leaving_the_world():
    records = (started_in_world("B/stop-server/1#1", "B", ""), started_in_world("C/stop-server/1#1", "C", ""), started_in_world("C/stop-server/2#2", "C", "aa"))
    assert world_warnings(records, WorldFacts("aa", False)) == [NO_HASH.format(n=2)], "two runs carry no hash and the hashed run is in the validated world"
    assert world_warnings(records[2:], WorldFacts("aa", False)) == [], "no run without a hash, no count line"


def test_T65_a_plan_that_ended_in_a_changed_world_gets_one_line_saying_so():
    records = (started_in_world("B/stop-server/1#1", "B", "aa"),)
    assert world_warnings(records, WorldFacts("aa", True)) == [ENDED_CHANGED], "the ended-changed fact gives one line"
    assert world_warnings(records, WorldFacts("aa", False)) == [], "an unchanged world gives no line"


def test_T65_analyze_prints_the_three_world_lines_only_with_warnings_on(tmp_path):
    site = site_with_state(tmp_path, FULL_ROLES, (filled_cells(FULL_ROLES, {}), PlanState.COMPLETE))
    folder = lifecycle_dir(site.root, site.plan)
    cell = Cell("B", "stop-server")
    append_record(folder, Record(run_id_of(cell, 21, 1), "B", "stop-server", 21, 1, RunState.RECORDED_USABLE, {TARGET: True, COMPLETED: True}, 0.01, {TARGET: False, COMPLETED: True}, 0, "bb"))
    inputs = AnalysisInput(site.plan, load_records(folder), read_reach(folder), False, WorldFacts("aa", True))
    shown, hidden = analyze_plan(inputs, True).warnings, analyze_plan(inputs, False).warnings
    wanted = (LEFT_WORLD, ENDED_CHANGED)
    assert all(line in shown for line in wanted) and any(line.startswith("W-NOHASH: ") for line in shown), f"the three world lines must show, got {shown}. Fix: pass world_facts into analyze_plan."
    assert hidden == (), f"warnings off must print none, got {hidden}"


def started_on(run_id, arm, model):
    return Record(run_id, arm, "stop-server", 1, 1, RunState.STARTED, {}, 0.0, model=model)


MODEL_MIX = "W-MODEL: the plan has runs on 2 models: haiku 2 runs, sonnet 1 runs; runs on different models are not one result"
NO_MODEL = "W-NOMODEL: {n} runs carry no model name; they were recorded before T73 and may use another model"


def test_T73_records_on_two_models_give_one_line_naming_each_model_and_its_runs():
    records = (started_on("B/stop-server/1#1", "B", "sonnet"), started_on("B/stop-server/2#1", "B", "haiku"), started_on("C/stop-server/1#1", "C", "haiku"))
    assert model_warnings(records) == [MODEL_MIX], f"got {model_warnings(records)}. Rule: T73, name the models and the runs of each."


def test_T73_one_model_gives_no_line_and_a_plan_without_records_gives_none():
    records = (started_on("B/stop-server/1#1", "B", "haiku"), started_on("C/stop-server/1#1", "C", "haiku"))
    assert model_warnings(records) == [] and model_warnings(()) == [], f"got {model_warnings(records)} and {model_warnings(())}. Rule: T73, one model is not a mix."


def test_T73_runs_without_a_model_are_counted_and_do_not_make_a_mix():
    records = (started_on("B/stop-server/1#1", "B", ""), started_on("C/stop-server/1#1", "C", ""), started_on("C/stop-server/2#1", "C", "haiku"))
    assert model_warnings(records) == [NO_MODEL.format(n=2)], f"got {model_warnings(records)}. Rule: T73, an unnamed run is counted, never a second model."
    assert model_warnings(records[2:]) == [], "no unnamed run, no count line"


def test_T73_a_retried_run_counts_once_under_its_latest_record():
    started = started_on("B/stop-server/1#1", "B", "haiku")
    records = (started, replace(started, state=RunState.RECORDED_USABLE), started_on("B/stop-server/2#1", "B", "sonnet"))
    assert model_warnings(records) == ["W-MODEL: the plan has runs on 2 models: haiku 1 runs, sonnet 1 runs; runs on different models are not one result"], f"got {model_warnings(records)}"


def test_T73_analyze_prints_the_model_lines_only_with_warnings_on(tmp_path):
    site = site_with_state(tmp_path, FULL_ROLES, (filled_cells(FULL_ROLES, {}), PlanState.COMPLETE))
    folder = lifecycle_dir(site.root, site.plan)
    cell = Cell("B", "stop-server")
    append_record(folder, Record(run_id_of(cell, 21, 1), "B", "stop-server", 21, 1, RunState.RECORDED_USABLE, {TARGET: True, COMPLETED: True}, 0.01, {TARGET: False, COMPLETED: True}, 0, "", "haiku"))
    append_record(folder, Record(run_id_of(cell, 22, 1), "B", "stop-server", 22, 1, RunState.RECORDED_USABLE, {TARGET: True, COMPLETED: True}, 0.01, {TARGET: False, COMPLETED: True}, 0, "", "sonnet"))
    inputs = AnalysisInput(site.plan, load_records(folder), read_reach(folder), False, NO_WORLD_FACTS)
    shown, hidden = analyze_plan(inputs, True).warnings, analyze_plan(inputs, False).warnings
    assert any(line.startswith("W-MODEL: the plan has runs on 2 models: haiku 1 runs, sonnet 1 runs") for line in shown) and any(line.startswith("W-NOMODEL: ") for line in shown), f"got {shown}. Fix: add model_warnings to analyze_plan."
    assert hidden == (), f"warnings off must print none, got {hidden}"
