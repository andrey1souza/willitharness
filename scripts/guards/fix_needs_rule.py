import re
import subprocess
import sys

FIX_SUBJECT = re.compile(r"^fix(\([^)]*\))?!?:")
CHECK_PREFIXES = ("tests/", "features/", "formal/")
EXIT_CLEAN = 0
EXIT_MISSING_CHECK = 1
SHORT_SHA_LENGTH = 10


def git_lines(repo, arguments):
    assert isinstance(arguments, list) and arguments, (
        "git_lines needs a non-empty list but got %r. Rule: git needs a subcommand. "
        "Fix: pass a list such as ['rev-list', 'HEAD']." % (arguments,)
    )
    result = subprocess.run(["git"] + arguments, cwd=repo, capture_output=True, text=True)
    assert result.returncode == 0, (
        "git %s exited %r with %r. Rule: the guard reads history and cannot continue on an error. "
        "Fix: check the revision range and the repository path." % (arguments[0], result.returncode, result.stderr)
    )
    return [line for line in result.stdout.splitlines() if line.strip()]


def is_fix(subject):
    assert isinstance(subject, str), (
        "is_fix needs text but got %r. Rule: a subject is one line of text. "
        "Fix: pass the commit subject." % (subject,)
    )
    assert "\n" not in subject, (
        "subject %r spans several lines. Rule: the subject is the first line only. "
        "Fix: pass git log --format=%%s output." % (subject,)
    )
    return bool(FIX_SUBJECT.match(subject))


def touches_a_check(paths):
    assert isinstance(paths, list), (
        "touches_a_check needs a list but got %r. Rule: a commit changes a list of paths. "
        "Fix: pass the diff-tree output lines." % (paths,)
    )
    assert all(isinstance(path, str) for path in paths), (
        "paths %r must all be text. Rule: git prints paths as text. "
        "Fix: pass the lines git printed." % (paths,)
    )
    return any(path.startswith(CHECK_PREFIXES) for path in paths)


def commits_without_check(repo, revision_arguments):
    assert isinstance(revision_arguments, list) and revision_arguments, (
        "commits_without_check got %r. Rule: git rev-list needs a range. "
        "Fix: pass for example ['origin/main..HEAD']." % (revision_arguments,)
    )
    offenders = []
    for sha in git_lines(repo, ["rev-list"] + revision_arguments):
        subject = git_lines(repo, ["log", "-n1", "--format=%s", sha])[0]
        paths = git_lines(repo, ["diff-tree", "--no-commit-id", "--name-only", "-r", "--root", sha])
        if is_fix(subject) and not touches_a_check(paths):
            offenders.append((sha[:SHORT_SHA_LENGTH], subject))
    assert all(len(sha) <= SHORT_SHA_LENGTH for sha, _ in offenders), (
        "offenders %r hold a sha longer than %d characters. Rule: reports show short shas. "
        "Fix: cut the sha before storing it." % (offenders, SHORT_SHA_LENGTH)
    )
    return offenders


def fix_failure_message(offenders):
    assert offenders, (
        "fix_failure_message got offenders %r. Rule: a failure names at least one commit. "
        "Fix: call it only when commits_without_check found one." % (offenders,)
    )
    assert all(len(pair) == 2 for pair in offenders), (
        "offenders %r must be (sha, subject) pairs. Rule: the report prints both. "
        "Fix: build the pairs in commits_without_check." % (offenders,)
    )
    listing = "; ".join("%s %s" % pair for pair in offenders)
    return (
        "fix-needs-rule: %d fix commit(s) change no check: %s. "
        "Rule: every fix ships a test, a feature or a formal check that rules out the whole category. "
        "Fix: add one under %s in the same commit, then commit again."
        % (len(offenders), listing, ", ".join(CHECK_PREFIXES))
    )


def main(arguments, repo):
    assert arguments, (
        "main got arguments %r. Rule: the guard needs a git revision range. "
        "Fix: pass for example HEAD or origin/main..HEAD." % (arguments,)
    )
    offenders = commits_without_check(repo, arguments)
    assert isinstance(offenders, list), (
        "commits_without_check returned %r. Rule: callers test the list for emptiness. "
        "Fix: return a list." % (offenders,)
    )
    if not offenders:
        return EXIT_CLEAN
    print(fix_failure_message(offenders), file=sys.stderr)
    return EXIT_MISSING_CHECK


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:], "."))
