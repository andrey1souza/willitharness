from dataclasses import dataclass
from pathlib import Path

from willitharness.paths import inside
from willitharness.world import STORE_DIR

REDACTED = "[redacted]"
SECRET_MARKERS = ("KEY", "TOKEN", "SECRET")
RUNS_DIR = "runs"
TRANSCRIPT_NAME = "transcript-{attempt}.jsonl"
CALLS_NAME = "calls-{attempt}.log"


@dataclass(frozen=True)
class RunArtifacts:
    transcript: str
    calls: str


def secret_values(environment):
    assert hasattr(environment, "items"), f"secret_values needs a mapping of variables, got {type(environment).__name__}. Fix: pass the agent environment."
    values = {value for name, value in environment.items() if value and any(marker in name.upper() for marker in SECRET_MARKERS)}
    ordered = tuple(sorted(values, key=lambda value: (-len(value), value)))
    assert all(ordered), f"secret_values kept an empty value in {ordered!r}"
    return ordered


def redact(text, secrets):
    assert isinstance(text, str), f"redact needs text, got {type(text).__name__}. Fix: pass the transcript or log text."
    assert isinstance(secrets, tuple), f"redact needs the secrets as a tuple, got {type(secrets).__name__}. Fix: pass secret_values output."
    for secret in secrets:
        text = text.replace(secret, REDACTED)
    assert not any(secret in text for secret in secrets), f"redact left a secret in the text. Rule: a stored artifact holds no secret value."
    return text


def artifact_directory(root, plan_name, cell, rep):
    assert isinstance(root, Path), f"artifact_directory needs a Path root, got {root!r}. Fix: pass the project directory."
    assert rep >= 1, f"rep {rep} starts at 1. Rule: run ids count from 1. Fix: claim jobs through claim_next_job."
    runs = inside(root, f"{STORE_DIR}/{plan_name}/{RUNS_DIR}")
    runs.mkdir(parents=True, exist_ok=True)
    folder = inside(runs, f"{cell.arm}/{cell.task}/{rep}")
    folder.mkdir(parents=True, exist_ok=True)
    assert folder.is_dir(), f"{folder} was not created. Rule: artifacts live under {STORE_DIR}."
    return folder


def store_artifacts(folder, attempt, artifacts, environment):
    assert folder.is_dir(), f"{folder} is not a directory. Fix: build it with artifact_directory."
    assert attempt >= 1, f"attempt {attempt} starts at 1. Rule: run ids count from 1."
    secrets = secret_values(environment)
    transcript = folder / TRANSCRIPT_NAME.format(attempt=attempt)
    calls = folder / CALLS_NAME.format(attempt=attempt)
    transcript.write_text(redact(artifacts.transcript, secrets))
    calls.write_text(redact(artifacts.calls, secrets))
    assert transcript.is_file() and calls.is_file(), f"the artifacts under {folder} are incomplete"
    return transcript, calls
