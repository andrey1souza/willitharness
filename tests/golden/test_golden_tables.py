import pytest

from willitharness.conformance import (
    GOLDEN_DIRECTORY,
    decision_mismatches,
    effect_mismatches,
    guard_mismatches,
    load_rows,
    main,
    probe_mismatches,
    reported_mismatches,
)
from willitharness.analysis import PlanFacts, can_report
from willitharness.decision import decide
from willitharness.effect import map_effect
from willitharness.guard import evaluate
from willitharness.probe import classify
from willitharness.vocabulary import Decision, EffectResult, NoiseStatus, Reach

ROW_COUNT_BY_KIND = {"decision": 45, "effect": 12, "probe": 140, "guard": 30, "reported": 54}
USAGE_EXIT_CODE = 2
SUCCESS_EXIT_CODE = 0
TABLE_FILE_NAMES = ["decision_table.json", "effect_table.json", "guard_table.json", "probe_table.json", "reported_table.json"]


def wrong_decide_masked_keeps(reach, effect, guard):
    return Decision.KEEP if reach is Reach.MASKED else decide(reach, effect, guard)


def wrong_effect_unmeasured_is_ok(noise, verdict):
    adjusted = NoiseStatus.NOISE_OK if noise is NoiseStatus.NOISE_UNMEASURED else noise
    return map_effect(adjusted, verdict)


def wrong_classify_ignores_control(runs, target_hits, control_hits):
    return classify(runs, target_hits, 0)


def wrong_evaluate_ignores_bypass(completed, coverage, zero_bypass):
    return evaluate(completed, coverage, True)


def wrong_can_report_ignores_noise(facts):
    return can_report(PlanFacts(facts.has_noise_pair, NoiseStatus.NOISE_OK, facts.loo_probe, facts.rule_reach))


@pytest.mark.parametrize(("kind", "count"), ROW_COUNT_BY_KIND.items())
def test_golden_table_has_the_expected_row_count(kind, count):
    rows = len(load_rows(kind))
    assert rows == count, f"{kind=} {rows=} expected {count=}"


def test_D1_to_D12_decision_table_conforms():
    found = decision_mismatches(load_rows("decision"))
    assert found == [], f"{found=}"


def test_E1_effect_table_conforms():
    found = effect_mismatches(load_rows("effect"))
    assert found == [], f"{found=}"


def test_P1_to_P4_probe_table_conforms():
    found = probe_mismatches(load_rows("probe"))
    assert found == [], f"{found=}"


def test_G1_guard_table_conforms():
    found = guard_mismatches(load_rows("guard"))
    assert found == [], f"{found=}"


def test_L8_reported_table_conforms():
    found = reported_mismatches(load_rows("reported"))
    assert found == [], f"{found=}"


def test_proof_it_can_fail_V6_reporting_despite_a_noise_problem_is_detected():
    found = reported_mismatches(load_rows("reported"), wrong_can_report_ignores_noise)
    assert found != [], f"{found=} for a report gate that ignores the noise status"


def test_proof_it_can_fail_D1_masked_keeps_is_detected():
    found = decision_mismatches(load_rows("decision"), wrong_decide_masked_keeps)
    assert found != [], f"{found=} for a table that keeps masked rules"


def test_proof_it_can_fail_V6_unmeasured_noise_as_ok_is_detected():
    found = effect_mismatches(load_rows("effect"), wrong_effect_unmeasured_is_ok)
    assert found != [], f"{found=} for an effect map that trusts unmeasured noise"


def test_proof_it_can_fail_P2_ignoring_the_control_token_is_detected():
    found = probe_mismatches(load_rows("probe"), wrong_classify_ignores_control)
    assert found != [], f"{found=} for a probe that ignores the control token"


def test_proof_it_can_fail_G1_ignoring_bypass_is_detected():
    found = guard_mismatches(load_rows("guard"), wrong_evaluate_ignores_bypass)
    assert found != [], f"{found=} for a guard check that ignores bypass"


def test_proof_it_can_fail_a_changed_table_row_is_detected():
    rows = load_rows("decision")
    rows[0] = {**rows[0], "decision": Decision.CANNOT_DECIDE.value}
    found = decision_mismatches(rows)
    assert len(found) == 1, f"{found=} for one changed row"


@pytest.mark.parametrize("kind", ROW_COUNT_BY_KIND)
def test_conformance_command_reports_the_case_count(kind, capsys):
    code = main([kind])
    printed = capsys.readouterr().out
    assert code == SUCCESS_EXIT_CODE, f"{code=} for {kind=}"
    assert printed == f"{kind} table conforms: {ROW_COUNT_BY_KIND[kind]} cases\n", f"{printed=}"


def test_conformance_command_rejects_an_unknown_kind(capsys):
    code = main(["unknown"])
    printed = capsys.readouterr().err
    assert code == USAGE_EXIT_CODE, f"{code=} for an unknown kind"
    assert "usage: conformance" in printed, f"{printed=}"


def test_golden_directory_holds_the_four_tables():
    names = sorted(path.name for path in GOLDEN_DIRECTORY.glob("*_table.json"))
    assert names == TABLE_FILE_NAMES, f"{names=} in {GOLDEN_DIRECTORY}"


def test_effect_rows_use_known_spellings():
    spellings = {row["effect"] for row in load_rows("effect")}
    known = {result.value for result in EffectResult}
    assert spellings <= known, f"{spellings - known=}"
