from pathlib import Path

from willitharness.artifacts import RUNS_DIR, TRANSCRIPT_NAME
from willitharness.lifecycle import lifecycle_dir
from willitharness.paths import inside
from willitharness.real_runner import AGENT_RECORD, VERSION_KEY
from willitharness.stream import load_event, model_of

UNKNOWN = "unknown"
MODEL_SEPARATOR = ", "
TRANSCRIPT_GLOB = TRANSCRIPT_NAME.format(attempt="*")


def agent_line(version, models):
    assert isinstance(models, tuple) and all(isinstance(model, str) and model for model in models), f"agent_line needs the model ids as a tuple of text, got {models!r}. Fix: build them with stored_models."
    assert version is None or isinstance(version, str), f"agent_line needs the version as text or None, got {version!r}. Fix: read it with stored_version."
    shown = tuple(sorted(set(models))) or (UNKNOWN,)
    label = "models" if len(shown) > 1 else "model"
    line = f"agent: claude {version or UNKNOWN}, {label} {MODEL_SEPARATOR.join(shown)}"
    assert line.startswith("agent: claude "), f"agent_line lost its fixed start: {line!r}"
    assert UNKNOWN in line or version in line, f"agent_line dropped the version {version!r}: {line!r}"
    return line


def stored_version(folder):
    assert isinstance(folder, Path) and folder.is_dir(), f"stored_version needs the plan folder, got {folder!r}. Fix: use lifecycle_dir."
    record = inside(folder, AGENT_RECORD)
    version = load_event(record.read_text()).get(VERSION_KEY) if record.is_file() else None
    result = version if isinstance(version, str) and version else None
    assert result is None or isinstance(result, str), f"stored_version returned {result!r}, not text"
    return result


def stored_models(folder):
    assert isinstance(folder, Path) and folder.is_dir(), f"stored_models needs the plan folder, got {folder!r}. Fix: use lifecycle_dir."
    runs = inside(folder, RUNS_DIR)
    transcripts = sorted(runs.rglob(TRANSCRIPT_GLOB)) if runs.is_dir() else []
    found = tuple(model for model in (model_of(path.read_text().splitlines()) for path in transcripts) if model)
    assert all(isinstance(model, str) and model for model in found), f"stored_models found a bad id in {found!r}"
    assert len(found) <= len(transcripts), f"stored_models read {len(found)} ids from {len(transcripts)} transcripts"
    return found


def read_agent_line(root, plan):
    assert isinstance(root, Path), f"read_agent_line needs a Path root, got {root!r}. Fix: pass the project directory."
    assert plan.name, "read_agent_line needs a named plan. Fix: load the plan with read_plan."
    folder = lifecycle_dir(root, plan)
    line = agent_line(stored_version(folder), stored_models(folder))
    assert line.startswith("agent: claude "), f"read_agent_line built {line!r}"
    return line
