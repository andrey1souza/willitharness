import hashlib
import json
from pathlib import Path

from willitharness.paths import inside

FIXTURE_DIRECTORY = "fixtures/traces"
MODEL_DIRECTORY = "formal/tla"
MODEL_FILES = ("WillItHarness.tla", "TraceWalk.tla")
DIGEST_LENGTH = len(hashlib.sha256().hexdigest())
HEADER_KEYS = ("scenario", "seed", "walks", "depth", "tlc_jar_sha256", "model_sha256", "constants")


def model_digest(root, scenario):
    assert isinstance(root, Path), f"model_digest needs the repository root as a Path, got {root!r}. Fix: pass a Path."
    assert scenario, "model_digest needs a scenario name. Fix: pass the name of a formal/tla cfg."
    names = (*MODEL_FILES, f"{scenario}.cfg")
    digest = hashlib.sha256()
    for name in names:
        digest.update((inside(root, f"{MODEL_DIRECTORY}/{name}")).read_bytes())
    assert len(digest.hexdigest()) == DIGEST_LENGTH, f"the digest {digest.hexdigest()} is not {DIGEST_LENGTH} hex digits. Rule: the fixture header holds a sha256. Fix: use hashlib.sha256."
    return digest.hexdigest()


def load_fixture(root, scenario):
    assert scenario, "load_fixture needs a scenario name. Fix: pass the name of a recorded scenario."
    path = inside(root, f"{FIXTURE_DIRECTORY}/{scenario}.json")
    assert path.is_file(), f"the fixture {path} does not exist. Fix: run make replay-fixtures."
    data = json.loads(path.read_text())
    missing = [key for key in HEADER_KEYS if key not in data.get("header", {})]
    assert not missing and data.get("walks"), f"{path} lacks header keys {missing} or walks. Rule: a fixture holds a full header and walks. Fix: run make replay-fixtures."
    return data["header"], data["walks"]


def stale_fixture_errors(root):
    assert root.is_dir(), f"{root} is not a directory. Fix: pass the repository root."
    folder = inside(root, FIXTURE_DIRECTORY)
    errors = []
    for path in sorted(folder.glob("*.json")) if folder.is_dir() else []:
        header, _ = load_fixture(root, path.stem)
        if header["model_sha256"] != model_digest(root, header["scenario"]):
            errors.append(f"{path.name} was recorded from another model or cfg. Rule: a fixture matches the model file digest. Fix: run make replay-fixtures and commit the result")
    assert all(isinstance(error, str) for error in errors), f"errors must be text, got {errors!r}"
    return errors
