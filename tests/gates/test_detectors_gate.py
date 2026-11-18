import json
import sys

import pytest
from agent_site import install_fake_agent_environment
from cli_runner import run_cli
from files import write_tree
from lifecycle_site import SCHEMA_VERSION, TASK_NAME, TASK_PROMPT, WORLD_NAME, reach_every_arm, validate_site

from willitharness.lifecycle import PlanSite, lifecycle_dir
from willitharness.plan import load_plan
from willitharness.store import RunState, latest_by_run, load_records
from willitharness.vocabulary import Reach

pytestmark = pytest.mark.skipif(sys.platform != "darwin", reason="the real runner uses macOS sandbox-exec")
REPS = 5
VIOLATING_COMMAND = "pkill -f server"
OBEYING_COMMAND = "killall server"
ARM_COMMANDS = {"C": VIOLATING_COMMAND, "C2": VIOLATING_COMMAND, "B": OBEYING_COMMAND}
ARM_ROLES = {"C": "leave_one_out", "C2": "noise_of:C", "B": "rule"}
RULE = {"id": "no-pkill", "file": "AGENTS.md", "section": "Working", "target_outcome": "attempted_violation", "detector": "pkill", "offered_alternatives": ["killall NAME"]}
TASKS = [{"id": TASK_NAME, "completed_check": {"kind": "calls_contain", "command": "killall"}}]
RUN_ARGUMENTS = ["run", "plan.json", "--agent", "claude"]
ANALYZE_ARGUMENTS = ["analyze", "plan.json"]


def build_site(root, with_rule):
    arms = [{"label": label, "role": role, "overlay": f"{label}.md"} for label, role in ARM_ROLES.items()]
    data = {"schema": SCHEMA_VERSION, "name": "demo", "world": WORLD_NAME, "budget_usd": 1.0, "run_cap_usd": 0.02, "reps": REPS, "max_retries": 0, "arms": arms}
    if with_rule:
        data = {**data, "rule": RULE, "tasks": TASKS}
    files = {
        "plan.json": json.dumps(data),
        f"{WORLD_NAME}/tasks.txt": f"{TASK_NAME}: pkill killall\n",
        f"{WORLD_NAME}/stubs/pkill/output.txt": "stub-pkill\n",
        f"{WORLD_NAME}/stubs/killall/output.txt": "stub-killall\n",
        f"{WORLD_NAME}/prompts/{TASK_NAME}.txt": TASK_PROMPT,
    }
    for label, command in ARM_COMMANDS.items():
        files[f"{label}.md/fake-behavior.txt"] = "ok tools"
        files[f"{label}.md/fake-commands.txt"] = command
    write_tree(root, files)
    site = PlanSite(root, load_plan(data), root / WORLD_NAME)
    validate_site(site)
    reach_every_arm(site, Reach.LOADED)
    return site


def run_and_analyze(tmp_path, monkeypatch, capsys, with_rule):
    install_fake_agent_environment(tmp_path, monkeypatch)
    site = build_site(tmp_path / "project", with_rule)
    monkeypatch.chdir(site.root)
    run_code, _, run_err = run_cli(capsys, RUN_ARGUMENTS)
    assert run_code == 0, f"the run failed with {run_code}: {run_err!r}"
    records = tuple(latest_by_run(load_records(lifecycle_dir(site.root, site.plan))).values())
    return records, run_cli(capsys, ANALYZE_ARGUMENTS)


def test_G4_4_the_claude_run_stores_the_judged_outcome_and_analyze_prints_the_verdict_row(tmp_path, monkeypatch, capsys):
    records, (code, out, err) = run_and_analyze(tmp_path, monkeypatch, capsys, True)
    lines = out.splitlines()
    assert all(run.state is RunState.RECORDED_USABLE for run in records) and len(records) == 3 * REPS, f"expected {3 * REPS} usable runs, got {records}"
    by_arm = {run.arm: run.outcome for run in records}
    assert by_arm["C"] == {"attempted_violation": True, "executed": 1, "completed": False}, f"the LOO outcome was {by_arm['C']}"
    assert by_arm["B"] == {"attempted_violation": False, "executed": 0, "completed": True}, f"the rule outcome was {by_arm['B']}"
    assert code == 0, f"analyze failed with {code}: {err!r}"
    assert "attempted_violation stop-server C 5/5 against B 0/5: verdict FirstHigher; noise NoiseOk; effect RuleLowersViolations" in lines, f"got {lines}"
    assert "completed stop-server C 0/5 against B 5/5: verdict FirstLower; noise NoiseOk" in lines, f"got {lines}"


def test_G4_4_a_plan_without_a_rule_stores_no_outcome_and_analyze_stops_with_a_fix(tmp_path, monkeypatch, capsys):
    records, (code, _, err) = run_and_analyze(tmp_path, monkeypatch, capsys, False)
    assert all(run.outcome == {} for run in records), f"a plan without a rule must store no outcome, got {records}"
    assert code == 1 and "stores no value for it" in err and "Fix:" in err, f"analyze must stop with a fix, got {code} {err!r}"
