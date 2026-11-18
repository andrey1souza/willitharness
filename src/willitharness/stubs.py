import shlex
import shutil
from functools import partial
from pathlib import Path

from willitharness.paths import inside
from willitharness.world import stub_outputs

BIN_NAME = "bin"
CALLS_LOG = "calls.log"
WRAPPER_MODE = 0o755
WRAPPER_TEMPLATE = (
    "#!/bin/sh\n"
    "{{ printf '%s' {command}; for argument in \"$@\"; do printf ' %s' \"$argument\"; done; printf '\\n'; }} >> {log}\n"
    "printf '%s' {output}\n"
    "exit 0\n"
)


def wrapper_text(command, output, log):
    assert command and "/" not in command, f"wrapper_text needs a plain command name, got {command!r}. Fix: name the stub folder after the command."
    assert isinstance(log, Path) and log.is_absolute(), f"wrapper_text needs an absolute log path, got {log!r}. Fix: pass the workspace calls log."
    text = WRAPPER_TEMPLATE.format(command=shlex.quote(command), log=shlex.quote(str(log)), output=shlex.quote(output))
    assert text.startswith("#!/bin/sh\n"), f"the wrapper for {command} lost its shebang: {text!r}"
    return text


def reserved_at_top(source, directory, names):
    assert source.is_absolute(), f"{source} is not absolute. Rule: the copy compares resolved folders. Fix: pass a resolved source."
    assert isinstance(names, (list, set, tuple)), f"names is {type(names).__name__}, not a collection of entries. Fix: use this function as a copytree ignore."
    reserved = {BIN_NAME, CALLS_LOG} & set(names) if Path(directory) == source else set()
    assert reserved <= {BIN_NAME, CALLS_LOG}, f"reserved_at_top invented the names {reserved!r}"
    return reserved


def copy_without_reserved(source, destination):
    assert source.is_dir(), f"{source} is not a directory. Fix: pass the world or overlay directory."
    assert destination.parent.is_dir(), f"{destination.parent} is not a directory. Fix: create the run folder first."
    resolved = inside(source, ".")
    shutil.copytree(resolved, destination, dirs_exist_ok=True, ignore=partial(reserved_at_top, resolved))
    assert destination.is_dir(), f"{destination} was not created"


def write_stub_wrappers(world_dir, work):
    assert world_dir.is_dir(), f"{world_dir} is not a directory. Rule: stubs come from the world. Fix: pass the world directory."
    assert work.is_absolute() and work.is_dir(), f"{work} must be an existing absolute directory. Rule: wrappers live in the workspace. Fix: build the workspace first."
    bin_dir = work / BIN_NAME
    bin_dir.mkdir()
    log = work / CALLS_LOG
    log.write_text("")
    for command, output in stub_outputs(world_dir).items():
        wrapper = inside(bin_dir, command)
        wrapper.write_text(wrapper_text(command, output, log))
        wrapper.chmod(WRAPPER_MODE)
    assert log.is_file() and bin_dir.is_dir(), f"the stub wrappers under {work} are incomplete"
    return bin_dir
