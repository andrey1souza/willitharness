import subprocess
from pathlib import Path

TEST_EMAIL = "t@example.com"
TEST_NAME = "t"


def run_git(repo, arguments):
    subprocess.run(["git"] + arguments, cwd=repo, check=True, capture_output=True)


def git_output(repo, arguments):
    result = subprocess.run(["git"] + arguments, cwd=repo, check=True, capture_output=True, text=True)
    return result.stdout.strip()


def init_repo(directory, email):
    run_git(directory, ["init", "-q", "-b", "main"])
    run_git(directory, ["config", "user.email", email])
    run_git(directory, ["config", "user.name", TEST_NAME])
    return directory


def commit_files(repo, subject, relative_paths):
    for relative_path in relative_paths:
        target = Path(repo) / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(subject + relative_path)
        run_git(repo, ["add", relative_path])
    run_git(repo, ["commit", "-q", "--allow-empty", "-m", subject])
