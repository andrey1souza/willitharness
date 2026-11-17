import os
import re
import subprocess
import sys

PATTERN_VARIABLE = "WILLITHARNESS_EMAIL_PATTERN"
DEFAULT_PATTERN = r"^\d+\+andrey1souza@users\.noreply\.github\.com$"
EXIT_CLEAN = 0
EXIT_WRONG_IDENTITY = 1
GIT_CONFIG_MISSING_KEY = 1


def configured_email(repo):
    assert repo, (
        "configured_email got repo %r. Rule: git config reads one repository. "
        "Fix: pass the repository directory." % (repo,)
    )
    result = subprocess.run(["git", "config", "--get", "user.email"], cwd=repo, capture_output=True, text=True)
    assert result.returncode in (0, GIT_CONFIG_MISSING_KEY), (
        "git config exited %r with %r. Rule: 0 means set and 1 means unset. "
        "Fix: check that %r is a git repository." % (result.returncode, result.stderr, repo)
    )
    return result.stdout.strip()


def email_allowed(email, pattern):
    assert isinstance(email, str), (
        "email_allowed needs text but got %r. Rule: an address is text. "
        "Fix: pass the git config output." % (email,)
    )
    assert pattern, (
        "email_allowed got pattern %r. Rule: an empty pattern would accept anything. "
        "Fix: set %s to a regex or unset it." % (pattern, PATTERN_VARIABLE)
    )
    return bool(re.match(pattern, email))


def identity_failure_message(email, pattern):
    assert pattern, (
        "identity_failure_message got pattern %r. Rule: the message names the pattern. "
        "Fix: pass the pattern that rejected the address." % (pattern,)
    )
    assert not email_allowed(email, pattern), (
        "identity_failure_message was called for %r, which matches %r. Rule: only a rejected address "
        "gets this message. Fix: call it when email_allowed returns False." % (email, pattern)
    )
    shown = email if email else "(unset)"
    return (
        "identity: commit email %s does not match %s. "
        "Rule: commits in this repo use the personal noreply address, never a work or private one. "
        "Fix: run git config user.email with your personal noreply address in this repo."
        % (shown, pattern)
    )


def main(environment, repo):
    pattern = environment.get(PATTERN_VARIABLE, DEFAULT_PATTERN)
    email = configured_email(repo)
    allowed = email_allowed(email, pattern)
    assert allowed in (True, False), (
        "email_allowed returned %r for %r. Rule: the check answers yes or no. "
        "Fix: return a bool." % (allowed, email)
    )
    assert allowed == bool(re.match(pattern, email)), (
        "email %r and pattern %r gave allowed=%r. Rule: allowed means the pattern matches. "
        "Fix: correct email_allowed." % (email, pattern, allowed)
    )
    if allowed:
        return EXIT_CLEAN
    print(identity_failure_message(email, pattern), file=sys.stderr)
    return EXIT_WRONG_IDENTITY


if __name__ == "__main__":
    sys.exit(main(os.environ, os.getcwd()))
