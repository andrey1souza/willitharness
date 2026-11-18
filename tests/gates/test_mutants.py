from pathlib import Path

import pytest

import mutants
from mutant_tables import MODULES

REPO_ROOT = Path(__file__).resolve().parents[2]
STATS_MUTANT_COUNT = 8
FAILING_TEST = "def test_always_fails():\n    assert False, 'planted failure'\n"


def stats_mutants():
    return MODULES["stats"][1]


def test_the_stats_module_lists_eight_mutants_with_distinct_names():
    names = [mutant[0] for mutant in stats_mutants()]
    assert len(names) == STATS_MUTANT_COUNT, f"expected {STATS_MUTANT_COUNT} stats mutants, got {names}"
    assert len(set(names)) == len(names), f"mutant names must be distinct, got {names}"


def test_every_stats_target_occurs_exactly_once_and_changes_the_text():
    for name, relative_path, old, new in stats_mutants():
        text = (REPO_ROOT / relative_path).read_text()
        assert text.count(old) == 1, f"mutant {name}: target occurs {text.count(old)} times in {relative_path}"
        assert old != new, f"mutant {name}: the replacement equals the target"


def test_an_ambiguous_target_is_rejected():
    with pytest.raises(AssertionError) as raised:
        mutants.mutated_text("a = 1\nb = 1\n", "1", "2")
    assert "occurs 2 times" in str(raised.value), f"unexpected message {str(raised.value)!r}"


def test_a_missing_target_is_rejected():
    with pytest.raises(AssertionError) as raised:
        mutants.mutated_text("a = 1\n", "7", "2")
    assert "occurs 0 times" in str(raised.value), f"unexpected message {str(raised.value)!r}"


def test_a_unique_target_is_replaced():
    result = mutants.mutated_text("a = 1\nb = 2\n", "a = 1", "a = 3")
    assert result == "a = 3\nb = 2\n", f"unexpected text {result!r}"


def test_an_empty_tests_directory_kills_nothing_and_fails_the_gate(tmp_path, capsys):
    code = mutants.main(["stats", "--tests", str(tmp_path)])
    output = capsys.readouterr().out
    assert code == mutants.EXIT_SURVIVED, f"expected exit {mutants.EXIT_SURVIVED}, got {code}; output {output!r}"
    assert "mutants killed: 0/%d" % STATS_MUTANT_COUNT in output, f"unexpected output {output!r}"


def test_tests_that_fail_on_unmutated_code_stop_the_gate(tmp_path, capsys):
    (tmp_path / "test_planted.py").write_text(FAILING_TEST)
    code = mutants.main(["stats", "--tests", str(tmp_path)])
    output = capsys.readouterr().out
    assert code == mutants.EXIT_BASELINE_BROKEN, f"expected exit {mutants.EXIT_BASELINE_BROKEN}, got {code}"
    assert "mutants killed" not in output, f"no mutant may run on a broken baseline, got {output!r}"
