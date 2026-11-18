from types import SimpleNamespace

import pytest

from willitharness.artifacts import REDACTED, RunArtifacts, artifact_directory, redact, secret_values, store_artifacts

ENVIRONMENT = {"MY_SECRET": "s3", "X_TOKEN": "tok-long", "A_KEY": "k", "HOME": "/home/u", "EMPTY_KEY": "", "lower_token": "low"}


def test_secret_values_takes_every_value_whose_name_holds_key_token_or_secret_longest_first():
    assert secret_values(ENVIRONMENT) == ("tok-long", "low", "s3", "k"), f"got {secret_values(ENVIRONMENT)!r}"


def test_secret_values_leaves_out_ordinary_and_empty_variables():
    assert "/home/u" not in secret_values(ENVIRONMENT) and "" not in secret_values(ENVIRONMENT), f"HOME and an empty KEY are not secrets, got {secret_values(ENVIRONMENT)!r}"


def test_redact_replaces_every_occurrence_and_keeps_the_rest():
    assert redact("a k b k tok-long", ("tok-long", "k")) == f"a {REDACTED} b {REDACTED} {REDACTED}", "every secret occurrence must be replaced"


def test_a_longer_secret_is_replaced_before_a_shorter_one_that_it_contains():
    assert redact("tok-long", secret_values({"A_KEY": "tok", "B_KEY": "tok-long"})) == REDACTED, "the longer secret goes first so no tail is left"


def test_the_artifact_folder_is_plan_runs_arm_task_rep(tmp_path):
    folder = artifact_directory(tmp_path, "demo", SimpleNamespace(arm="A", task="stop"), 3)
    assert folder == tmp_path.resolve() / ".willitharness" / "demo" / "runs" / "A" / "stop" / "3", f"got {folder}"


def test_an_arm_label_that_escapes_the_project_is_refused(tmp_path):
    from willitharness.paths import PathOutsideRoot

    with pytest.raises(PathOutsideRoot) as raised:
        artifact_directory(tmp_path, "demo", SimpleNamespace(arm="../../x", task="stop"), 1)
    assert "outside" in str(raised.value) and "Fix:" in str(raised.value), f"the refusal must name the escape and the fix, got {str(raised.value)!r}"


def test_store_artifacts_writes_both_files_redacted(tmp_path):
    store_artifacts(tmp_path, 2, RunArtifacts("line k", "call tok-long"), ENVIRONMENT)
    assert (tmp_path / "transcript-2.jsonl").read_text() == f"line {REDACTED}", f"got {(tmp_path / 'transcript-2.jsonl').read_text()!r}"
    assert (tmp_path / "calls-2.log").read_text() == f"call {REDACTED}", f"got {(tmp_path / 'calls-2.log').read_text()!r}"
