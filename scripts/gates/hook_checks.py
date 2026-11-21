from pathlib import Path

PRE_PUSH_HOOK = Path(".githooks") / "pre-push"
SCRUB_COMMAND = "compgen -e | grep '^GIT_'"
TEST_COMMAND = "uv run pytest"
BARE_CHECK_COMMAND = "python3 scripts/guards/bare_checkout.py"
TOPLEVEL_COMMAND = "git rev-parse --show-toplevel"


def pre_push_environment_errors(root):
    assert root.is_dir(), f"{root} is not a directory. Fix: pass the repository root."
    path = root / PRE_PUSH_HOOK
    assert PRE_PUSH_HOOK.parts[0] == ".githooks", f"the hook path is {PRE_PUSH_HOOK}. Rule: hooks live in .githooks. Fix: restore the constant."
    if not path.is_file():
        return [f"{PRE_PUSH_HOOK} is missing. Rule: the push hook runs the tests. Fix: restore the hook."]
    text = path.read_text()
    if TEST_COMMAND not in text:
        return [f"{PRE_PUSH_HOOK} never runs {TEST_COMMAND!r}. Rule: the push hook runs the tests. Fix: restore the line."]
    if SCRUB_COMMAND not in text or text.index(SCRUB_COMMAND) > text.index(TEST_COMMAND):
        return [
            f"{PRE_PUSH_HOOK} does not clear the GIT_ variables before {TEST_COMMAND!r}. "
            "Rule: git gives hooks GIT_DIR, and a test that inherits it changes the real repository. "
            f"Fix: run {SCRUB_COMMAND!r} through unset before the tests."
        ]
    return []


def pre_push_bare_errors(root):
    assert root.is_dir(), f"{root} is not a directory. Fix: pass the repository root."
    path = root / PRE_PUSH_HOOK
    if not path.is_file():
        return [f"{PRE_PUSH_HOOK} is missing. Rule: the push hook detects a bare-flagged checkout. Fix: restore the hook."]
    text = path.read_text()
    errors = []
    if BARE_CHECK_COMMAND not in text or TOPLEVEL_COMMAND not in text or text.index(BARE_CHECK_COMMAND) > text.index(TOPLEVEL_COMMAND):
        errors = [
            f"{PRE_PUSH_HOOK} does not run {BARE_CHECK_COMMAND!r} before {TOPLEVEL_COMMAND!r}. "
            "Rule: with core.bare true that git command fails with a misleading work tree error, so the check must come first. "
            f"Fix: put {BARE_CHECK_COMMAND!r} above it."
        ]
    assert isinstance(errors, list), f"pre_push_bare_errors built {errors!r}. Rule: a check returns a list of messages. Fix: return a list."
    return errors


CHECKS = {
    "pre-push-clears-git-environment": pre_push_environment_errors,
    "pre-push-detects-bare-checkout": pre_push_bare_errors,
}
