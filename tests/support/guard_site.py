import json
from pathlib import Path

from willitharness.detectors import Call
from willitharness.guard import load_rules
from willitharness.plan import KIND_FORBIDDEN, Arm, Detector, Plan, Rule
from willitharness.store import Record, RunState

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"
RULES_FILE = FIXTURES / "guard" / "rules.json"
CORPUS_FILE = FIXTURES / "guard" / "corpus.json"
MESSAGES_FILE = FIXTURES / "rules" / "messages.json"
TASK = "backup"
RUN_COST_USD = 0.01
BLOCKED_COPY = "cp a.json b.json"
COMPLETED = "completed"


def guard_rules():
    return load_rules(RULES_FILE.parent, RULES_FILE.name)


def corpus():
    entries = json.loads(CORPUS_FILE.read_text())
    assert entries, f"{CORPUS_FILE} holds no commands. Fix: restore the corpus."
    return entries


def messages():
    entries = json.loads(MESSAGES_FILE.read_text())
    assert entries, f"{MESSAGES_FILE} holds no messages. Fix: restore the fixed messages."
    return entries


def bash(command):
    assert command, "bash needs a command. Fix: pass the command text."
    return Call("Bash", command)


def write_call(path, tool="Write"):
    assert path, "write_call needs a path. Fix: pass the written path."
    return Call(tool, "", path)


def plan_of(roles, action="cp"):
    assert roles, "plan_of needs roles. Fix: pass a label to role mapping."
    arms = tuple(Arm(label, role, f"{label}.md", "file") for label, role in roles.items())
    rule = Rule("no-cp", "AGENTS.md", "Working", "attempted_violation", Detector(KIND_FORBIDDEN, action), ("command cp -f SOURCE TARGET",))
    return Plan("guard", 2.0, 0.5, 20, 2, "world/", arms, rule)


def usable_guard_run(arm, rep, completed):
    assert rep >= 1, f"rep {rep} starts at 1. Fix: count reps from 1."
    run_id = f"{arm}/{TASK}/{rep}#1"
    return Record(run_id, arm, TASK, rep, 1, RunState.RECORDED_USABLE, {COMPLETED: True}, RUN_COST_USD, {COMPLETED: completed})


def arm_records(arm, completed_count, runs):
    assert 0 <= completed_count <= runs, f"{completed_count} completed of {runs}. Fix: keep completed within runs."
    records = tuple(usable_guard_run(arm, rep, rep <= completed_count) for rep in range(1, runs + 1))
    assert len(records) == runs, f"arm_records built {len(records)} of {runs}"
    return records
