import check_lean

PINNED = {"lean": "aa", "lake": "bb"}


def test_matching_digests_have_no_mismatch():
    mismatches = check_lean.pin_mismatches({"lean": "aa", "lake": "bb"}, PINNED)
    assert mismatches == [], f"digests that match their pins must pass, got {mismatches}"
    assert PINNED == {"lean": "aa", "lake": "bb"}, "the check must not change the pins"


def test_a_changed_binary_and_a_missing_binary_are_both_reported():
    mismatches = check_lean.pin_mismatches({"lean": "xx"}, PINNED)
    assert len(mismatches) == 2, f"a changed and a missing binary must both be reported, got {mismatches}"
    assert any("lean has sha256 xx" in item for item in mismatches) and any("lake has sha256 None" in item for item in mismatches), f"each error must name the binary and its digest, got {mismatches}"


def test_the_pins_cover_lean_and_lake_with_64_hex_digits():
    for key, pinned in check_lean.PINNED_BINARY_SHA256.items():
        assert sorted(pinned) == ["lake", "lean"], f"{key} must pin lean and lake, got {sorted(pinned)}"
        assert all(len(digest) == 64 for digest in pinned.values()), f"{key} needs sha256 hex digests, got {pinned}"


def test_the_installed_toolchain_matches_its_pin_when_present():
    key = (check_lean.platform.system(), check_lean.platform.machine())
    if key in check_lean.PINNED_BINARY_SHA256 and check_lean.TOOLS.is_dir():
        row = check_lean.check_toolchain_pin()
        assert row[3], f"the installed toolchain does not match its pin: {row}"
    assert check_lean.toolchain_directory_name() == "leanprover--lean4---v4.36.0", "the directory name must follow lean-toolchain"
