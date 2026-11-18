import hashlib
import json
from pathlib import Path

from willitharness.paths import inside

STUBS_DIR = "stubs"
STUB_OUTPUT_NAME = "output.txt"
REAL_FILE = "real.txt"
TASKS_FILE = "tasks.txt"
TASK_SEPARATOR = ":"
PARENT_SEGMENT = ".."
ROOT_PREFIX = "/"
HASH_LENGTH = 8
PATH_NAME_SEPARATOR = b"\0"
CONTENT_SEPARATOR = b"\1"
RECORD_HASH_KEY = "hash"
RECORD_VALIDATED_KEY = "validated"
STORE_DIR = ".willitharness"
STORE_NAME = "world.json"


class WorldError(Exception):
    pass


def world_files(world_dir):
    assert isinstance(world_dir, Path), f"world_files needs a Path, got {world_dir!r}. Fix: pass pathlib.Path."
    assert world_dir.is_dir(), f"{world_dir} is not a directory. Rule: a world is a directory. Fix: pass the world directory."
    files = sorted(path for path in world_dir.rglob("*") if path.is_file())
    assert all(path.is_relative_to(world_dir) for path in files), f"world_files found a file outside {world_dir}: {files!r}"
    return files


def world_hash(world_dir):
    assert isinstance(world_dir, Path), f"world_hash needs a Path, got {world_dir!r}. Fix: pass pathlib.Path."
    assert world_dir.is_dir(), f"{world_dir} is not a directory. Rule: a world is a directory. Fix: pass the world directory."
    digest = hashlib.sha256()
    for path in world_files(world_dir):
        digest.update(path.relative_to(world_dir).as_posix().encode() + PATH_NAME_SEPARATOR)
        digest.update(path.read_bytes() + CONTENT_SEPARATOR)
    short = digest.hexdigest()[:HASH_LENGTH]
    assert len(short) == HASH_LENGTH, f"the hash {short!r} is not {HASH_LENGTH} characters long"
    return short


def read_lines(world_dir, name):
    assert isinstance(world_dir, Path), f"read_lines needs a Path, got {world_dir!r}. Fix: pass pathlib.Path."
    assert name, f"read_lines needs a file name under {world_dir}. Fix: pass REAL_FILE or TASKS_FILE."
    path = inside(world_dir, name)
    if not path.is_file():
        return []
    lines = [line.strip() for line in path.read_text().splitlines()]
    return [line for line in lines if line]


def declared_real(world_dir):
    assert isinstance(world_dir, Path), f"declared_real needs a Path, got {world_dir!r}. Fix: pass pathlib.Path."
    assert world_dir.is_dir(), f"{world_dir} is not a directory. Rule: a world is a directory. Fix: pass the world directory."
    return frozenset(read_lines(world_dir, REAL_FILE))


def stub_outputs(world_dir):
    assert isinstance(world_dir, Path), f"stub_outputs needs a Path, got {world_dir!r}. Fix: pass pathlib.Path."
    assert world_dir.is_dir(), f"{world_dir} is not a directory. Rule: a world is a directory. Fix: pass the world directory."
    outputs = {path.parent.name: path.read_text() for path in sorted((world_dir / STUBS_DIR).glob(f"*/{STUB_OUTPUT_NAME}"))}
    assert all(isinstance(text, str) for text in outputs.values()), f"stub outputs must be text, got {outputs!r}"
    return outputs


def task_commands(world_dir):
    assert isinstance(world_dir, Path), f"task_commands needs a Path, got {world_dir!r}. Fix: pass pathlib.Path."
    assert world_dir.is_dir(), f"{world_dir} is not a directory. Rule: a world is a directory. Fix: pass the world directory."
    tasks = {}
    for line in read_lines(world_dir, TASKS_FILE):
        name, separator, commands = line.partition(TASK_SEPARATOR)
        if not separator or not name.strip():
            raise WorldError(
                f"{TASKS_FILE} line {line!r} has no task name. "
                f"Rule: each line is <task>{TASK_SEPARATOR} <command> <command>. Fix: write the line as <task>{TASK_SEPARATOR} <commands>."
            )
        tasks[name.strip()] = tuple(commands.split())
    assert all(isinstance(commands, tuple) for commands in tasks.values()), f"task commands must be tuples, got {tasks!r}"
    return tasks


def check_commands(world_dir):
    assert isinstance(world_dir, Path), f"check_commands needs a Path, got {world_dir!r}. Fix: pass pathlib.Path."
    assert world_dir.is_dir(), f"{world_dir} is not a directory. Rule: a world is a directory. Fix: pass the world directory."
    known = set(stub_outputs(world_dir)) | declared_real(world_dir)
    for task, commands in task_commands(world_dir).items():
        for command in commands:
            if command not in known:
                raise WorldError(
                    f"task names {command} but the world has no stub or declaration for it. "
                    f"Rule: W1, every command task {task} names has a stub or is declared real. "
                    f"Fix: add {STUBS_DIR}/{command}/{STUB_OUTPUT_NAME} or add {command} to {REAL_FILE}."
                )
    assert all(command in known for commands in task_commands(world_dir).values() for command in commands), f"check_commands let an unknown command pass in {world_dir}"


def path_tokens(text):
    assert isinstance(text, str), f"path_tokens needs text, got {text!r}. Fix: pass the stub output."
    tokens = [token for token in text.split() if token.startswith(ROOT_PREFIX) or PARENT_SEGMENT in Path(token).parts]
    assert all(token in text for token in tokens), f"path_tokens invented a token in {tokens!r}"
    return tokens


def check_stub_paths(world_dir):
    assert isinstance(world_dir, Path), f"check_stub_paths needs a Path, got {world_dir!r}. Fix: pass pathlib.Path."
    assert world_dir.is_dir(), f"{world_dir} is not a directory. Rule: a world is a directory. Fix: pass the world directory."
    root = world_dir.resolve()
    for stub, text in stub_outputs(world_dir).items():
        for token in path_tokens(text):
            if not (root / token).resolve().is_relative_to(root):
                raise WorldError(
                    f"world invalid: stub output refers to a path outside the world. Stub {stub} prints {token}, outside {root}. "
                    f"Rule: W2, stub output references only paths inside the world. Fix: list only paths under the world root {root} in {STUBS_DIR}/{stub}/{STUB_OUTPUT_NAME}."
                )
    assert root.is_dir(), f"the world root {root} vanished during the check"


def validate_world(world_dir):
    assert isinstance(world_dir, Path), f"validate_world needs a Path, got {world_dir!r}. Fix: pass pathlib.Path."
    assert world_dir.is_dir(), f"{world_dir} is not a directory. Rule: a world is a directory. Fix: pass the world directory."
    check_commands(world_dir)
    check_stub_paths(world_dir)
    validated = world_hash(world_dir)
    assert len(validated) == HASH_LENGTH, f"validate_world returned {validated!r}. Rule: the hash has {HASH_LENGTH} characters."
    return validated


def store_path(root, world_dir):
    assert isinstance(root, Path) and isinstance(world_dir, Path), f"store_path needs Paths, got {root!r} and {world_dir!r}. Fix: pass pathlib.Path."
    assert world_dir.name, f"{world_dir!r} has no name. Fix: pass a named world directory."
    return inside(root, f"{STORE_DIR}/{world_dir.name}/{STORE_NAME}")


def store_validation(root, world_dir, validated_hash):
    assert validated_hash, "store_validation needs a hash. Fix: pass the hash validate_world returned."
    store_file = store_path(root, world_dir)
    store_file.parent.mkdir(parents=True, exist_ok=True)
    store_file.write_text(json.dumps({RECORD_HASH_KEY: validated_hash, RECORD_VALIDATED_KEY: True}))
    assert stored_hash(root, world_dir) == validated_hash, f"{store_file} did not keep {validated_hash!r}"


def stored_hash(root, world_dir):
    store_file = store_path(root, world_dir)
    assert store_file.name == STORE_NAME, f"the record path {store_file} must end in {STORE_NAME}"
    if not store_file.is_file():
        return None
    record = json.loads(store_file.read_text())
    assert RECORD_HASH_KEY in record, f"{store_file} has no {RECORD_HASH_KEY}. Rule: store_validation wrote it. Fix: run willitharness world check."
    return record[RECORD_HASH_KEY] if record.get(RECORD_VALIDATED_KEY) else None


def world_changed(root, world_dir):
    assert isinstance(root, Path), f"world_changed needs a Path root, got {root!r}. Fix: pass pathlib.Path."
    assert world_dir.is_dir(), f"{world_dir} is not a directory. Rule: a world is a directory. Fix: pass the world directory."
    stored = stored_hash(root, world_dir)
    changed = stored is not None and stored != world_hash(world_dir)
    assert isinstance(changed, bool), f"world_changed returned {changed!r}, not a bool"
    return changed
