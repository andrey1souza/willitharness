import json

from willitharness.isolation import SECRET_DIRECTORIES
from willitharness.stubs import calls_path, scratch_path

ENABLED = True
FAIL_IF_UNAVAILABLE = True
ALLOW_UNSANDBOXED_COMMANDS = False
NO_DOMAINS = ()


def sandbox_settings(workspace, run_root, home, allowed_domains):
    assert workspace.is_absolute() and run_root.is_absolute() and home.is_absolute(), f"{workspace}, {run_root} and {home} must be absolute. Rule: a sandbox rule names real folders. Fix: pass resolved paths."
    assert not isinstance(allowed_domains, str), f"allowed_domains is one string {allowed_domains!r}. Fix: pass a tuple of domain names."
    settings = {
        "sandbox": {
            "enabled": ENABLED,
            "failIfUnavailable": FAIL_IF_UNAVAILABLE,
            "allowUnsandboxedCommands": ALLOW_UNSANDBOXED_COMMANDS,
            "filesystem": {
                "allowWrite": [str(path) for path in (workspace, scratch_path(run_root), calls_path(run_root))],
                "denyRead": [str(home / name) for name in SECRET_DIRECTORIES],
            },
            "network": {"allowedDomains": list(allowed_domains)},
        }
    }
    text = json.dumps(settings)
    assert json.loads(text) == settings, f"the settings did not survive JSON: {text!r}"
    assert len(settings["sandbox"]["filesystem"]["denyRead"]) == len(SECRET_DIRECTORIES), f"a secret folder is missing from denyRead: {text!r}. Rule: every secret folder under home is hidden. Fix: build denyRead from SECRET_DIRECTORIES."
    return text
