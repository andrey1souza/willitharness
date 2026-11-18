import subprocess


def git_lines(repo, arguments):
    assert repo, f"git_lines got repo {repo!r}. Rule: git runs in one repository. Fix: pass the repository directory."
    assert isinstance(arguments, list) and arguments, (
        f"git_lines needs a non-empty list but got {arguments!r}. Rule: git needs a subcommand. "
        "Fix: pass a list such as ['rev-list', 'HEAD']."
    )
    result = subprocess.run(["git"] + arguments, cwd=repo, capture_output=True, text=True)
    assert result.returncode == 0, (
        f"git {arguments[0]} exited {result.returncode} with {result.stderr.strip()!r}. "
        "Rule: a guard reads git state and cannot continue on an error. "
        "Fix: check the arguments and that the directory is a git repository."
    )
    return [line for line in result.stdout.splitlines() if line.strip()]
