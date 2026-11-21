import os
from dataclasses import replace

from fake_claude import ESCAPE_TARGET_FILE, SECRET_VARIABLE, install_fake_claude
from files import write_tree
from lifecycle_site import SiteSpec, TASK_NAME, ready_site, run_setup

from willitharness.lifecycle import start_running
from willitharness.real_runner import claude_runner
from willitharness.store import Cell

ONE_RUN = SiteSpec(arm_count=1, budget_usd=1.0, run_cap_usd=0.02, reps=1, max_retries=0)
TWO_RUNS = SiteSpec(arm_count=1, budget_usd=1.0, run_cap_usd=0.02, reps=2, max_retries=0)
CELL = Cell("A", TASK_NAME)
OVERLAY_NAME = "A.md"
SECRET_MARKERS = ("KEY", "TOKEN", "SECRET")


def install_fake_agent_environment(tmp_path, monkeypatch):
    for name in [name for name in os.environ if any(marker in name for marker in SECRET_MARKERS)]:
        monkeypatch.delenv(name)
    config = tmp_path / "config"
    config.mkdir()
    bin_dir = install_fake_claude(tmp_path / "bin")
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(config))
    monkeypatch.setenv(SECRET_VARIABLE, "leak")
    assert (bin_dir / "claude").is_file(), f"the fake agent is missing in {bin_dir}"
    return bin_dir


def prepare_project_with_fake_agent(tmp_path, monkeypatch, spec, behavior):
    install_fake_agent_environment(tmp_path, monkeypatch)
    site = ready_site(tmp_path / "project", spec)
    outside = tmp_path / "outside"
    write_tree(site.root, {"A.md/fake-behavior.txt": behavior, "A.md/rule.txt": "the rule text", f"A.md/{ESCAPE_TARGET_FILE}": str(outside / "escaped.txt")})
    outside.mkdir()
    return site


def run_one(site, base=None):
    setup = run_setup(site)
    start_running(site)
    return claude_runner(setup, "haiku", base)(CELL, 1, 1)


def add_overlay_file(site, name, text):
    write_tree(site.root, {f"{OVERLAY_NAME}/{name}": text})
    assert (site.root / OVERLAY_NAME / name).read_text() == text, f"the overlay file {name} was not written"
    return site


def guard_site(site):
    guard = replace(site.plan.arms[0], role="guard_only")
    guarded = replace(site, plan=replace(site.plan, arms=(guard,)))
    assert guarded.plan.arms[0].role == "guard_only", f"the arm is {guarded.plan.arms[0].role}, not guard_only"
    return guarded
