import atexit
import contextlib
import os
import shutil
import signal
import subprocess
import tempfile
import threading
import time
from dataclasses import dataclass
from pathlib import Path

from willitharness.claude_agent import build_command
from willitharness.isolation import agent_environment, sandbox_profile, sandboxed_command
from willitharness.lifecycle import TIMED_OUT, PlanState, RunSetup, finished, lifecycle_dir, read_state
from willitharness.paths import PathOutsideRoot, inside
from willitharness.plan import PlanError
from willitharness.world import task_commands

POLL_SECONDS = 0.05
RUN_DIRECTORY_PREFIX = "willitharness-run-"
WORK_NAME = "work"
SCRATCH_NAME = "tmp"
TEMP_VARIABLE = "TMPDIR"
CONFIG_VARIABLE = "CLAUDE_CONFIG_DIR"
DEFAULT_CONFIG_NAME = ".claude"
HOME_STATE_NAME = ".claude.json"
UNSUPPORTED_CHANNEL = "system_prompt"
TASK_PROMPT = "Do the task {task}. It uses these commands: {commands}. Reply when it is done."
LIVE_GROUPS = set()
LIVE_LOCK = threading.Lock()


@dataclass(frozen=True)
class AgentRunner:
    setup: RunSetup
    model: str

    def __call__(self, cell, rep, attempt):
        assert rep >= 1 and attempt >= 1, f"rep {rep} and attempt {attempt} start at 1. Rule: run ids count from 1. Fix: claim jobs through claim_next_job."
        assert cell.arm and cell.task, f"cell {cell} lacks an arm or a task. Rule: every run belongs to a cell."
        return run_cell(self, cell)


def check_runnable(setup):
    assert isinstance(setup, RunSetup), f"check_runnable needs a RunSetup, got {setup!r}. Fix: build one with the site, tasks and timeout."
    assert setup.timeout_seconds > 0, f"the timeout is {setup.timeout_seconds}. Rule: every run has a wall-clock limit above 0. Fix: pass a positive limit."
    site = setup.site
    for arm in site.plan.arms:
        if arm.channel == UNSUPPORTED_CHANNEL:
            raise PlanError(
                f"arm {arm.label} uses channel {arm.channel}. Rule: the claude runner delivers an arm as files in the workspace. "
                f"Fix: use another channel for arm {arm.label}."
            )
        try:
            overlay = inside(site.root, arm.overlay)
        except PathOutsideRoot as error:
            raise PlanError(str(error)) from error
        if not overlay.is_dir():
            raise PlanError(f"overlay {overlay} of arm {arm.label} is not a directory. Rule: an arm is an overlay directory. Fix: create the directory the arm names in overlay.")
    assert all(inside(site.root, arm.overlay).is_dir() for arm in site.plan.arms), f"an overlay of plan {site.plan.name} is not a directory"


def claude_runner(setup, model):
    assert model, "claude_runner needs a model. Fix: pass the model name."
    check_runnable(setup)
    runner = AgentRunner(setup, model)
    assert callable(runner), f"claude_runner built {runner!r}, which cannot be called. Rule: the runner is runner(cell, rep, attempt)."
    return runner


def task_prompt(task, commands):
    assert task, "task_prompt needs a task name. Fix: pass a task from tasks.txt."
    assert isinstance(commands, tuple), f"task_prompt needs the commands as a tuple, got {commands!r}. Fix: pass task_commands output."
    prompt = TASK_PROMPT.format(task=task, commands=" ".join(commands))
    assert task in prompt, f"the prompt {prompt!r} lost the task name {task!r}"
    return prompt


def build_workspace(site, arm_label, run_root):
    assert run_root.is_dir(), f"{run_root} is not a directory. Rule: each run gets its own folder. Fix: create it first."
    arms = {arm.label: arm for arm in site.plan.arms}
    assert arm_label in arms, f"{arm_label} is not an arm of plan {site.plan.name}. Rule: a run belongs to a plan arm. Fix: use an arm label."
    work = run_root / WORK_NAME
    shutil.copytree(site.world_dir, work)
    shutil.copytree(inside(site.root, arms[arm_label].overlay), work, dirs_exist_ok=True)
    (run_root / SCRATCH_NAME).mkdir()
    assert work.is_dir() and (run_root / SCRATCH_NAME).is_dir(), f"the workspace under {run_root} is incomplete"
    return work


def agent_config_directory(environ, home):
    assert hasattr(environ, "get"), f"config_directory needs a mapping of variables, got {type(environ).__name__}. Fix: pass os.environ."
    assert home.is_dir(), f"{home} is not a directory. Rule: the agent keeps its settings under home. Fix: pass the user's home."
    configured = environ.get(CONFIG_VARIABLE)
    return Path(configured) if configured else home / DEFAULT_CONFIG_NAME


def writable_extras(run_root, environ, home):
    assert run_root.is_dir(), f"{run_root} is not a directory. Fix: pass the run folder."
    extras = (run_root / SCRATCH_NAME, agent_config_directory(environ, home), home / HOME_STATE_NAME)
    assert all(path.is_absolute() for path in extras), f"an extra writable path is relative: {extras!r}. Fix: use absolute paths."
    return extras


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


def start_agent(command, profile, work, environment):
    assert command and profile, f"start_agent needs a command and a profile, got {command!r} and {profile!r}. Fix: build them first."
    assert work.is_dir(), f"{work} is not a directory. Rule: the agent starts in its workspace. Fix: build the workspace first."
    process = subprocess.Popen(
        sandboxed_command(command, profile),
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


def run_cell(runner, cell):
    assert isinstance(runner, AgentRunner), f"run_cell needs an AgentRunner, got {runner!r}. Fix: build one with claude_runner."
    assert cell.arm and cell.task, f"cell {cell} lacks an arm or a task. Rule: every run belongs to a cell."
    site = runner.setup.site
    home = Path.home()
    prompt = task_prompt(cell.task, task_commands(site.world_dir)[cell.task])
    with tempfile.TemporaryDirectory(prefix=RUN_DIRECTORY_PREFIX) as directory:
        run_root = Path(directory).resolve()
        work = build_workspace(site, cell.arm, run_root)
        profile = sandbox_profile(work, home, writable_extras(run_root, os.environ, home))
        environment = {**agent_environment(os.environ), TEMP_VARIABLE: str(run_root / SCRATCH_NAME)}
        command = build_command(prompt, runner.model, site.plan.run_cap_usd)
        deadline = time.monotonic() + runner.setup.timeout_seconds
        output = watch(start_agent(command, profile, work, environment), deadline, lifecycle_dir(site.root, site.plan))
    return TIMED_OUT if output is None else finished(output.splitlines())
