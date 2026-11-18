import pytest

from willitharness.arms import remove_section

SECTION = "Working here as an agent"
HARNESS = "# Rules\n\n## Working here as an agent\n\nA rule.\n\n### Detail\n\nNested text.\n\n## Style\n\nKeep it short.\n"


def test_removing_a_section_keeps_every_other_section():
    result = remove_section(HARNESS, SECTION)
    assert result == "# Rules\n\n## Style\n\nKeep it short.\n", f"unexpected result {result!r}"


def test_removing_a_section_removes_its_nested_sections():
    result = remove_section(HARNESS, SECTION)
    assert "Nested text." not in result and "### Detail" not in result, f"the nested section stayed: {result!r}"


def test_a_section_at_the_end_of_the_file_is_removed():
    result = remove_section("## One\n\nA\n\n## Two\n\nB\n", "Two")
    assert result == "## One\n\nA\n\n", f"unexpected result {result!r}"


def test_a_missing_heading_is_rejected_with_the_count():
    with pytest.raises(AssertionError) as raised:
        remove_section(HARNESS, "Nothing like this")
    assert "occurs 0 times" in str(raised.value), f"unexpected message {str(raised.value)!r}"


def test_a_repeated_heading_is_rejected():
    with pytest.raises(AssertionError) as raised:
        remove_section("## Same\n\nA\n\n## Same\n\nB\n", "Same")
    assert "occurs 2 times" in str(raised.value), f"unexpected message {str(raised.value)!r}"
