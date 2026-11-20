import re
import tomllib
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
PYTHON_VERSION_FILE = Path(".python-version")
PYPROJECT_FILE = Path("pyproject.toml")
REQUIRED_JOBS = ("test", "zanity", "macos")
JOB_NAMES = {
    "test": "Tests, mutants, repo checks and site (Linux, pinned Python)",
    "macos": "Tests, mutants and repo checks (macOS, pinned Python)",
    "test-latest": "Tests, mutants and repo checks (Linux, latest Python)",
    "macos-latest-python": "Tests, mutants and repo checks (macOS, latest Python)",
    "zanity": "Zanity rules (Linux)",
    "gitleaks": "Secret scan with gitleaks (Linux)",
}
REQUIRED_CHECK_NAMES = tuple(JOB_NAMES[job] for job in REQUIRED_JOBS)
JOB_NAME_LINE = re.compile(r"^    name:\s*(.+?)\s*$", re.MULTILINE)
JOBS_HEADER = re.compile(r"^jobs:\s*$", re.MULTILINE)
JOB_KEY = re.compile(r"^  ([\w-]+):\s*$", re.MULTILINE)
UV_USE = re.compile(r"setup-uv|\buv (?:sync|run)\b")
EXPLICIT_PYTHON = re.compile(r"python-version:|\bUV_PYTHON\b|--python\b")
MAJOR_MINOR = re.compile(r"(\d+)\.(\d+)")
MINIMUM_SPECIFIER = re.compile(r"^>=\s*(\d+)\.(\d+)$")
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


def job_blocks(text):
    assert isinstance(text, str), f"workflow text must be str, got {type(text).__name__}. Fix: pass read_text output."
    header = JOBS_HEADER.search(text)
    if not header:
        return {}
    body = text[header.end():]
    keys = list(JOB_KEY.finditer(body))
    blocks = {key.group(1): body[key.start():keys[index + 1].start() if index + 1 < len(keys) else len(body)] for index, key in enumerate(keys)}
    assert len(blocks) == len(keys), f"two jobs share a name in {[key.group(1) for key in keys]!r}. Fix: rename one."
    return blocks


def missing_jobs(text):
    assert isinstance(text, str), f"workflow text must be str, got {type(text).__name__}. Fix: pass read_text output."
    assert REQUIRED_JOBS, "no jobs are required. Rule: a gate with no expectations proves nothing."
    present = job_blocks(text)
    return [f"job {name} is missing; the ruleset requires a status check with that name" for name in REQUIRED_JOBS if name not in present]


def job_name_problems(text):
    assert isinstance(text, str), f"workflow text must be str, got {type(text).__name__}. Fix: pass read_text output."
    assert JOB_NAMES, "no job names are expected. Rule: a gate with no expectations proves nothing."
    problems = []
    for job, block in job_blocks(text).items():
        found = JOB_NAME_LINE.search(block)
        shown = found.group(1) if found else None
        if job not in JOB_NAMES:
            problems.append(f"job {job} has no expected name in JOB_NAMES. Rule: every job is named for what it runs. Fix: add it to JOB_NAMES")
        elif shown != JOB_NAMES[job]:
            problems.append(f"job {job} is named {shown!r}, expected {JOB_NAMES[job]!r}. Rule: the status check shows the job name, so it must say what runs")
    return problems


def unsourced_python_jobs(text):
    assert isinstance(text, str), f"workflow text must be str, got {type(text).__name__}. Fix: pass read_text output."
    assert EXPLICIT_PYTHON.pattern, "the explicit-python pattern is empty"
    return [
        f"job {name} runs uv without an explicit python-version and {PYTHON_VERSION_FILE} is missing"
        for name, block in job_blocks(text).items()
        if UV_USE.search(block) and not EXPLICIT_PYTHON.search(block)
    ]


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


def required_job_errors(root):
    assert root.is_dir(), f"{root} is not a directory. Fix: pass the repository root."
    assert REQUIRED_JOBS, "no jobs are required. Rule: a gate with no expectations proves nothing."
    return workflow_errors(root, missing_jobs)


def job_name_errors(root):
    assert root.is_dir(), f"{root} is not a directory. Fix: pass the repository root."
    assert JOB_NAME_LINE.pattern, "the job name pattern is empty"
    return workflow_errors(root, job_name_problems)


def python_source_errors(root):
    assert root.is_dir(), f"{root} is not a directory. Fix: pass the repository root."
    assert UV_USE.pattern, "the uv pattern is empty"
    if (root / PYTHON_VERSION_FILE).is_file():
        return []
    return workflow_errors(root, unsourced_python_jobs)


def python_version_errors(root):
    assert root.is_dir(), f"{root} is not a directory. Fix: pass the repository root."
    assert MINIMUM_SPECIFIER.pattern, "the specifier pattern is empty"
    pinned = MAJOR_MINOR.match((root / PYTHON_VERSION_FILE).read_text().strip()) if (root / PYTHON_VERSION_FILE).is_file() else None
    if not pinned:
        return [f"{PYTHON_VERSION_FILE} is missing or does not start with major.minor, so local and CI Python are not pinned"]
    specifier = tomllib.loads((root / PYPROJECT_FILE).read_text()).get("project", {}).get("requires-python", "")
    minimum = MINIMUM_SPECIFIER.match(specifier)
    if not minimum:
        return [f"requires-python {specifier!r} is not of the form '>=X.Y', so {PYTHON_VERSION_FILE} cannot be checked against it"]
    satisfied = tuple(map(int, pinned.groups())) >= tuple(map(int, minimum.groups()))
    return [] if satisfied else [f"{PYTHON_VERSION_FILE} pins {pinned.group(0)}, below requires-python {specifier}"]


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
    "workflow-required-jobs": required_job_errors,
    "workflow-job-names": job_name_errors,
    "workflow-python-source": python_source_errors,
    "python-version-file": python_version_errors,
    "security-files": security_file_errors,
    "codeowners": codeowners_errors,
    "dependabot": dependabot_errors,
}
