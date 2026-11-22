import decide_all
from analysis_site import FULL_ROLES, NO_PAIR_ROLES, CellShape, site_with_state
from cli_runner import run_cli

from willitharness.conformance import load_rows
from willitharness.decision import decide
from willitharness.lifecycle import PlanState, lifecycle_dir, read_state, record_reachability
from willitharness.store import Cell
from willitharness.vocabulary import Decision, Reach

STOP = "stop-server"
LOWERS = {Cell("C", STOP): CellShape(20, 17), Cell("C2", STOP): CellShape(20, 16), Cell("B", STOP): CellShape(20, 0)}
NO_EFFECT = {**LOWERS, Cell("B", STOP): CellShape(20, 17)}
RAISES = {**LOWERS, Cell("C", STOP): CellShape(20, 1), Cell("C2", STOP): CellShape(20, 2), Cell("B", STOP): CellShape(20, 18)}
DECIDE = ["decide", "plan.json"]
KEEP_LINE = "decision stop-server B: Keep (reach Loaded, effect RuleLowersViolations, guard GuardUntested)"
RULE_MARKER = "Rule:"
FIX_MARKER = "Fix:"
EXIT_OK = 0
EXIT_REFUSED = 1


def complete_site(tmp_path, monkeypatch, roles, cells):
    site = site_with_state(tmp_path, roles, (cells, PlanState.COMPLETE))
    monkeypatch.chdir(tmp_path)
    assert (tmp_path / "plan.json").is_file(), f"no plan file in {tmp_path}. Fix: site_with_state writes it."
    return site


def test_G5_4_a_rule_that_lowers_violations_with_no_guard_is_kept(tmp_path, monkeypatch, capsys):
    site = complete_site(tmp_path, monkeypatch, FULL_ROLES, LOWERS)
    code, out, err = run_cli(capsys, DECIDE)
    assert code == EXIT_OK and out.splitlines() == [KEEP_LINE], f"got {code} {out!r} {err!r}"
    assert read_state(lifecycle_dir(site.root, site.plan)) is PlanState.COMPLETE, f"Rule: decide reads the plan and never moves its state. Got {read_state(lifecycle_dir(site.root, site.plan))} for {site.plan.name}."


def test_G5_4_a_masked_rule_must_have_its_loading_fixed(tmp_path, monkeypatch, capsys):
    site = site_with_state(tmp_path, FULL_ROLES, (LOWERS, PlanState.COMPLETE))
    record_reachability(site, "B", Reach.MASKED)
    monkeypatch.chdir(tmp_path)
    code, out, err = run_cli(capsys, DECIDE)
    assert code == EXIT_OK and "decision stop-server B: FixLoading (reach Masked" in out, f"got {code} {out!r} {err!r}"


def test_G5_4_a_rule_with_no_measurable_effect_is_a_delete_candidate(tmp_path, monkeypatch, capsys):
    complete_site(tmp_path, monkeypatch, FULL_ROLES, NO_EFFECT)
    code, out, err = run_cli(capsys, DECIDE)
    assert code == EXIT_OK and "decision stop-server B: DeleteCandidate (reach Loaded, effect NoMeasurableEffect" in out, f"got {code} {out!r} {err!r}"


def test_G5_4_a_rule_that_raises_violations_is_a_delete_candidate(tmp_path, monkeypatch, capsys):
    complete_site(tmp_path, monkeypatch, FULL_ROLES, RAISES)
    code, out, err = run_cli(capsys, DECIDE)
    assert code == EXIT_OK and "decision stop-server B: DeleteCandidate (reach Loaded, effect RuleRaisesViolations" in out, f"got {code} {out!r} {err!r}"


def test_G5_4_an_unmeasurable_comparison_cannot_be_decided(tmp_path, monkeypatch, capsys):
    cells = {cell: shape for cell, shape in LOWERS.items() if cell.arm != "C2"}
    complete_site(tmp_path, monkeypatch, NO_PAIR_ROLES, cells)
    code, out, err = run_cli(capsys, DECIDE)
    assert code == EXIT_OK and "decision stop-server B: CannotDecide (reach Loaded, effect Invalid" in out, f"got {code} {out!r} {err!r}"


def test_G5_4_a_plan_that_has_not_run_is_refused_with_rule_and_fix(tmp_path, monkeypatch, capsys):
    site_with_state(tmp_path, FULL_ROLES, (LOWERS, PlanState.REACHABILITY_CHECKED))
    monkeypatch.chdir(tmp_path)
    code, out, err = run_cli(capsys, DECIDE)
    assert code == EXIT_REFUSED and out == "", f"got {code} {out!r} {err!r}"
    assert "plan demo is ReachabilityChecked" in err and RULE_MARKER in err and err.rstrip().endswith("run decide again."), f"got {err!r}"


def test_G5_4_a_plan_with_a_guard_arm_is_refused_with_rule_and_fix(tmp_path, monkeypatch, capsys):
    roles = {**FULL_ROLES, "G": "guard_only"}
    complete_site(tmp_path, monkeypatch, roles, LOWERS)
    code, out, err = run_cli(capsys, DECIDE)
    assert code == EXIT_REFUSED and out == "", f"got {code} {out!r} {err!r}"
    assert "plan demo has a guard_only arm" in err and RULE_MARKER in err and FIX_MARKER in err, f"got {err!r}"


def test_G5_4_a_plan_with_no_rule_arm_is_refused_with_rule_and_fix(tmp_path, monkeypatch, capsys):
    roles = {label: role for label, role in FULL_ROLES.items() if role != "rule"}
    complete_site(tmp_path, monkeypatch, roles, {cell: shape for cell, shape in LOWERS.items() if cell.arm != "B"})
    code, out, err = run_cli(capsys, DECIDE)
    assert code == EXIT_REFUSED and out == "", f"got {code} {out!r} {err!r}"
    assert "plan demo has no leave_one_out arm or no rule arm" in err and RULE_MARKER in err and FIX_MARKER in err, f"got {err!r}"


def test_G5_4_a_missing_plan_file_is_refused_naming_the_file(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    code, out, err = run_cli(capsys, ["decide", "absent.json"])
    assert code == EXIT_REFUSED and out == "" and "absent.json" in err, f"got {code} {out!r} {err!r}"


def test_G5_4_all_45_inputs_equal_the_decision_table(capsys):
    code = decide_all.main(decide)
    captured = capsys.readouterr()
    assert code == EXIT_OK and captured.out == "45 of 45 equal to the decision table\n", f"got {code} {captured}"


def keep_everything(reach, effect, guard):
    return Decision.KEEP


def test_G5_4_a_wrong_decision_function_prints_the_first_mismatch_and_exits_one(capsys):
    first_mismatch = next(row for row in load_rows("decision") if row["decision"] != Decision.KEEP)
    code = decide_all.main(keep_everything)
    captured = capsys.readouterr()
    assert code == EXIT_REFUSED and captured.out == "", f"got {code} {captured}"
    assert captured.err.count("\n") == 1 and f"lean={first_mismatch['decision']}" in captured.err, f"got {captured.err!r}"


def test_G5_4_the_real_decision_function_has_no_mismatch(capsys):
    assert decide_all.main(decide) == EXIT_OK, f"got {capsys.readouterr()}"
