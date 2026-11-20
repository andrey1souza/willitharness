import hook_checks
import repo_checks
from files import write_tree

SCRUB = "while read -r name; do unset \"${name}\"; done < <(compgen -e | grep '^GIT_' || true)\n"
GOOD_HOOK = "#!/usr/bin/env bash\n" + SCRUB + "zanity check .\nuv run pytest\n"
HOOK_PATH = ".githooks/pre-push"


def hook_errors_for(tmp_path, hook_text):
    write_tree(tmp_path, {"README.md": "x\n"} if hook_text is None else {HOOK_PATH: hook_text})
    return hook_checks.pre_push_environment_errors(tmp_path)


def test_a_hook_that_clears_git_variables_before_the_tests_passes(tmp_path):
    assert hook_errors_for(tmp_path, GOOD_HOOK) == [], "the scrub before the tests is the required shape"


def test_a_hook_that_clears_the_variables_after_the_tests_is_reported(tmp_path):
    late = "#!/usr/bin/env bash\nuv run pytest\n" + SCRUB
    errors = hook_errors_for(tmp_path, late)
    assert len(errors) == 1 and "does not clear the GIT_ variables" in errors[0], f"got {errors}"


def test_a_hook_without_the_scrub_is_reported(tmp_path):
    errors = hook_errors_for(tmp_path, "#!/usr/bin/env bash\nuv run pytest\n")
    assert len(errors) == 1 and "does not clear the GIT_ variables" in errors[0], f"got {errors}"


def test_a_hook_that_never_runs_the_tests_is_reported(tmp_path):
    errors = hook_errors_for(tmp_path, "#!/usr/bin/env bash\n" + SCRUB)
    assert len(errors) == 1 and "never runs" in errors[0], f"got {errors}"


def test_a_missing_hook_is_reported(tmp_path):
    errors = hook_errors_for(tmp_path, None)
    assert len(errors) == 1 and "is missing" in errors[0], f"got {errors}"


def test_the_hook_check_is_part_of_the_repository_checks():
    missing = [name for name in hook_checks.CHECKS if name not in repo_checks.CHECKS]
    assert missing == [], f"repo_checks.CHECKS must run {missing}"


BARE_CHECK = "python3 scripts/guards/bare_checkout.py\n"
TOPLEVEL = 'repo_root="$(git rev-parse --show-toplevel)"\n'
GOOD_PUSH_HOOK = "#!/usr/bin/env bash\n" + BARE_CHECK + TOPLEVEL + SCRUB + "uv run pytest\n"


def bare_errors_for(tmp_path, hook_text):
    write_tree(tmp_path, {"README.md": "x\n"} if hook_text is None else {HOOK_PATH: hook_text})
    return hook_checks.pre_push_bare_errors(tmp_path)


def test_a_hook_that_detects_a_bare_checkout_before_the_toplevel_call_passes(tmp_path):
    assert bare_errors_for(tmp_path, GOOD_PUSH_HOOK) == [], "the bare check above the toplevel call is the required shape"


def test_a_bare_check_after_the_toplevel_call_is_reported(tmp_path):
    late = "#!/usr/bin/env bash\n" + TOPLEVEL + BARE_CHECK
    errors = bare_errors_for(tmp_path, late)
    assert len(errors) == 1 and "before" in errors[0], f"got {errors}"


def test_a_hook_without_the_bare_check_is_reported(tmp_path):
    errors = bare_errors_for(tmp_path, "#!/usr/bin/env bash\n" + TOPLEVEL)
    assert len(errors) == 1 and "does not run" in errors[0], f"got {errors}"


def test_a_hook_without_the_toplevel_call_is_reported(tmp_path):
    errors = bare_errors_for(tmp_path, "#!/usr/bin/env bash\n" + BARE_CHECK)
    assert len(errors) == 1 and "does not run" in errors[0], f"got {errors}"


def test_a_missing_hook_is_reported_by_the_bare_check(tmp_path):
    errors = bare_errors_for(tmp_path, None)
    assert len(errors) == 1 and "detects a bare-flagged checkout" in errors[0], f"got {errors}"


def test_the_hook_checks_are_the_two_expected_ones():
    assert sorted(hook_checks.CHECKS) == ["pre-push-clears-git-environment", "pre-push-detects-bare-checkout"], f"got {sorted(hook_checks.CHECKS)}"
