import json

import repo_checks
from files import write_tree


def test_a_result_that_records_the_gate_detector_passes(tmp_path):
    recorded = {"detector": ["pkill", "pgrep -f", "pgrep --full"]}
    write_tree(tmp_path, {"fixtures/results/g4_4.json": json.dumps(recorded)})
    assert repo_checks.result_detector_errors(tmp_path) == [], f"the gate uses {repo_checks.pilot_live.STOP_SERVER_ACTIONS}"
    assert "result-detector" in repo_checks.CHECKS, "the check is registered"


def test_a_result_that_records_another_detector_is_reported(tmp_path):
    write_tree(tmp_path, {"fixtures/results/g4_4.json": json.dumps({"detector": ["pkill"]})})
    errors = repo_checks.result_detector_errors(tmp_path)
    assert len(errors) == 1 and "records the detector ['pkill']" in errors[0], f"unexpected errors {errors}"
    write_tree(tmp_path, {"fixtures/results/g4_4.json": json.dumps({})})
    assert len(repo_checks.result_detector_errors(tmp_path)) == 1, "a result with no detector is reported"
