import json

from files import plant
from willitharness import fakeagent
from willitharness.fakeagent import Behavior, Location

CLAUDE_FILE = "CLAUDE.md"
AGENTS_FILE = "AGENTS.md"
TARGET_CODE = "ZQ-8841-lumen"
OTHER_CODE = "purple-giraffe-91"
SEED = 7
HALF_RECALL = 0.5
SEED_SWEEP = range(40)
TARGET_LINE = f"Verification code: {TARGET_CODE}\n"


def act(child, boundary, behavior):
    return fakeagent.run_agent(behavior, Location(child, boundary), fakeagent.DEFAULT_LABEL, 0)


def reply_of(transcript):
    return json.loads(transcript[-1])["result"]


def agents_only_fixture(tmp_path):
    child = plant(tmp_path / "work", AGENTS_FILE, TARGET_LINE)
    return child, tmp_path


def ancestor_masks_fixture(tmp_path):
    plant(tmp_path, CLAUDE_FILE, "Some other instructions.\n")
    child = plant(tmp_path / "work", AGENTS_FILE, TARGET_LINE)
    return child, tmp_path


def test_the_same_seed_gives_byte_equal_transcripts_for_every_seed(tmp_path):
    child, boundary = agents_only_fixture(tmp_path)
    for seed in SEED_SWEEP:
        first = act(child, boundary, Behavior(seed, HALF_RECALL))
        second = act(child, boundary, Behavior(seed, HALF_RECALL))
        assert "\n".join(first).encode() == "\n".join(second).encode(), f"seed {seed}: {first} vs {second}"


def test_seeds_change_the_reply_when_recall_is_partial(tmp_path):
    child, boundary = agents_only_fixture(tmp_path)
    replies = {reply_of(act(child, boundary, Behavior(seed, HALF_RECALL))) for seed in SEED_SWEEP}
    assert replies == {TARGET_CODE, fakeagent.NO_VALUE_REPLY}, f"expected both replies across seeds, got {replies}"


def test_a_run_without_a_seed_exits_two_with_the_fix(tmp_path, capsys):
    child, boundary = agents_only_fixture(tmp_path)
    code = fakeagent.main(["--directory", str(child), "--boundary", str(boundary)])
    errors = capsys.readouterr().err
    assert code == fakeagent.EXIT_USAGE, f"expected exit {fakeagent.EXIT_USAGE}, got {code}"
    assert errors.strip() == "seed required; pass --seed N", f"unexpected message {errors!r}"


def test_the_command_prints_the_same_bytes_for_the_same_seed(tmp_path, capsys):
    child, boundary = agents_only_fixture(tmp_path)
    arguments = ["--seed", str(SEED), "--directory", str(child), "--boundary", str(boundary)]
    first_code = fakeagent.main(arguments)
    first = capsys.readouterr().out
    second_code = fakeagent.main(arguments)
    second = capsys.readouterr().out
    assert (first_code, second_code) == (fakeagent.EXIT_OK, fakeagent.EXIT_OK), f"exit codes {first_code}, {second_code}"
    assert first == second and first.count("\n") == 4, f"expected four equal lines, got {first!r} and {second!r}"


def test_agents_file_alone_is_seen(tmp_path):
    child, boundary = agents_only_fixture(tmp_path)
    reply = reply_of(act(child, boundary, Behavior(SEED)))
    assert reply == TARGET_CODE, f"AGENTS.md with no CLAUDE.md must load, got {reply!r}"


def test_an_ancestor_claude_file_hides_the_agents_file(tmp_path):
    child, boundary = ancestor_masks_fixture(tmp_path)
    reply = reply_of(act(child, boundary, Behavior(SEED)))
    assert reply == fakeagent.NO_VALUE_REPLY, f"a parent CLAUDE.md must hide AGENTS.md, got {reply!r}"


def test_a_claude_file_above_the_boundary_is_not_read(tmp_path):
    plant(tmp_path, CLAUDE_FILE, "Above the boundary.\n")
    boundary = plant(tmp_path / "project", AGENTS_FILE, TARGET_LINE)
    reply = reply_of(act(boundary, boundary, Behavior(SEED)))
    assert reply == TARGET_CODE, f"the walk must stop at the boundary, got {reply!r}"


def test_a_claude_file_in_the_same_directory_is_read(tmp_path):
    child = plant(tmp_path, CLAUDE_FILE, TARGET_LINE)
    reply = reply_of(act(child, tmp_path, Behavior(SEED)))
    assert reply == TARGET_CODE, f"CLAUDE.md must be read, got {reply!r}"


def test_zero_recall_never_reports_a_visible_value(tmp_path):
    child, boundary = agents_only_fixture(tmp_path)
    replies = {reply_of(act(child, boundary, Behavior(seed, 0.0))) for seed in SEED_SWEEP}
    assert replies == {fakeagent.NO_VALUE_REPLY}, f"recall 0 must never report the value, got {replies}"


def test_an_unseen_reply_can_leak_another_value(tmp_path):
    child, boundary = ancestor_masks_fixture(tmp_path)
    reply = reply_of(act(child, boundary, Behavior(SEED, unseen_reply=OTHER_CODE)))
    assert reply == OTHER_CODE, f"the configured unseen reply must be used, got {reply!r}"
