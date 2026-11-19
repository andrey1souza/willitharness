import repo_checks

STATUS_FILE = "site/data/gate_status.json"


def test_a_tracked_status_file_is_reported():
    errors = repo_checks.generated_errors_among([STATUS_FILE, "site/src/index.html"])
    assert len(errors) == 1 and errors[0].startswith(f"{STATUS_FILE} is generated and must not be tracked"), f"got {errors}"
    assert "site/src/index.html" not in "".join(errors), f"the template is a source, got {errors}"


def test_a_tracked_file_in_a_generated_folder_is_reported():
    errors = repo_checks.generated_errors_among(["formal/tla/generated/Mutant_L1.tla"])
    assert len(errors) == 1 and "formal/tla/generated/Mutant_L1.tla" in errors[0], f"got {errors}"
    assert repo_checks.generated_errors_among(["formal/tla/WillItHarness.tla"]) == [], "a source beside the folder is not reported"


def test_a_name_that_only_starts_like_a_generated_path_is_not_reported():
    names = ["formal/tla/generated_notes.md", "site/data/gate_status.json.md", "site/data/gate_status.jsonx"]
    errors = repo_checks.generated_errors_among(names)
    assert errors == [], f"only the exact file and the folder contents count, got {errors}"
    assert repo_checks.generated_errors_among([]) == [], "no files, no errors"
