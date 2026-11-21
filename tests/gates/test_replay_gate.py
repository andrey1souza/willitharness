import json
import sys
from pathlib import Path

import check_models
import pytest
import replay_traces
import trace_fixtures

REPO_ROOT = Path(__file__).resolve().parents[2]
UNAVAILABLE = replay_traces.tlc_unavailable(check_models.DEFAULT_JAR, check_models.DEFAULT_JAVA)
needs_tlc = pytest.mark.skipif(bool(UNAVAILABLE), reason=UNAVAILABLE or "TLC is available")
DIGEST_OF_ABC = "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
WALK_LINE = json.dumps("WALK " + json.dumps([{"act": ["Init"]}, {"act": ["Terminated"]}])) + "\n"


def test_an_absent_jar_is_the_skip_reason(tmp_path):
    reason = replay_traces.tlc_unavailable(tmp_path / "absent.jar", check_models.DEFAULT_JAVA)
    assert reason.startswith(f"the TLA tools jar {tmp_path / 'absent.jar'} is absent"), f"got {reason!r}"
    assert "Fix:" in reason, f"the reason must name the fix, got {reason!r}"


def test_an_absent_java_is_the_skip_reason(tmp_path):
    jar = tmp_path / "tla2tools.jar"
    jar.write_bytes(b"abc")
    reason = replay_traces.tlc_unavailable(jar, str(tmp_path / "no-java"))
    assert reason.startswith(f"java {tmp_path / 'no-java'} is absent"), f"got {reason!r}"
    assert "Fix:" in reason, f"the reason must name the fix, got {reason!r}"


def test_a_jar_with_another_digest_is_the_skip_reason(tmp_path):
    jar = tmp_path / "tla2tools.jar"
    jar.write_bytes(b"abc")
    reason = replay_traces.tlc_unavailable(jar, sys.executable)
    assert DIGEST_OF_ABC in reason, f"the digest of the jar must show in the reason, got {reason!r}"
    assert check_models.TLA_JAR_SHA256 in reason, f"the pinned digest must show in the reason, got {reason!r}"


def test_the_script_without_tlc_exits_1_and_says_why(tmp_path, capsys):
    code = replay_traces.main(["--jar", str(tmp_path / "absent.jar")])
    error = capsys.readouterr().err
    assert code == replay_traces.EXIT_FAILED, f"expected exit {replay_traces.EXIT_FAILED}, got {code}"
    assert "is absent" in error, f"the reason must reach stderr, got {error!r}"


def test_the_walk_cfg_swaps_the_checked_names_for_the_walker():
    cfg = replay_traces.walk_cfg("resume_world", 5)
    assert cfg.startswith("INIT WalkInit\nNEXT WalkNext\nCONSTANTS\n"), f"got {cfg[:60]!r}"
    assert "WalkDepth = 4" in cfg and cfg.endswith("INVARIANT\n    Export\n"), f"got {cfg!r}"
    assert "Budget = 3" in cfg and "SPECIFICATION" not in cfg, f"the scenario constants must stay and the spec line must go, got {cfg!r}"


def test_a_walk_line_is_parsed_once_without_its_terminated_tail():
    walks = replay_traces.parse_walks(WALK_LINE + WALK_LINE + "Progress: 3 states checked\n")
    assert walks == [[{"act": ["Init"]}]], f"got {walks}"
    assert replay_traces.parse_walks("no walk here\n") == [], "output without a walk line holds no walk"


def test_the_constants_of_a_scenario_are_read_from_its_cfg():
    constants = replay_traces.constants_of("resume_world")
    assert constants["Budget"] == 3 and constants["RunCap"] == 2 and constants["Reps"] == 1, f"got {constants}"
    assert constants["MaxBudget"] == 6, f"got {constants}"


@needs_tlc
@pytest.mark.parametrize("scenario", replay_traces.SCENARIOS)
def test_the_fixture_is_what_tlc_walks_again_from_its_seed(scenario):
    header, walks = trace_fixtures.load_fixture(REPO_ROOT, scenario)
    again = replay_traces.run_walks(scenario, check_models.DEFAULT_JAR, check_models.DEFAULT_JAVA, header)
    assert again == walks, f"TLC walks of {scenario} from seed {header['seed']} differ from the fixture. Fix: run make replay-fixtures."
    assert header["tlc_jar_sha256"] == check_models.TLA_JAR_SHA256, f"the fixture was recorded with another jar: {header['tlc_jar_sha256']}"
    assert all(len(walk) <= header["depth"] for walk in walks), f"a walk is deeper than {header['depth']}"


@needs_tlc
def test_the_whole_replay_finds_no_divergence_and_covers_every_action(capsys):
    code = replay_traces.replay_all(check_models.DEFAULT_JAR, check_models.DEFAULT_JAVA, replay_traces.SEED)
    output = capsys.readouterr().out
    assert code == replay_traces.EXIT_OK, f"the replay must pass, got {output}"
    assert "refusal probes" in output and "divergence" not in output, f"unexpected output {output!r}"
