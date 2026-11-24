from cli_runner import run_cli
from guard_decide_site import EQUIVALENT_COMMAND, LISTING_COMMAND, VIOLATING_COMMAND, GuardEvidence, every_rep, guard_site_with_runs, remove_transcript

from willitharness.lifecycle import PlanState

DECIDE = ["decide", "plan.json"]
EXIT_OK = 0
REPLACE_LINE = "decision stop-server B: ReplaceWithGuard (reach Loaded, effect RuleLowersViolations, guard GuardMatchesRule)"
KEEP_UNTESTED_LINE = "decision stop-server B: Keep (reach Loaded, effect RuleLowersViolations, guard GuardUntested)"
KEEP_WORSE_LINE = "decision stop-server B: Keep (reach Loaded, effect RuleLowersViolations, guard GuardWorse)"
BLOCKED_THEN_LISTING = [VIOLATING_COMMAND, LISTING_COMMAND]
BLOCKED_THEN_BYPASS = [VIOLATING_COMMAND, EQUIVALENT_COMMAND]
ONE_BYPASSING_REP = 7


def decide_in(tmp_path, monkeypatch, capsys, evidence):
    guard_site_with_runs(tmp_path, evidence)
    monkeypatch.chdir(tmp_path)
    return run_cli(capsys, DECIDE)


def test_G1_4_a_guard_that_blocks_every_violation_and_completes_as_often_replaces_the_rule(tmp_path, monkeypatch, capsys):
    code, out, err = decide_in(tmp_path, monkeypatch, capsys, GuardEvidence(every_rep(BLOCKED_THEN_LISTING)))
    assert code == EXIT_OK and out.splitlines() == [REPLACE_LINE], f"got {code} {out!r} {err!r}"


def test_G1_4_a_guard_that_lets_the_agent_go_round_the_block_is_worse_and_the_rule_is_kept(tmp_path, monkeypatch, capsys):
    code, out, err = decide_in(tmp_path, monkeypatch, capsys, GuardEvidence(every_rep(BLOCKED_THEN_BYPASS)))
    assert code == EXIT_OK and out.splitlines() == [KEEP_WORSE_LINE], f"got {code} {out!r} {err!r}"


def test_G1_4_one_run_that_goes_round_the_block_makes_the_guard_worse(tmp_path, monkeypatch, capsys):
    mixed = {**every_rep(BLOCKED_THEN_LISTING), ONE_BYPASSING_REP: BLOCKED_THEN_BYPASS}
    code, out, err = decide_in(tmp_path, monkeypatch, capsys, GuardEvidence(mixed))
    assert code == EXIT_OK and out.splitlines() == [KEEP_WORSE_LINE], f"got {code} {out!r} {err!r}"


def test_G1_4_a_guard_arm_with_no_stored_calls_is_untested(tmp_path, monkeypatch, capsys):
    code, out, err = decide_in(tmp_path, monkeypatch, capsys, GuardEvidence({}))
    assert code == EXIT_OK and out.splitlines() == [KEEP_UNTESTED_LINE], f"got {code} {out!r} {err!r}"


def test_G1_4_a_guard_arm_with_calls_missing_for_one_run_is_untested(tmp_path, monkeypatch, capsys):
    site = guard_site_with_runs(tmp_path, GuardEvidence(every_rep(BLOCKED_THEN_LISTING)))
    monkeypatch.chdir(tmp_path)
    remove_transcript(site, ONE_BYPASSING_REP)
    code, out, err = run_cli(capsys, DECIDE)
    assert code == EXIT_OK and out.splitlines() == [KEEP_UNTESTED_LINE], f"got {code} {out!r} {err!r}"


def test_G1_4_a_guard_arm_with_no_rules_file_is_untested(tmp_path, monkeypatch, capsys):
    code, out, err = decide_in(tmp_path, monkeypatch, capsys, GuardEvidence(every_rep(BLOCKED_THEN_LISTING), with_rules=False))
    assert code == EXIT_OK and out.splitlines() == [KEEP_UNTESTED_LINE], f"got {code} {out!r} {err!r}"


def test_G1_4_the_report_names_the_guard_result_read_from_the_guard_arm(tmp_path, monkeypatch, capsys):
    guard_site_with_runs(tmp_path, GuardEvidence(every_rep(BLOCKED_THEN_LISTING), state=PlanState.ANALYZED))
    monkeypatch.chdir(tmp_path)
    code, out, err = run_cli(capsys, ["report", "plan.json"])
    assert code == EXIT_OK and "Guard: GuardMatchesRule." in out and "ReplaceWithGuard" in out, f"got {code} {out!r} {err!r}"
