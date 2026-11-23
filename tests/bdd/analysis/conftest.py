from dataclasses import replace

import pytest
from analysis_site import COMPLETED, FULL_ROLES, LOO_LABEL, TARGET, filled_cells, TASK, TWO_TASK_CELLS, site_with_state
from cli_runner import run_cli
from pytest_bdd import parsers, then, when

from willitharness.analysis import PlanFacts, analyze_effect
from willitharness.counts import Counts
from willitharness.lifecycle import PlanState
from willitharness.store import Cell
from willitharness.verdict import verdict_of
from willitharness.vocabulary import Reach


@pytest.fixture
def world():
    return {"roles": FULL_ROLES, "cells": {}, "pooled": False, "models": {}}


def analyze_with_given_noise(world):
    assert world["given_noise"], "the scenario names a noise status. Fix: give one before analyzing."
    verdict = verdict_of(Counts(1, world["few"]), Counts(0, world["few"]))
    world["effect"] = analyze_effect(PlanFacts(True, world["given_noise"], Reach.LOADED, Reach.LOADED), verdict, LOO_LABEL)
    assert world["effect"].message is None or world["effect"].verdict is None, f"got {world['effect']}"


@when("I analyze the plan")
def analyze_the_plan(world, tmp_path, monkeypatch, capsys):
    if "given_noise" in world:
        return analyze_with_given_noise(world)
    cells = filled_cells(world["roles"], world["cells"])
    cells = {cell: replace(shape, model=world["models"].get(cell.arm, shape.model)) for cell, shape in cells.items()}
    site_with_state(tmp_path, world["roles"], (cells, PlanState.COMPLETE))
    monkeypatch.chdir(tmp_path)
    arguments = ["analyze", "plan.json", *(["--pooled"] if world["pooled"] else [])]
    world["exit_code"], out, world["message"] = run_cli(capsys, arguments)
    world["report"] = out + world["message"]
    world["lines"] = out.splitlines()
    assert world["exit_code"] in (0, 1), f"analyze exits 0 or 1, got {world['exit_code']}; {world['message']!r}"


@when(parsers.re('I request a pooled verdict( over two tasks)?'))
def request_pooled_verdict(world, tmp_path, monkeypatch, capsys):
    world["cells"] = world["cells"] or dict(TWO_TASK_CELLS)
    world["pooled"] = True
    analyze_the_plan(world, tmp_path, monkeypatch, capsys)


def lines_of(world, outcome):
    found = [line for line in world["lines"] if line.startswith(f"{outcome} ")]
    assert found, f"the report has no {outcome} line: {world['lines']}"
    return found


@then(parsers.parse('the noise status is "{name}"'))
def noise_status_is(world, name):
    assert any(f"noise {name}" in line for line in lines_of(world, TARGET)), f"expected the {TARGET} line to show noise {name}. Fix: check the noise pair counts; got {lines_of(world, TARGET)}"


@then(parsers.parse('the report says "{text}"'))
def report_says(world, text):
    assert text in world["report"], f"expected the report to say {text!r}, got {world['report']!r}"


@then(parsers.parse('the warning "{name}" is shown'))
def warning_is_shown(world, name):
    assert any(line.startswith(name) for line in world["lines"]), f"expected a {name} warning, got {world['lines']}"


@then(parsers.parse('the warning "{name}" is not shown'))
@then(parsers.parse('the warning "{name}" is absent'))
def warning_is_not_shown(world, name):
    assert not any(line.startswith(name) for line in world["lines"]), f"expected no {name} warning, got {world['lines']}"


@then(parsers.parse('the verdict is labeled "{label}"'))
def verdict_is_labeled(world, label):
    assert any(f"[{label}]" in line for line in lines_of(world, TARGET)), f"expected the label {label}, got {lines_of(world, TARGET)}"
