import re
from pathlib import Path

WORKFLOW_DIRECTORY = Path(".github") / "workflows"
SECURITY_FILE = Path("SECURITY.md")
CODEOWNERS_FILE = Path(".github") / "CODEOWNERS"
DEPENDABOT_FILE = Path(".github") / "dependabot.yml"
REQUIRED_FILES = (SECURITY_FILE, CODEOWNERS_FILE, DEPENDABOT_FILE)
REQUIRED_ECOSYSTEMS = ("github-actions", "uv")
LOCAL_ACTION_PREFIX = "./"
USES_LINE = re.compile(r"^\s*(?:-\s+)?uses:\s*['\"]?([^\s'\"#]+)")
PINNED_REFERENCE = re.compile(r"[^@\s]+@[0-9a-f]{40}")
PERMISSIONS_LINE = re.compile(r"^permissions:", re.MULTILINE)
TRIGGER_LINE = re.compile(r"^\s*(?:-\s+)?pull_request_target\b|^\s*on:.*\bpull_request_target\b", re.MULTILINE)
RUN_LINE = re.compile(r"^(\s*)(-\s+)?run:\s*(.*)$")
UNTRUSTED_EXPRESSION = re.compile(r"\$\{\{[^}]*github\.(?:event\.|head_ref)[^}]*\}\}")
UNLOCKED_SYNC = re.compile(r"uv sync(?! --locked)")
CATCH_ALL_OWNER = re.compile(r"^\*\s+@\S+", re.MULTILINE)
ECOSYSTEM_LINE = re.compile(r"package-ecosystem:\s*['\"]?([\w-]+)")
BLOCK_SCALARS = ("|", ">", "|-", ">-", "|+", ">+")


def unpinned_uses(text):
    assert isinstance(text, str), f"workflow text must be str, got {type(text).__name__}. Fix: pass read_text output."
    references = [match.group(1) for line in text.splitlines() if (match := USES_LINE.match(line))]
    assert all(references), f"an empty uses reference slipped through in {references!r}"
    return [f"uses {reference} is not pinned to a 40-hex commit SHA" for reference in references if not reference.startswith(LOCAL_ACTION_PREFIX) and not PINNED_REFERENCE.fullmatch(reference)]


def missing_permissions(text):
    assert isinstance(text, str), f"workflow text must be str, got {type(text).__name__}. Fix: pass read_text output."
    assert PERMISSIONS_LINE.pattern.startswith("^"), "the permissions pattern must anchor at column 0"
    return [] if PERMISSIONS_LINE.search(text) else ["no top-level permissions: block, so the token gets the repository default"]


def pull_request_target_use(text):
    assert isinstance(text, str), f"workflow text must be str, got {type(text).__name__}. Fix: pass read_text output."
    assert TRIGGER_LINE.pattern, "the trigger pattern is empty"
    return ["pull_request_target runs fork code with secrets and a write token"] if TRIGGER_LINE.search(text) else []


def run_blocks(text):
    assert isinstance(text, str), f"workflow text must be str, got {type(text).__name__}. Fix: pass read_text output."
    lines = text.splitlines()
    blocks = []
    for number, line in enumerate(lines):
        match = RUN_LINE.match(line)
        if not match:
            continue
        key_indent = len(match.group(1)) + len(match.group(2) or "")
        body = [] if match.group(3) in BLOCK_SCALARS else [match.group(3)]
        for following in lines[number + 1:]:
            if following.strip() and len(following) - len(following.lstrip()) <= key_indent:
                break
            body.append(following)
        blocks.append("\n".join(body))
    assert all(isinstance(block, str) for block in blocks), f"blocks must be text, got {blocks!r}"
    return blocks


def script_injection(text):
    assert isinstance(text, str), f"workflow text must be str, got {type(text).__name__}. Fix: pass read_text output."
    expressions = [match.group(0) for block in run_blocks(text) for match in UNTRUSTED_EXPRESSION.finditer(block)]
    errors = [f"run block interpolates {expression}; pass it through env: instead (CICD-SEC-4)" for expression in expressions]
    assert len(errors) == len(expressions), f"expected one error per expression, got {errors!r}"
    return errors


def unlocked_sync(text):
    assert isinstance(text, str), f"workflow text must be str, got {type(text).__name__}. Fix: pass read_text output."
    assert UNLOCKED_SYNC.pattern, "the sync pattern is empty"
    return ["uv sync without --locked can change the lockfile in CI"] if UNLOCKED_SYNC.search(text) else []


def workflow_errors(root, text_check):
    assert root.is_dir(), f"{root} is not a directory. Fix: pass the repository root."
    assert callable(text_check), f"text_check must be a function, got {text_check!r}"
    files = sorted((root / WORKFLOW_DIRECTORY).glob("*.yml"))
    if not files:
        return [f"{WORKFLOW_DIRECTORY} holds no workflows, so the check could not run"]
    return [f"{path.name}: {error}" for path in files for error in text_check(path.read_text())]


def pinned_errors(root):
    assert root.is_dir(), f"{root} is not a directory. Fix: pass the repository root."
    assert PINNED_REFERENCE.pattern, "the pin pattern is empty"
    return workflow_errors(root, unpinned_uses)


def permissions_errors(root):
    assert root.is_dir(), f"{root} is not a directory. Fix: pass the repository root."
    assert PERMISSIONS_LINE.pattern, "the permissions pattern is empty"
    return workflow_errors(root, missing_permissions)


def trigger_errors(root):
    assert root.is_dir(), f"{root} is not a directory. Fix: pass the repository root."
    assert TRIGGER_LINE.pattern, "the trigger pattern is empty"
    return workflow_errors(root, pull_request_target_use)


def injection_errors(root):
    assert root.is_dir(), f"{root} is not a directory. Fix: pass the repository root."
    assert UNTRUSTED_EXPRESSION.pattern, "the expression pattern is empty"
    return workflow_errors(root, script_injection)


def locked_sync_errors(root):
    assert root.is_dir(), f"{root} is not a directory. Fix: pass the repository root."
    assert UNLOCKED_SYNC.pattern, "the sync pattern is empty"
    return workflow_errors(root, unlocked_sync)


def security_file_errors(root):
    assert root.is_dir(), f"{root} is not a directory. Fix: pass the repository root."
    assert REQUIRED_FILES, "no security files are required. Rule: a gate with no expectations proves nothing."
    return [f"{path} is missing" for path in REQUIRED_FILES if not (root / path).is_file()]


def codeowners_errors(root):
    assert root.is_dir(), f"{root} is not a directory. Fix: pass the repository root."
    assert CATCH_ALL_OWNER.pattern, "the owner pattern is empty"
    path = root / CODEOWNERS_FILE
    if not path.is_file():
        return []
    return [] if CATCH_ALL_OWNER.search(path.read_text()) else [f"{CODEOWNERS_FILE} has no catch-all line like '* @owner'"]


def dependabot_errors(root):
    assert root.is_dir(), f"{root} is not a directory. Fix: pass the repository root."
    assert REQUIRED_ECOSYSTEMS, "no ecosystems are required. Rule: a gate with no expectations proves nothing."
    path = root / DEPENDABOT_FILE
    if not path.is_file():
        return []
    listed = ECOSYSTEM_LINE.findall(path.read_text())
    return [f"{DEPENDABOT_FILE} does not update {name}" for name in REQUIRED_ECOSYSTEMS if name not in listed]


CHECKS = {
    "workflow-pinned": pinned_errors,
    "workflow-permissions": permissions_errors,
    "workflow-triggers": trigger_errors,
    "workflow-injection": injection_errors,
    "workflow-locked-sync": locked_sync_errors,
    "security-files": security_file_errors,
    "codeowners": codeowners_errors,
    "dependabot": dependabot_errors,
}
