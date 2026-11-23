import json
from dataclasses import asdict, dataclass
from pathlib import Path

RESUME_FILE = "resume.json"
NOT_ENDED = "none"
RESUME_WORLD_REFUSED = "world not validated or changed since validation. Rule: L10, the world must be validated again before a resume. Fix: run willitharness world check."
RESUME_NO_RECORD = "plan has no stored budget and fingerprint. Rule: L10, a plan stores both when it first runs. Fix: start the plan with run before resuming."
RESUME_PLAN_CHANGED = "plan differs from the stored plan in more than budget_usd. Rule: A-FP, a resume changes only the budget. Fix: restore the plan and raise only budget_usd."
RESUME_NO_OVERLAYS = "plan stored its fingerprint without overlay files. Rule: A-FP, the fingerprint covers every overlay file, and this plan started before that. Fix: start the plan again under a new name."


def overlay_changed_message(names):
    assert names, "overlay_changed_message needs the changed files. Fix: pass the names that differ."
    message = f"overlay files changed since the first run: {', '.join(names)}. Rule: A-FP, a resume keeps every overlay file as it was. Fix: restore these files or start the plan again under a new name."
    assert all(name in message for name in names), f"the message {message!r} lacks a changed file from {names!r}"
    return message


@dataclass(frozen=True)
class ResumeRecord:
    budget_usd: float
    fingerprint: str
    ended_by: str
    ended_in_changed_world: bool = False
    overlay_files: dict | None = None


def read_resume(folder):
    assert isinstance(folder, Path), f"read_resume needs the plan folder as a Path, got {folder!r}. Fix: use lifecycle_dir."
    path = folder / RESUME_FILE
    record = ResumeRecord(**json.loads(path.read_text())) if path.is_file() else None
    assert record is None or record.fingerprint, f"{path} holds no fingerprint. Rule: the fingerprint is stored with the budget."
    return record


def write_resume(folder, record):
    assert isinstance(record, ResumeRecord), f"write_resume needs a ResumeRecord, got {record!r}. Fix: build one with the budget, fingerprint and ended marker."
    (folder / RESUME_FILE).write_text(json.dumps(asdict(record)))
    assert read_resume(folder) == record, f"{folder / RESUME_FILE} did not keep {record}. Rule: the stored budget, fingerprint and ended marker persist."
