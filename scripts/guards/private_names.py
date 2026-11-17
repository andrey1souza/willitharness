import os
import subprocess
import sys
import tempfile
from pathlib import Path

DENYLIST_VARIABLE = "WILLITHARNESS_DENYLIST"
DEFAULT_DENYLIST = Path.home() / ".config" / "willitharness" / "denylist"
EXIT_CLEAN = 0
EXIT_LEAK = 1
EXIT_BLOCKED = 2
GIT_GREP_NO_MATCH = 1
STAGED_FLAG = "--staged"
REVISION_FLAG = "--rev"


def denylist_location(environment):
    location = Path(environment.get(DENYLIST_VARIABLE, DEFAULT_DENYLIST))
    assert str(location) not in ("", "."), (
        "%s resolved to %r. Rule: the denylist is a file path. "
        "Fix: set the variable to a file or unset it." % (DENYLIST_VARIABLE, str(location))
    )
    assert not location.is_dir(), (
        "denylist %s is a directory. Rule: the denylist is one file with a regex per line. "
        "Fix: point %s at a file." % (location, DENYLIST_VARIABLE)
    )
    return location


def patterns_from_text(text):
    assert isinstance(text, str), (
        "patterns_from_text needs text but got %r. Rule: the denylist is a text file. "
        "Fix: pass the file contents." % (text,)
    )
    patterns = [line.strip() for line in text.splitlines() if line.strip()]
    assert len(patterns) <= len(text.splitlines()), (
        "found %d patterns in %d lines. Rule: each pattern comes from one line. "
        "Fix: do not split lines further." % (len(patterns), len(text.splitlines()))
    )
    return patterns


def read_patterns(environment):
    location = denylist_location(environment)
    text = location.read_text() if location.is_file() else ""
    assert location.is_file() or not text, (
        "denylist %s is missing but text %r was read. Rule: a missing file has no text. "
        "Fix: read the file only when it exists." % (location, text[:20])
    )
    patterns = patterns_from_text(text)
    assert bool(patterns) == bool(text.strip()), (
        "denylist %s has %d patterns for text %r. Rule: non-blank text gives at least one pattern. "
        "Fix: check patterns_from_text." % (location, len(patterns), text[:20])
    )
    return location, patterns


def grep_options(staged, revision):
    assert staged != bool(revision), (
        "grep_options got staged=%r and revision=%r. Rule: scan either the index or one revision. "
        "Fix: pass exactly one of them." % (staged, revision)
    )
    options = ["git", "grep", "-I", "-i", "-E", "-l"]
    assert options[:2] == ["git", "grep"], (
        "options start with %r. Rule: the scan runs git grep. Fix: keep git grep first." % (options[:2],)
    )
    return options[:2] + ["--cached"] + options[2:] if staged else options


def grep_tail(patterns_file, revision):
    assert patterns_file, (
        "grep_tail got patterns_file %r. Rule: git grep reads patterns from a file. "
        "Fix: pass the temporary file name." % (patterns_file,)
    )
    assert isinstance(revision, str), (
        "revision is %r. Rule: a revision is text, empty for the index. "
        "Fix: pass an empty string when scanning staged files." % (revision,)
    )
    return ["-f", patterns_file] + ([revision] if revision else []) + ["--"]


def matching_files(repo, patterns, staged, revision):
    assert patterns, (
        "matching_files got patterns %r. Rule: an empty pattern list matches every file. "
        "Fix: stop before scanning when the denylist is empty." % (patterns,)
    )
    assert Path(repo).is_dir(), (
        "repo %r is not a directory. Rule: git grep runs inside a work tree. "
        "Fix: run the guard from the repository root." % (repo,)
    )
    with tempfile.NamedTemporaryFile("w", suffix=".patterns", delete=False) as handle:
        handle.write("\n".join(patterns) + "\n")
    command = grep_options(staged, revision) + grep_tail(handle.name, revision)
    result = subprocess.run(command, cwd=repo, capture_output=True, text=True)
    os.unlink(handle.name)
    assert result.returncode in (0, GIT_GREP_NO_MATCH), (
        "git grep exited %r with %r. Rule: 0 means a match and 1 means none. "
        "Fix: read the git error above and correct the revision or the pattern." % (result.returncode, result.stderr)
    )
    return [line for line in result.stdout.splitlines() if line.strip()]


def denylist_missing_message(denylist):
    assert str(denylist), (
        "denylist_missing_message got %r. Rule: the message names the file. "
        "Fix: pass the denylist path." % (str(denylist),)
    )
    message = (
        "private-names: denylist missing or empty: %s. "
        "Rule: public text must not carry private names, and the scan needs the list of terms. "
        "Fix: create that file with one regex per line, set %s to your own file, "
        "or unset core.hooksPath if you do not maintain this repo."
        % (denylist, DENYLIST_VARIABLE)
    )
    assert str(denylist) in message, (
        "message %r does not name %s. Rule: the reader must see which file is missing. "
        "Fix: keep the path in the template." % (message, denylist)
    )
    return message


def leak_message(files):
    assert files, (
        "leak_message got files %r. Rule: a leak report names at least one file. "
        "Fix: call it only when the scan found a file." % (files,)
    )
    assert all(isinstance(name, str) for name in files), (
        "files %r must all be text. Rule: git grep lists file names. "
        "Fix: pass the list git grep returned." % (files,)
    )
    return (
        "private-names: %d file(s) contain a term from the private denylist: %s. "
        "Rule: public text must not carry private names. "
        "Fix: remove or reword the term in those files, then commit again."
        % (len(files), ", ".join(sorted(files)))
    )


def main(arguments, environment, repo):
    denylist, patterns = read_patterns(environment)
    if not patterns:
        print(denylist_missing_message(denylist), file=sys.stderr)
        return EXIT_BLOCKED
    staged = STAGED_FLAG in arguments
    revision = arguments[arguments.index(REVISION_FLAG) + 1] if REVISION_FLAG in arguments else ""
    assert staged != bool(revision), (
        "arguments %r gave staged=%r and revision=%r. Rule: scan the index or one revision. "
        "Fix: pass either %s or %s <sha>." % (arguments, staged, revision, STAGED_FLAG, REVISION_FLAG)
    )
    files = matching_files(repo, patterns, staged, revision)
    assert isinstance(files, list), (
        "matching_files returned %r. Rule: callers count the files. "
        "Fix: return a list." % (files,)
    )
    if not files:
        return EXIT_CLEAN
    print(leak_message(files), file=sys.stderr)
    return EXIT_LEAK


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:], os.environ, os.getcwd()))
