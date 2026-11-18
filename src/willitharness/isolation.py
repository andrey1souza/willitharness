import subprocess
from pathlib import Path

ALLOWED_VARIABLES = frozenset({
    "PATH", "HOME", "USER", "LOGNAME", "SHELL", "LANG", "TERM", "TMPDIR",
    "CLAUDE_CONFIG_DIR", "ANTHROPIC_API_KEY", "ANTHROPIC_BASE_URL",
    "HTTPS_PROXY", "HTTP_PROXY", "NO_PROXY", "SSL_CERT_FILE", "NODE_EXTRA_CA_CERTS",
})
ALLOWED_PREFIXES = ("LC_", "CLAUDE_CODE_")
SECRET_DIRECTORIES = (".ssh", ".aws", ".gnupg", ".config/gh", ".netrc", ".docker")
WRITABLE_DEVICES = ("/dev/null", "/dev/dtracehelper", "/dev/tty", "/dev/stdout", "/dev/stderr")
SANDBOX_TIMEOUT_SECONDS = 30


def agent_environment(environ):
    assert hasattr(environ, "items"), f"agent_environment needs a mapping of variables, got {type(environ).__name__}. Fix: pass os.environ."
    assert "PATH" in environ, "the environment has no PATH. Rule: the agent cannot find its tools without it. Fix: set PATH."
    kept = {
        name: value
        for name, value in environ.items()
        if name in ALLOWED_VARIABLES or name.startswith(ALLOWED_PREFIXES)
    }
    assert kept.keys() <= environ.keys(), f"the scrubbed environment gained variables: {sorted(kept.keys() - environ.keys())}"
    return kept


def quoted(path):
    assert isinstance(path, Path) and path.is_absolute(), f"{path!r} must be an absolute Path. Rule: a sandbox rule names real directories. Fix: pass an absolute Path."
    text = str(path.resolve())
    assert '"' not in text and "\\" not in text, f"{text!r} holds a quote or backslash. Rule: profile paths are plain. Fix: use another folder."
    return f'"{text}"'


def sandbox_profile(world, home, extra_writable):
    assert world.is_dir(), f"{world} is not a directory. Rule: the run writes only inside the world. Fix: create the world first."
    assert home.is_dir(), f"{home} is not a directory. Rule: the profile hides secret folders under home. Fix: pass the user's home."
    writable = [world, *extra_writable]
    allow_writes = " ".join(f"(subpath {quoted(path)})" for path in writable)
    allow_devices = " ".join(f'(literal "{device}")' for device in WRITABLE_DEVICES)
    deny_reads = " ".join(f"(subpath {quoted(home / name)})" for name in SECRET_DIRECTORIES)
    profile = "\n".join([
        "(version 1)",
        "(allow default)",
        "(deny file-write*)",
        f"(allow file-write* {allow_writes} {allow_devices})",
        f"(deny file-read* {deny_reads})",
    ])
    assert "(deny file-write*)" in profile and "(deny file-read*" in profile, f"the profile lost a deny rule: {profile!r}. Rule: writes and secret reads stay denied. Fix: restore the deny lines."
    return profile


def sandboxed_command(command, profile):
    assert command, "sandboxed_command needs a command. Fix: pass the argument list to run."
    assert profile.startswith("(version 1)"), f"the profile must start with (version 1), got {profile!r}. Fix: build it with sandbox_profile."
    return ["sandbox-exec", "-p", profile, *command]


def run_sandboxed(command, profile, directory):
    assert directory.is_dir(), f"{directory} is not a directory. Rule: the command starts inside the world. Fix: pass an existing folder."
    wrapped = sandboxed_command(command, profile)
    completed = subprocess.run(wrapped, cwd=directory, capture_output=True, text=True, timeout=SANDBOX_TIMEOUT_SECONDS)
    assert isinstance(completed.returncode, int), f"the sandboxed run returned {completed.returncode!r}, not an exit code"
    return completed
