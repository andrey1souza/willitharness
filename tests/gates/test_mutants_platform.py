import mutants
from mutant_tables import MODULES


DARWIN_ONLY_MODULES = ["artifacts", "claude", "detectors", "isolation", "pilot_live", "real_runner", "run_live", "stubs"]


def test_off_darwin_the_darwin_only_modules_are_skipped_and_the_rest_are_not():
    names = sorted(MODULES)
    assert mutants.skipped_modules(names, "linux") == DARWIN_ONLY_MODULES, "every darwin-only module must be skipped on linux"
    assert mutants.skipped_modules(names, "darwin") == [], "nothing may be skipped on darwin"


def test_a_skipped_module_prints_the_reason_and_exits_zero(capsys):
    code = mutants.main(["claude"], "linux")
    output = capsys.readouterr().out
    assert code == mutants.EXIT_ALL_KILLED, f"a skipped module must exit {mutants.EXIT_ALL_KILLED}, got {code}"
    assert output == "skipped claude: needs darwin\n", f"unexpected output {output!r}"


def test_the_closing_line_lists_every_skipped_module():
    line = mutants.skipped_line(["claude", "isolation"])
    assert line == "skipped modules: claude, isolation", f"unexpected line {line!r}"
    assert mutants.skipped_line(["stubs"]) == "skipped modules: stubs", "one module must list alone"
