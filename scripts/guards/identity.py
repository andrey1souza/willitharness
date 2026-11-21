import os
import re
import subprocess
import sys
from pathlib import Path

PATTERN_VARIABLE = "WILLITHARNESS_EMAIL_PATTERN"
DEFAULT_PATTERN = r"^\d+\+andrey1souza@users\.noreply\.github\.com$"
ACCOUNT_VARIABLE = "WILLITHARNESS_GH_ACCOUNT"
DEFAULT_ACCOUNT = "andrey1souza"
ACCOUNT_KEY = "credential.https://github.com.username"
EXIT_CLEAN = 0
EXIT_WRONG_IDENTITY = 1
GIT_CONFIG_MISSING_KEY = 1
SIGNING_KEY = "user.signingkey"
SIGNERS_KEY = "gpg.ssh.allowedsignersfile"
KEY_FIELD_INDEX = 1


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


def configured_account(repo):
    assert repo, (
        "configured_account got repo %r. Rule: git config reads one repository. "
        "Fix: pass the repository directory." % (repo,)
    )
    result = subprocess.run(
        ["git", "config", "--local", "--get", ACCOUNT_KEY], cwd=repo, capture_output=True, text=True
    )
    assert result.returncode in (0, GIT_CONFIG_MISSING_KEY), (
        "git config exited %r with %r. Rule: 0 means set and 1 means unset. "
        "Fix: check that %r is a git repository." % (result.returncode, result.stderr, repo)
    )
    return result.stdout.strip()


def account_failure_message(account, expected_account):
    assert expected_account, (
        "account_failure_message got expected account %r. Rule: the message names the expected account. "
        "Fix: set %s or unset it." % (expected_account, ACCOUNT_VARIABLE)
    )
    assert account != expected_account, (
        "account_failure_message was called with the expected account %r. Rule: only a wrong account "
        "gets this message. Fix: call it when the accounts differ." % (account,)
    )
    shown = account if account else "(unset in this repo)"
    return (
        "identity: the GitHub account for gh in this repo is %s, expected %s. "
        "Rule: only the repo-local %s counts, because the global value is the work account. "
        "Fix: run git config %s %s in this repo."
        % (shown, expected_account, ACCOUNT_KEY, ACCOUNT_KEY, expected_account)
    )


def configured_value(repo, key):
    assert repo, (
        "configured_value got repo %r. Rule: git config reads one repository. "
        "Fix: pass the repository directory." % (repo,)
    )
    assert key, "configured_value got key %r. Rule: git config needs a key. Fix: pass a key such as %s." % (key, SIGNING_KEY)
    result = subprocess.run(["git", "config", "--get", key], cwd=repo, capture_output=True, text=True)
    assert result.returncode in (0, GIT_CONFIG_MISSING_KEY), (
        "git config exited %r with %r. Rule: 0 means set and 1 means unset. "
        "Fix: check that %r is a git repository." % (result.returncode, result.stderr, repo)
    )
    return result.stdout.strip()


def key_blob(public_key_text):
    assert isinstance(public_key_text, str), (
        "key_blob needs text but got %r. Rule: a public key file is text. "
        "Fix: pass the file content." % (public_key_text,)
    )
    fields = public_key_text.split()
    blob = fields[KEY_FIELD_INDEX] if len(fields) > KEY_FIELD_INDEX else ""
    assert blob in fields or blob == "", f"key_blob returned {blob!r}, which is not a field of {public_key_text!r}. Rule: the blob is the second field. Fix: read the second field."
    return blob


def principal_trusts_key(signers_text, email, blob):
    assert isinstance(signers_text, str), (
        "principal_trusts_key needs text but got %r. Rule: the signers file is text. "
        "Fix: pass the file content." % (signers_text,)
    )
    assert email and blob, (
        "principal_trusts_key got email %r and key %r. Rule: both identify one signer. "
        "Fix: read them from git config and the public key file." % (email, blob)
    )
    for line in signers_text.splitlines():
        fields = line.split()
        if len(fields) > KEY_FIELD_INDEX and email in fields[0].split(",") and blob in fields[KEY_FIELD_INDEX:]:
            return True
    return False


def read_key_file_text(path):
    assert path, "read_key_file_text got path %r. Rule: a key file has a path. Fix: set the git config key first." % (path,)
    target = Path(path).expanduser()
    text = target.read_text() if target.is_file() else ""
    assert isinstance(text, str), f"read_key_file_text returned {text!r}, not text. Rule: a key file is text. Fix: read it as text."
    return text


def signing_problem(email, signing_key_path, signers_path):
    assert email, (
        "signing_problem got email %r. Rule: the signer is the commit email. "
        "Fix: set git config user.email first." % (email,)
    )
    assert isinstance(signing_key_path, str) and isinstance(signers_path, str), (
        "signing_problem got key %r and signers %r. Rule: both are config text, empty when unset. "
        "Fix: pass the git config output." % (signing_key_path, signers_path)
    )
    if not signing_key_path or not signers_path:
        return (
            "identity: %s or %s is unset. "
            "Rule: GitHub shows a commit as verified only when its signing key is registered for the author. "
            "Fix: set both in git config." % (SIGNING_KEY, SIGNERS_KEY)
        )
    blob = key_blob(read_key_file_text(signing_key_path))
    if not blob:
        return (
            "identity: %s names %s, which holds no public key. "
            "Rule: the signing key is a public key file. Fix: point it at the .pub file." % (SIGNING_KEY, signing_key_path)
        )
    trusted = principal_trusts_key(read_key_file_text(signers_path), email, blob)
    assert isinstance(trusted, bool), f"principal_trusts_key returned {trusted!r}, not a bool. Rule: a key is trusted or not. Fix: return a bool."
    if not trusted:
        return (
            "identity: the signing key %s is not listed for %s in %s. "
            "Rule: GitHub shows a commit as unverified when the key is not registered for the author. "
            "Fix: set %s to the key that %s lists for this email, in this repo."
            % (signing_key_path, email, signers_path, SIGNING_KEY, signers_path)
        )
    return ""


def identity_problems(email, pattern, account, expected_account):
    assert pattern, (
        "identity_problems got pattern %r. Rule: an empty pattern would accept anything. "
        "Fix: set %s to a regex or unset it." % (pattern, PATTERN_VARIABLE)
    )
    assert expected_account, (
        "identity_problems got expected account %r. Rule: an empty account would accept anything. "
        "Fix: set %s or unset it." % (expected_account, ACCOUNT_VARIABLE)
    )
    problems = []
    if not email_allowed(email, pattern):
        problems.append(identity_failure_message(email, pattern))
    if account != expected_account:
        problems.append(account_failure_message(account, expected_account))
    return problems


def main(environment, repo):
    pattern = environment.get(PATTERN_VARIABLE, DEFAULT_PATTERN)
    expected_account = environment.get(ACCOUNT_VARIABLE, DEFAULT_ACCOUNT)
    email = configured_email(repo)
    signing = signing_problem(email, configured_value(repo, SIGNING_KEY), configured_value(repo, SIGNERS_KEY)) if email else ""
    problems = identity_problems(email, pattern, configured_account(repo), expected_account)
    if signing:
        problems.append(signing)
    assert isinstance(problems, list), (
        "identity_problems returned %r. Rule: callers count the problems. Fix: return a list." % (problems,)
    )
    assert all(isinstance(problem, str) for problem in problems), (
        "problems %r must all be text. Rule: each problem is one message. Fix: build messages as text." % (problems,)
    )
    for problem in problems:
        print(problem, file=sys.stderr)
    return EXIT_WRONG_IDENTITY if problems else EXIT_CLEAN


if __name__ == "__main__":
    sys.exit(main(os.environ, os.getcwd()))
