import copy
import json
from pathlib import Path

import pytest
import trace_fixtures
import trace_replay
from files import write_tree

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = REPO_ROOT / trace_fixtures.FIXTURE_DIRECTORY
RECORDED = {"resume_world": (8, 136), "unusable": (8, 143), "resume_abort": (72, 436)}
CONSTANTS = {"Reps": 1, "MaxRetries": 0, "RunCap": 2, "Budget": 3}
DIGEST_OF_ABC = "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
RECORD_STEP = 9
MODEL_FILES = {"formal/tla/WillItHarness.tla": "a", "formal/tla/TraceWalk.tla": "b", "formal/tla/demo.cfg": "c"}
HEADER = {"scenario": "demo", "seed": 1, "walks": 1, "depth": 2, "tlc_jar_sha256": "x", "constants": CONSTANTS}


def recorded(name):
    return trace_fixtures.load_fixture(REPO_ROOT, name)


def running_state(startable):
    zero_cells = {"LOO/t1": [0, 0, 0, 0], "Rule/t1": [0, 0, 0, 0]}
    return {"state": "Running", "worldOk": True, "budget": 3, "analyzable": False, "finishable": False, "startable": startable, "cells": zero_cells}


def running_rig(tmp_path):
    rig = trace_replay.build_rig(tmp_path / "site", CONSTANTS, ["LOO", "Rule"])
    loaded = {"reach": {"LOO": "Loaded", "Rule": "Loaded"}}
    for action in (["ValidateWorld"], ["CheckReach", "LOO"], ["CheckReach", "Rule"], ["BeginRunning"]):
        trace_replay.replay_action(rig, action, loaded)
    assert trace_replay.observe(rig)["state"] == "Running", "the rig must be Running before a probe"
    return rig


@pytest.mark.parametrize("name", sorted(RECORDED))
def test_every_recorded_walk_replays_on_the_code_without_divergence(name):
    header, walks = recorded(name)
    result = trace_replay.replay_walks(walks, header)
    assert result.divergence is None, trace_replay.describe(result.divergence)
    assert (result.walks, result.steps) == RECORDED[name], f"{name} replayed {result.walks} walks and {result.steps} states, expected {RECORDED[name]}"
    assert result.probes > result.steps, f"{name} ran {result.probes} refusal probes for {result.steps} states"


def test_the_recorded_walks_take_every_action_the_code_replays():
    every_walk = [walk for name in RECORDED for walk in recorded(name)[1]]
    assert trace_replay.coverage_errors(every_walk) == [], "the recorded walks must take every replayed action"
    assert len(every_walk) == 88, f"expected 88 recorded walks, got {len(every_walk)}"


def test_a_walk_that_only_starts_misses_every_action_and_the_abort_in_flight():
    start_only = [[recorded("resume_world")[1][0][0]]]
    errors = trace_replay.coverage_errors(start_only)
    assert len(errors) == len(trace_replay.CODE_ACTIONS) + 1, f"expected one error per action and one for the abort, got {errors}"
    assert any("Abort with a run in flight" in error for error in errors), f"the abort in flight must be named, got {errors}"


def test_a_wrong_model_cost_is_reported_with_the_walk_the_step_and_both_states():
    header, walks = recorded("resume_world")
    tampered = copy.deepcopy(walks)
    for state in tampered[0][RECORD_STEP:]:
        state["cells"]["LOO/t1"][3] = 1
    result = trace_replay.replay_walks(tampered, header)
    divergence = result.divergence
    assert divergence is not None, "a changed model cost must diverge from the code"
    assert (divergence.walk, divergence.step, divergence.action) == (0, RECORD_STEP, "Record"), f"expected walk 0 step {RECORD_STEP} Record, got {divergence}. Fix: the replay must stop at the first changed step."
    assert divergence.model["cells"]["LOO/t1"] == [1, 1, 0, 1] and divergence.code["cells"]["LOO/t1"] == [1, 1, 0, 2], f"both states must show the cost, got {divergence}"
    text = trace_replay.describe(divergence)
    assert "seed 20261119, walk 0, step 9 (Record)" in text and "model:" in text and "code:" in text, f"the report must name seed, walk, step and both states, got {text}"


def test_a_start_the_model_forbids_but_the_code_allows_is_caught_by_the_probe(tmp_path):
    rig = running_rig(tmp_path)
    problems, probed = trace_replay.probe_refusals(rig, running_state([]))
    assert len(problems) == 2 and problems[0].startswith("the code started a run in LOO"), f"expected the start and the ending of Running reported, got {problems}"
    assert probed == 6, f"expected 6 probes, got {probed}"


def test_the_probe_is_quiet_when_the_model_and_the_code_agree(tmp_path):
    rig = running_rig(tmp_path)
    problems, probed = trace_replay.probe_refusals(rig, running_state(["LOO/t1", "Rule/t1"]))
    assert problems == [], f"agreeing states must raise no problem, got {problems}"
    assert probed == 6, f"expected 6 probes, got {probed}"


def test_a_fixture_recorded_from_the_current_model_is_fresh(tmp_path):
    write_tree(tmp_path, MODEL_FILES)
    write_tree(tmp_path, {"fixtures/traces/demo.json": json.dumps({"header": {**HEADER, "model_sha256": DIGEST_OF_ABC}, "walks": [[{}]]})})
    errors = trace_fixtures.stale_fixture_errors(tmp_path)
    assert errors == [], f"a fixture with the digest of the model files must be fresh, got {errors}"
    assert trace_fixtures.model_digest(tmp_path, "demo") == DIGEST_OF_ABC, "the digest covers the model, the walker and the cfg in that order"


def test_a_fixture_recorded_from_another_model_is_stale(tmp_path):
    write_tree(tmp_path, {**MODEL_FILES, "formal/tla/TraceWalk.tla": "changed"})
    write_tree(tmp_path, {"fixtures/traces/demo.json": json.dumps({"header": {**HEADER, "model_sha256": DIGEST_OF_ABC}, "walks": [[{}]]})})
    errors = trace_fixtures.stale_fixture_errors(tmp_path)
    assert len(errors) == 1 and errors[0].startswith("demo.json was recorded from another model"), f"a changed walker must make the fixture stale, got {errors}"
    assert "Fix: run make replay-fixtures" in errors[0], f"the error must name the fix, got {errors}"


def test_the_repository_fixtures_are_fresh():
    errors = trace_fixtures.stale_fixture_errors(REPO_ROOT)
    assert errors == [], f"the committed fixtures are stale: {errors}"
    assert sorted(path.stem for path in FIXTURES.glob("*.json")) == sorted(RECORDED), f"unexpected fixtures in {FIXTURES}"
