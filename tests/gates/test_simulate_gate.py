import simulate

GOOD = ["--trials", "400", "--n", "20", "--seed", "20261117"]


def test_G4_3_the_calibrated_intervals_pass_the_simulation_gate(capsys):
    code = simulate.main(GOOD)
    out = capsys.readouterr().out
    assert code == 0, f"got {code} {out!r}"
    assert out.splitlines() == ["false-positive rate 0.0425 (at most 0.08)", "power (0.85 against 0.10) 1.0000 (at least 0.95)"], f"got {out!r}"


def test_G4_3_a_wrong_z_of_one_exceeds_the_false_positive_limit_and_exits_one(capsys):
    code = simulate.main([*GOOD, "--z", "1.0"])
    captured = capsys.readouterr()
    assert code == 1, f"got {code} {captured.out!r}"
    assert "false-positive rate 0.2625 (at most 0.08)" in captured.out and "simulation gate failed" in captured.err, f"got {captured}"


def test_G4_3_too_few_runs_per_arm_lose_power_and_exit_one(capsys):
    code = simulate.main(["--trials", "400", "--n", "4", "--seed", "20261117"])
    out = capsys.readouterr().out
    assert code == 1, f"got {code} {out!r}"
    assert "power (0.85 against 0.10) 0.0000" in out, f"got {out!r}"


def test_G4_3_the_same_seed_gives_the_same_report_and_another_seed_gives_another(capsys):
    simulate.main(GOOD)
    first = capsys.readouterr().out
    simulate.main(GOOD)
    repeated = capsys.readouterr().out
    simulate.main([*GOOD[:-1], "7"])
    other = capsys.readouterr().out
    assert first == repeated, f"seeded runs differ: {first!r} against {repeated!r}"
    assert first != other, f"seeds 20261117 and 7 gave one report: {first!r}"
