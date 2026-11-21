from pathlib import Path

import pytest

import repo_checks
from files import write_tree


PUBLISHING_SENTENCE = "Run scripts/guards/integrate.py --land-local to publish the branch."
CLEAN_README = "Run scripts/guards/integrate.py to verify the branch, then push it and open a pull request.\n\n`--land-local` is not for publishing.\n"


def publishing_errors(tmp_path, files):
    write_tree(tmp_path, files)
    return repo_checks.integrate_publishing_errors(tmp_path)


def test_a_readme_that_verifies_with_integrate_and_bans_land_local_for_publishing_passes(tmp_path):
    errors = publishing_errors(tmp_path, {"README.md": CLEAN_README})
    assert errors == [], f"integrate and the pull request in separate sentences must pass, got {errors}"
    assert repo_checks.publish_documents(tmp_path) == [Path("README.md")], "only the existing document is scanned"


@pytest.mark.parametrize("name", ["README.md", "SECURITY.md", "Makefile", "docs/guide.md"])
def test_each_document_that_publishes_with_integrate_fails(tmp_path, name):
    errors = publishing_errors(tmp_path, {name: "Intro line.\n\n" + PUBLISHING_SENTENCE + "\n"})
    assert len(errors) == 1 and name in errors[0], f"{name} must be named, got {errors}"
    assert "Rule:" in errors[0] and "Fix:" in errors[0], f"the message needs Rule and Fix, got {errors[0]!r}"


@pytest.mark.parametrize("sentence", ["--land-local opens a pull request.", "Use --land-local to push to origin.", "--land-local opens a PR for you."])
def test_each_publishing_word_is_caught(tmp_path, sentence):
    errors = publishing_errors(tmp_path, {"README.md": sentence + "\n"})
    assert len(errors) == 1, f"{sentence!r} must fail, got {errors}"
    assert "README.md" in errors[0], f"the file must be named, got {errors}"


def test_a_sentence_wrapped_over_two_lines_is_caught(tmp_path):
    errors = publishing_errors(tmp_path, {"README.md": "Use --land-local\nto publish your work.\n"})
    assert len(errors) == 1, f"a wrapped sentence must fail, got {errors}"
    assert "--land-local to publish" in errors[0], f"the sentence is quoted on one line, got {errors[0]!r}"


def test_the_frozen_contract_and_the_research_folder_are_exempt(tmp_path):
    files = {"docs/contract-v0.1.md": PUBLISHING_SENTENCE, "docs/research/note.md": PUBLISHING_SENTENCE, "docs/plan/old.md": PUBLISHING_SENTENCE}
    errors = publishing_errors(tmp_path, files)
    assert errors == [], f"history and nested docs are not scanned, got {errors}"
    assert repo_checks.publish_documents(tmp_path) == [], "no scanned document exists"


def test_the_check_is_registered():
    assert repo_checks.CHECKS["integrate-not-for-publishing"] is repo_checks.integrate_publishing_errors, "the check runs in make repo"
    assert "integrate-not-for-publishing" in repo_checks.CHECKS, "the check is listed by name"


@pytest.mark.parametrize("negation", ["not", "never", "No"])
def test_a_sentence_that_forbids_land_local_for_publishing_passes(tmp_path, negation):
    sentence = f"{negation} use --land-local to publish." if negation != "No" else "No --land-local to publish."
    errors = publishing_errors(tmp_path, {"README.md": sentence + "\n"})
    assert errors == [], f"a sentence that forbids it must pass, got {errors} for {sentence!r}"
    bare = publishing_errors(tmp_path, {"README.md": "Use --land-local to publish.\n"})
    assert bare != [], f"without the negation it fails in {tmp_path}, got {bare}"
