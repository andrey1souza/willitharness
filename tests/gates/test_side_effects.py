import pytest
from guard_site import bash, write_call

from willitharness.side_effects import (
    CHANNELS_HEADING,
    NO_DIFFERENCE_LINE,
    NOT_PART_OF_RULE_LINE,
    channels_of_run,
    command_key,
    commands_of_run,
    side_effect_report_lines,
)

GIT_C_RUN = (bash("git -C repo status"),)
PLAIN_RUN = (bash("ls"),)


def mixed_arm(hits, total):
    return tuple([GIT_C_RUN + PLAIN_RUN] * hits + [PLAIN_RUN] * (total - hits))


def test_S1_a_command_used_far_more_in_one_arm_is_listed_with_counts_per_arm():
    lines = side_effect_report_lines({"B": mixed_arm(22, 60), "C": mixed_arm(1, 60)})
    assert lines[0] == "git -C: B 22 of 60 runs, C 1 of 60 runs", f"got {lines!r}"
    assert NOT_PART_OF_RULE_LINE in lines, f"got {lines!r}"
    assert not any(line.startswith("ls") for line in lines), f"a command used the same in both arms was listed: {lines!r}"


def test_S1_equal_use_gives_the_explicit_no_difference_message():
    lines = side_effect_report_lines({"B": mixed_arm(5, 10), "C": mixed_arm(5, 10)})
    assert lines == [NO_DIFFERENCE_LINE], f"got {lines!r}"


def test_S1_the_gap_is_compared_as_rates_not_counts():
    lines = side_effect_report_lines({"B": mixed_arm(10, 20), "C": mixed_arm(5, 10)})
    assert lines == [NO_DIFFERENCE_LINE], f"10 of 20 equals 5 of 10, got {lines!r}"


def test_S1_a_gap_of_exactly_the_minimum_is_listed():
    lines = side_effect_report_lines({"B": mixed_arm(2, 10), "C": mixed_arm(0, 10)})
    assert lines[0] == "git -C: B 2 of 10 runs, C 0 of 10 runs", f"got {lines!r}"


def test_S1_a_gap_below_the_minimum_is_not_listed():
    lines = side_effect_report_lines({"B": mixed_arm(1, 10), "C": mixed_arm(0, 10)})
    assert lines == [NO_DIFFERENCE_LINE], f"got {lines!r}"


def test_S1_a_command_counts_once_per_run():
    twice = (bash("git -C a status; git -C b status"),)
    lines = side_effect_report_lines({"B": (twice, PLAIN_RUN), "C": (PLAIN_RUN, PLAIN_RUN)})
    assert lines[0] == "git -C: B 1 of 2 runs, C 0 of 2 runs", f"got {lines!r}"


def test_S1_alternative_channels_are_listed_with_counts():
    written = (bash("ls"), write_call("a.txt"))
    lines = side_effect_report_lines({"D1": (PLAIN_RUN,) * 10, "D2": (written,) * 4 + (PLAIN_RUN,) * 6})
    assert lines[-2:] == [CHANNELS_HEADING, "Write: D1 0 of 10 runs, D2 4 of 10 runs"], f"got {lines!r}"
    assert lines[0] == NO_DIFFERENCE_LINE, f"got {lines!r}"


def test_S1_no_channel_section_without_a_non_bash_tool():
    lines = side_effect_report_lines({"B": (PLAIN_RUN,), "C": (PLAIN_RUN,)})
    assert CHANNELS_HEADING not in lines, f"got {lines!r}"


def test_S1_the_report_is_the_same_for_the_same_input():
    arms = {"B": mixed_arm(22, 60), "C": mixed_arm(1, 60)}
    assert side_effect_report_lines(arms) == side_effect_report_lines(arms), "the report changed between two builds"


def test_S1_command_key_keeps_the_leading_flags_only():
    assert command_key(("git", "-C", "repo", "status", "-s")) == "git -C", "flags after a word must not join the key"
    assert command_key(("FOO=1", "env", "git", "status")) == "git", "assignments and env must be skipped"
    assert command_key(("ls", "-l", "-a")) == "ls -l -a", "every leading flag joins the key"


def test_S1_assignment_only_segments_give_no_command():
    assert commands_of_run((bash("FOO=1"),)) == frozenset(), "an assignment is not a command"


def test_S1_only_non_bash_tools_are_channels():
    assert channels_of_run((bash("ls"), write_call("a", "Edit"))) == frozenset({"Edit"}), "Bash must not be a channel"


@pytest.mark.parametrize("runs_by_arm", [{"B": (PLAIN_RUN,)}, {"B": (PLAIN_RUN,), "C": ()}])
def test_S1_a_report_needs_two_arms_with_runs(runs_by_arm):
    with pytest.raises(AssertionError, match="Fix:") as refusal:
        side_effect_report_lines(runs_by_arm)
    assert "side-effect report" in str(refusal.value) or "no runs" in str(refusal.value), f"got {refusal.value}"


def test_S1_every_segment_of_a_command_line_counts():
    assert commands_of_run((bash("ls; git -C repo status | cat"),)) == frozenset({"ls", "git -C", "cat"}), "a later segment was lost"
