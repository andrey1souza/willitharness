import shutil
from dataclasses import replace

import pytest
from files import plant, write_tree
from lifecycle_site import OVERLAY_FILE, OVERLAY_TEXT, SiteSpec, edit_overlay, make_site, with_budget

from willitharness.plan import PlanError, changed_overlay_files, overlay_digests, plan_fingerprint

SMALL = SiteSpec(arm_count=1, budget_usd=1.0, run_cap_usd=0.02, reps=2, max_retries=1)


def test_A_FP_the_same_overlays_give_the_same_fingerprint_and_a_budget_change_does_not_move_it(tmp_path):
    site = make_site(tmp_path, SMALL)
    first = plan_fingerprint(site.plan, site.root)
    assert plan_fingerprint(site.plan, site.root) == first, f"two runs of the fingerprint over the same overlays differ from {first}"
    assert plan_fingerprint(with_budget(site, 7.0).plan, site.root) == first, f"budget 7.0 moved the fingerprint of {site.plan.name}"


def test_A_FP_the_fingerprint_follows_the_bytes_and_the_path_of_an_overlay_file(tmp_path):
    site = make_site(tmp_path, SMALL)
    first = plan_fingerprint(site.plan, site.root)
    edit_overlay(site)
    edited = plan_fingerprint(site.plan, site.root)
    assert edited != first, f"an overlay edit left the fingerprint at {first}"
    (site.root / "A.md" / OVERLAY_FILE).rename(site.root / "A.md" / "moved.txt")
    assert plan_fingerprint(site.plan, site.root) != edited, f"a renamed overlay file left the fingerprint at {edited}"


def test_A_FP_a_missing_overlay_gives_a_fingerprint_that_changes_when_the_overlay_appears(tmp_path):
    site = make_site(tmp_path, SMALL)
    shutil.rmtree(site.root / "A.md")
    absent = plan_fingerprint(site.plan, site.root)
    plant(site.root / "A.md", OVERLAY_FILE, OVERLAY_TEXT)
    assert plan_fingerprint(site.plan, site.root) != absent, f"a new overlay left the fingerprint at {absent}"


def test_A_FP_an_overlay_outside_the_project_is_refused_with_a_rule_and_a_fix(tmp_path):
    site = make_site(tmp_path / "project", SMALL)
    outside = replace(site.plan, arms=(replace(site.plan.arms[0], overlay="../elsewhere"),))
    with pytest.raises(PlanError) as raised:
        plan_fingerprint(outside, site.root)
    assert "Rule:" in str(raised.value) and "Fix:" in str(raised.value), f"got {raised.value!r}"


def test_A_FP_the_digests_do_not_depend_on_the_order_the_files_were_written(tmp_path):
    first = make_site(tmp_path / "first", SMALL)
    second = make_site(tmp_path / "second", SMALL)
    write_tree(first.root, {"A.md/b/one.txt": "1", "A.md/a/two.txt": "2", "A.md/c.txt": "3"})
    write_tree(second.root, {"A.md/c.txt": "3", "A.md/a/two.txt": "2", "A.md/b/one.txt": "1"})
    assert list(overlay_digests(first.plan, first.root)) == sorted(overlay_digests(first.plan, first.root)), f"the digests are not sorted: {list(overlay_digests(first.plan, first.root))}"
    assert "A.md/b/one.txt" in overlay_digests(first.plan, first.root), f"a file in a subfolder is missing from {list(overlay_digests(first.plan, first.root))}"
    assert plan_fingerprint(first.plan, first.root) == plan_fingerprint(second.plan, second.root), "the same overlay files in another write order gave another fingerprint"


def test_A_FP_the_same_bytes_under_another_path_give_another_fingerprint(tmp_path):
    site = make_site(tmp_path, SMALL)
    plant(site.root / "A.md", "one.txt", "same")
    first = plan_fingerprint(site.plan, site.root)
    (site.root / "A.md" / "one.txt").rename(site.root / "A.md" / "two.txt")
    assert plan_fingerprint(site.plan, site.root) != first, f"a rename with the same bytes left the fingerprint at {first} for {site.plan.arms[0].overlay} under {site.root}"


def test_A_FP_changed_overlay_files_names_edited_added_and_removed_files():
    stored = {"A.md/edited.txt": "1", "A.md/removed.txt": "2", "A.md/same.txt": "3"}
    current = {"A.md/edited.txt": "9", "A.md/added.txt": "4", "A.md/same.txt": "3"}
    assert changed_overlay_files(stored, current) == ["A.md/added.txt", "A.md/edited.txt", "A.md/removed.txt"], f"got {changed_overlay_files(stored, current)}"
    assert changed_overlay_files(stored, stored) == [], f"equal digests reported {changed_overlay_files(stored, stored)}"


def test_A_FP_a_file_overlay_is_hashed_by_its_bytes(tmp_path):
    site = make_site(tmp_path, SMALL)
    shutil.rmtree(site.root / "A.md")
    (site.root / "A.md").write_text("one")
    first = plan_fingerprint(site.plan, site.root)
    (site.root / "A.md").write_text("two")
    assert plan_fingerprint(site.plan, site.root) != first, f"an edit of a file overlay left the fingerprint at {first} for {site.plan.arms[0].overlay} under {site.root}"


def test_A_FP_two_arms_with_other_overlays_both_enter_the_fingerprint(tmp_path):
    site = make_site(tmp_path, replace(SMALL, arm_count=2))
    first = plan_fingerprint(site.plan, site.root)
    edit_overlay(site, arm_index=1)
    assert plan_fingerprint(site.plan, site.root) != first, f"an edit of the second overlay left the fingerprint at {first}"
    assert set(overlay_digests(site.plan, site.root)) == {"A.md/rule.txt", "B.md/rule.txt"}, f"got {set(overlay_digests(site.plan, site.root))}"
