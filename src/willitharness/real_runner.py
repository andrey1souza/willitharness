import atexit
import contextlib
import json
import os
import signal
import subprocess
import tempfile
import threading
import time
from dataclasses import dataclass, replace
from pathlib import Path

from willitharness.artifacts import RunArtifacts, artifact_directory, store_artifacts
from willitharness.claude_agent import build_command, claude_version, tool_policy
from willitharness.claude_sandbox import NO_DOMAINS, sandbox_settings
from willitharness.isolation import agent_environment, sandbox_profile, sandboxed_command
from willitharness.lifecycle import TIMED_OUT, PlanState, RunSetup, finished, lifecycle_dir, read_state
from willitharness.paths import PathOutsideRoot, inside
from willitharness.plan import PlanError, has_guard_arm
from willitharness.stubs import calls_path, copy_without_reserved, scratch_path, stub_folder, write_stub_wrappers
from willitharness.world import allowed_commands, prompt_text

POLL_SECONDS = 0.05
RUN_DIRECTORY_PREFIX = "willitharness-run-"
WORK_NAME = "work"
TEMP_VARIABLE = "TMPDIR"
CLAUDE_TEMP_VARIABLE = "CLAUDE_CODE_TMPDIR"
CONFIG_VARIABLE = "CLAUDE_CONFIG_DIR"
DEFAULT_CONFIG_NAME = ".claude"
HOME_STATE_NAME = ".claude.json"
UNSUPPORTED_CHANNEL = "system_prompt"
CHANNEL_TASK = "T64"
INSTRUCTION_FILES = ("CLAUDE.md", "AGENTS.md")
INSTRUCTION_DIRECTORY = ".claude"
AGENT_RECORD = "agent.json"
VERSION_KEY = "claude_version"
PATH_VARIABLE = "PATH"
LIVE_GROUPS = set()
LIVE_LOCK = threading.Lock()


@dataclass(frozen=True)
class AgentRunner:
    setup: RunSetup
    model: str
    base: Path | None = None

    def __call__(self, cell, rep, attempt):
        assert rep >= 1 and attempt >= 1, f"rep {rep} and attempt {attempt} start at 1. Rule: run ids count from 1. Fix: claim jobs through claim_next_job."
        assert cell.arm and cell.task, f"cell {cell} lacks an arm or a task. Rule: every run belongs to a cell."
        return run_cell(self, cell, rep, attempt)


@dataclass(frozen=True)
class RunKey:
    cell: object
    rep: int
    attempt: int


def check_channels(plan):
    assert plan.arms, f"plan {plan.name} has no arms. Rule: a plan needs arms. Fix: load the plan with load_plan."
    assert UNSUPPORTED_CHANNEL, "the unsupported channel name is empty. Fix: restore the constant."
    for arm in plan.arms:
        if arm.channel == UNSUPPORTED_CHANNEL:
            raise PlanError(
                f"arm {arm.label} uses channel {arm.channel}. Rule: the claude runner delivers an arm as files in the workspace; "
                f"the {arm.channel} channel is backlog task {CHANNEL_TASK}. Fix: use another channel for arm {arm.label}."
            )


def workspace_base(base):
    assert base is None or isinstance(base, Path), f"workspace_base needs a Path or None, got {base!r}. Fix: pass a pathlib.Path."
    resolved = Path(tempfile.gettempdir()).resolve() if base is None else base.resolve()
    assert resolved.is_absolute(), f"the workspace base {resolved} is not absolute"
    return resolved


def instruction_holder(directory):
    assert directory.is_absolute(), f"{directory} is not absolute. Rule: ancestors are read from a resolved path. Fix: resolve it first."
    assert directory.is_dir(), f"{directory} is not a directory. Rule: a workspace sits under a real folder. Fix: create it."
    for ancestor in (directory, *directory.parents):
        for name in INSTRUCTION_FILES:
            if (ancestor / name).is_file():
                return ancestor / name
        if (ancestor / INSTRUCTION_DIRECTORY).is_dir():
            return ancestor / INSTRUCTION_DIRECTORY
    return None


def check_ancestors(base):
    assert base.is_absolute(), f"{base} is not absolute. Fix: pass workspace_base output."
    holder = instruction_holder(base)
    if holder is not None:
        raise PlanError(
            f"{holder} sits above the run workspaces under {base}. "
            f"Rule: an instruction file in an ancestor of the workspace reaches the agent and masks the arm. "
            f"Fix: set TMPDIR to a folder whose ancestors hold no {', '.join(INSTRUCTION_FILES)} or {INSTRUCTION_DIRECTORY}."
        )
    assert holder is None, f"{holder} was found but not refused"


def check_runnable(setup, base):
    assert isinstance(setup, RunSetup), f"check_runnable needs a RunSetup, got {setup!r}. Fix: build one with the site, tasks and timeout."
    assert setup.timeout_seconds > 0, f"the timeout is {setup.timeout_seconds}. Rule: every run has a wall-clock limit above 0. Fix: pass a positive limit."
    site = setup.site
    check_channels(site.plan)
    check_ancestors(workspace_base(base))
    for arm in site.plan.arms:
        try:
            overlay = inside(site.root, arm.overlay)
        except PathOutsideRoot as error:
            raise PlanError(str(error)) from error
        if not overlay.is_dir():
            raise PlanError(f"overlay {overlay} of arm {arm.label} is not a directory. Rule: an arm is an overlay directory. Fix: create the directory the arm names in overlay.")
    assert all(inside(site.root, arm.overlay).is_dir() for arm in site.plan.arms), f"an overlay of plan {site.plan.name} is not a directory"


def record_agent_version(site, version):
    assert version, "record_agent_version needs a version. Fix: pass claude_version output."
    folder = lifecycle_dir(site.root, site.plan)
    record = folder / AGENT_RECORD
    record.write_text(json.dumps({VERSION_KEY: version}))
    assert json.loads(record.read_text())[VERSION_KEY] == version, f"{record} did not keep {version!r}"
    return record


def claude_runner(setup, model, base=None):
    assert model, "claude_runner needs a model. Fix: pass the model name."
    check_runnable(setup, base)
    record_agent_version(setup.site, claude_version())
    runner = AgentRunner(setup, model, base)
    assert callable(runner), f"claude_runner built {runner!r}, which cannot be called. Rule: the runner is runner(cell, rep, attempt)."
    return runner


def build_workspace(site, arm_label, run_root):
    assert run_root.is_dir(), f"{run_root} is not a directory. Rule: each run gets its own folder. Fix: create it first."
    arms = {arm.label: arm for arm in site.plan.arms}
    assert arm_label in arms, f"{arm_label} is not an arm of plan {site.plan.name}. Rule: a run belongs to a plan arm. Fix: use an arm label."
    work = run_root / WORK_NAME
    copy_without_reserved(site.world_dir, work)
    copy_without_reserved(inside(site.root, arms[arm_label].overlay), work)
    write_stub_wrappers(site.world_dir, run_root)
    scratch_path(run_root).mkdir()
    assert work.is_dir() and scratch_path(run_root).is_dir(), f"the workspace under {run_root} is incomplete"
    return work


def agent_config_directory(environ, home):
    assert hasattr(environ, "get"), f"config_directory needs a mapping of variables, got {type(environ).__name__}. Fix: pass os.environ."
    assert home.is_dir(), f"{home} is not a directory. Rule: the agent keeps its settings under home. Fix: pass the user's home."
    configured = environ.get(CONFIG_VARIABLE)
    return Path(configured) if configured else home / DEFAULT_CONFIG_NAME


def writable_extras(run_root, environ, home):
    assert run_root.is_dir(), f"{run_root} is not a directory. Fix: pass the run folder."
    extras = (scratch_path(run_root), calls_path(run_root), agent_config_directory(environ, home), home / HOME_STATE_NAME)
    assert all(path.is_absolute() for path in extras), f"an extra writable path is relative: {extras!r}. Fix: use absolute paths."
    return extras


def run_sandbox(guarded, work, run_root, home):
    assert work.is_dir() and run_root.is_dir(), f"{work} or {run_root} is not a directory. Fix: build the workspace first."
    assert home.is_dir(), f"{home} is not a directory. Rule: the sandbox hides secret folders under home. Fix: pass the user's home."
    profile = sandbox_profile(work, home, writable_extras(run_root, os.environ, home)) if guarded else None
    settings = "" if guarded else sandbox_settings(work, run_root, home, NO_DOMAINS)
    assert (profile is None) != (settings == ""), f"a run needs exactly one sandbox, got profile {profile!r} and settings {settings!r}. Rule: guard runs use sandbox-exec, effect runs use the Claude sandbox."
    return profile, settings


def kill_group(process):
    assert process.pid > 0, f"the process has pid {process.pid}. Rule: only a started process is killed."
    assert process.args, "the process has no command. Rule: only a started process is killed."
    with contextlib.suppress(ProcessLookupError):
        os.killpg(process.pid, signal.SIGKILL)


def kill_every_live_group():
    with LIVE_LOCK:
        groups = tuple(LIVE_GROUPS)
    assert all(group > 0 for group in groups), f"a live group id is not positive: {groups!r}"
    for group in groups:
        with contextlib.suppress(ProcessLookupError):
            os.killpg(group, signal.SIGKILL)
    assert isinstance(groups, tuple), f"the live groups are {groups!r}, not a tuple"


atexit.register(kill_every_live_group)


def agent_argv(command, profile):
    assert command, "agent_argv needs a command. Fix: pass the claude command."
    argv = command if profile is None else sandboxed_command(command, profile)
    assert argv[-len(command):] == command, f"agent_argv changed the claude command: {argv!r}. Rule: the wrapper only goes in front."
    return argv


def start_agent(command, profile, work, environment):
    assert command, f"start_agent needs a command, got {command!r}. Fix: build it first."
    assert work.is_dir(), f"{work} is not a directory. Rule: the agent starts in its workspace. Fix: build the workspace first."
    process = subprocess.Popen(
        agent_argv(command, profile),
        cwd=work,
        env=environment,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        start_new_session=True,
    )
    with LIVE_LOCK:
        LIVE_GROUPS.add(process.pid)
    assert process.pid in LIVE_GROUPS, f"process {process.pid} was not tracked. Rule: abort and exit kill every live agent."
    return process


def watch(process, deadline, folder):
    assert deadline > 0, f"the deadline is {deadline}. Rule: a deadline is a monotonic clock reading. Fix: use time.monotonic() plus the timeout."
    assert folder.is_dir(), f"{folder} is not a directory. Rule: the plan state is read from the plan folder. Fix: use lifecycle_dir."
    try:
        while time.monotonic() < deadline and read_state(folder) is PlanState.RUNNING:
            try:
                output, _ = process.communicate(timeout=POLL_SECONDS)
                return output
            except subprocess.TimeoutExpired:
                continue
        kill_group(process)
        process.communicate()
        return None
    finally:
        with LIVE_LOCK:
            LIVE_GROUPS.discard(process.pid)


def run_environment(run_root, environ):
    assert run_root.is_dir(), f"{run_root} is not a directory. Fix: build the workspace first."
    assert stub_folder(run_root).is_dir(), f"{stub_folder(run_root)} is not a directory. Rule: the wrappers exist before the run starts. Fix: write them first."
    scrubbed = agent_environment(environ)
    path = os.pathsep.join([str(stub_folder(run_root)), scrubbed[PATH_VARIABLE]])
    scratch = str(scratch_path(run_root))
    environment = {**scrubbed, PATH_VARIABLE: path, TEMP_VARIABLE: scratch, CLAUDE_TEMP_VARIABLE: scratch}
    assert environment[PATH_VARIABLE].startswith(str(stub_folder(run_root))), f"the stub folder is not first on PATH: {environment[PATH_VARIABLE]!r}"
    return environment


def calls_text(run_root):
    assert run_root.is_dir(), f"{run_root} is not a directory. Fix: pass the run folder."
    log = calls_path(run_root)
    text = log.read_text() if log.is_file() else ""
    assert isinstance(text, str), f"the calls log of {run_root} is not text"
    return text


def keep_run(site, key, artifacts, environment):
    assert isinstance(key, RunKey), f"keep_run needs a RunKey, got {key!r}. Fix: build one from the cell, rep and attempt."
    assert isinstance(artifacts, RunArtifacts), f"keep_run needs RunArtifacts, got {artifacts!r}. Fix: build them from the transcript and calls log."
    folder = artifact_directory(site.root, site.plan.name, key.cell, key.rep)
    return store_artifacts(folder, key.attempt, artifacts, environment)


def run_cell(runner, cell, rep, attempt):
    assert isinstance(runner, AgentRunner), f"run_cell needs an AgentRunner, got {runner!r}. Fix: build one with claude_runner."
    assert cell.arm and cell.task, f"cell {cell} lacks an arm or a task. Rule: every run belongs to a cell."
    site = runner.setup.site
    home = Path.home()
    prompt = prompt_text(site.world_dir, cell.task)
    guarded = has_guard_arm(site.plan)
    policy = tool_policy(guarded, allowed_commands(site.world_dir))
    with tempfile.TemporaryDirectory(prefix=RUN_DIRECTORY_PREFIX, dir=runner.base) as directory:
        run_root = Path(directory).resolve()
        work = build_workspace(site, cell.arm, run_root)
        profile, settings = run_sandbox(guarded, work, run_root, home)
        environment = run_environment(run_root, os.environ)
        command = build_command(prompt, runner.model, site.plan.run_cap_usd, replace(policy, settings=settings))
        deadline = time.monotonic() + runner.setup.timeout_seconds
        output = watch(start_agent(command, profile, work, environment), deadline, lifecycle_dir(site.root, site.plan))
        calls = calls_text(run_root)
        keep_run(site, RunKey(cell, rep, attempt), RunArtifacts(output or "", calls), environment)
    return TIMED_OUT if output is None else finished(output.splitlines(), calls)
