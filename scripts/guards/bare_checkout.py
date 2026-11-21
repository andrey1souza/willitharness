import os
import subprocess
import sys
from pathlib import Path

GIT_DIRECTORY_NAME = ".git"
BARE_ARGUMENTS = ["config", "--type=bool", "--get", "core.bare"]
COMMON_DIRECTORY_ARGUMENTS = ["rev-parse", "--path-format=absolute", "--git-common-dir"]
BARE_VALUE = "true"
EXIT_CLEAN = 0
EXIT_BARE_CHECKOUT = 1
GIT_CONFIG_MISSING_KEY = 1


def git_stdout(repo, arguments, accepted_codes):
    assert repo, "git_stdout got repo %r. Rule: git runs in one repository. Fix: pass the repository directory." % (repo,)
    assert arguments and accepted_codes, (
        "git_stdout got arguments %r and codes %r. Rule: a call names its git arguments and the exit codes it accepts. "
        "Fix: pass both." % (arguments, accepted_codes)
    )
    result = subprocess.run(["git", *arguments], cwd=repo, capture_output=True, text=True)
    assert result.returncode in accepted_codes, (
        "git %s exited %r with %r. Rule: this check reads git state and cannot continue on an error. "
        "Fix: run it inside a git repository." % (arguments[0], result.returncode, result.stderr.strip())
    )
    return result.stdout.strip()


def bare_checkout_problem(common_directory, bare_value):
    assert isinstance(common_directory, Path), (
        "bare_checkout_problem needs a Path but got %r. Rule: the git common directory is a path. "
        "Fix: pass Path(git rev-parse --git-common-dir)." % (common_directory,)
    )
    assert isinstance(bare_value, str), (
        "bare_checkout_problem needs text but got %r. Rule: core.bare is read as text. "
        "Fix: pass the git config output." % (bare_value,)
    )
    problem = ""
    if bare_value == BARE_VALUE and common_directory.name == GIT_DIRECTORY_NAME and common_directory.is_dir():
        checkout = common_directory.parent
        problem = (
            "bare-checkout: core.bare is %s in %s, which holds a %s directory. "
            "Rule: a checkout with a %s directory is not bare, and git then fails with a work tree error. "
            "Fix: run git config core.bare false in %s."
            % (bare_value, checkout, GIT_DIRECTORY_NAME, GIT_DIRECTORY_NAME, checkout)
        )
    assert isinstance(problem, str), "bare_checkout_problem returned %r. Rule: the answer is a message or empty text. Fix: return text." % (problem,)
    return problem


def main(repo):
    assert repo, "main got repo %r. Rule: the check reads one repository. Fix: pass the repository directory." % (repo,)
    common_directory = Path(git_stdout(repo, COMMON_DIRECTORY_ARGUMENTS, (0,)))
    bare_value = git_stdout(repo, BARE_ARGUMENTS, (0, GIT_CONFIG_MISSING_KEY))
    problem = bare_checkout_problem(common_directory, bare_value)
    code = EXIT_BARE_CHECKOUT if problem else EXIT_CLEAN
    if problem:
        print(problem, file=sys.stderr)
    assert code in (EXIT_CLEAN, EXIT_BARE_CHECKOUT), "main computed code %r. Rule: the exit code is clean or bare-checkout. Fix: return a listed code." % (code,)
    return code


if __name__ == "__main__":
    sys.exit(main(os.getcwd()))
