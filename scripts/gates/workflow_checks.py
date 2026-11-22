import re
import tomllib
from pathlib import Path

WORKFLOW_DIRECTORY = Path(".github") / "workflows"
SECURITY_FILE = Path("SECURITY.md")
CODEOWNERS_FILE = Path(".github") / "CODEOWNERS"
DEPENDABOT_FILE = Path(".github") / "dependabot.yml"
INCIDENT_HEADING = "## If something goes wrong"
INCIDENT_MAX_LINES = 12
INCIDENT_EVENTS = ("secret", "dependency", "workflow", "result")
SECTION_HEADING = re.compile(r"^## ", re.MULTILINE)
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
JOB_NAMES = {
    "unit-tests": "Unit tests (Linux)",
    "behavior-tests": "Behavior tests, BDD scenarios (Linux)",
    "property-tests": "Property-based tests (Linux)",
    "golden-tests": "Golden-table conformance tests (Linux)",
    "tooling-tests": "Tests of the repo's own guards, gates and site builder (Linux)",
    "mutation-tests": "Mutation tests, do the tests catch injected bugs (Linux)",
    "traceability": "Traceability check, every contract rule has a test (Linux)",
    "repo-rules": "Repository rule checks, static (Linux)",
    "zanity": "Static analysis with zanity (Linux)",
    "gitleaks": "Secret scan with gitleaks (Linux)",
    "site-build": "Site build and freshness check (Linux)",
    "simulation": "Statistical simulation, false-positive rate and power (Linux)",
    "macos-full": "Full tests, mutation, traceability and repository checks on macOS (sandbox tests)",
    "oldest-python-linux": "Tests on the oldest Python the project supports (Linux)",
    "latest-python-linux": "Tests, mutation, traceability and repo checks, latest Python (Linux, advisory, not required)",
    "latest-python-macos": "Tests, mutation, traceability and repo checks, latest Python (macOS, advisory, not required)",
    "build": "Build the site (Linux)",
    "deploy": "Publish the site to GitHub Pages",
}
REQUIRED_JOBS = (
    "unit-tests", "behavior-tests", "property-tests", "golden-tests", "tooling-tests", "mutation-tests",
    "traceability", "repo-rules", "zanity", "gitleaks", "site-build", "simulation", "macos-full", "oldest-python-linux",
)
REQUIRED_CHECK_NAMES = tuple(JOB_NAMES[job] for job in REQUIRED_JOBS)
MAX_JOB_NAME_LENGTH = 100
TESTS_DIRECTORY = Path("tests")
ADVISORY_WORD = "advisory"
UNRUN_TEST_DIRECTORIES = ("support",)
IGNORE_OPTION = "--ignore"
PYTEST_COMMAND = re.compile(r"^\s*-\s*run:\s*uv run pytest(?P<arguments>[^\n]*)$", re.MULTILINE)
JOB_NAME_LINE = re.compile(r"^    name:\s*(.+?)\s*$", re.MULTILINE)
JOBS_HEADER = re.compile(r"^jobs:\s*$", re.MULTILINE)
JOB_KEY = re.compile(r"^  ([\w-]+):\s*$", re.MULTILINE)
UV_USE = re.compile(r"setup-uv|\buv (?:sync|run)\b")
EXPLICIT_PYTHON = re.compile(r"python-version:|\bUV_PYTHON\b|--python\b")
MAJOR_MINOR = re.compile(r"(\d+)\.(\d+)")
MINIMUM_SPECIFIER = re.compile(r"^>=\s*(\d+)\.(\d+)$")
PYTHON_CLAIM = re.compile(r"Python (\d+)\.(\d+) or later")
DOCS_DIRECTORY = Path("docs")
README_FILE = Path("README.md")
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


def missing_jobs_across(texts):
    assert isinstance(texts, list) and all(isinstance(text, str) for text in texts), f"workflow texts must be a list of str, got {texts!r}. Fix: pass the text of every workflow file."
    assert REQUIRED_JOBS, "no jobs are required. Rule: a gate with no expectations proves nothing."
    present = set().union(*(job_blocks(text) for text in texts))
    return [f"job {name} is missing in every workflow; the ruleset requires a status check with that name" for name in REQUIRED_JOBS if name not in present]


def missing_jobs(text):
    assert isinstance(text, str), f"workflow text must be str, got {type(text).__name__}. Fix: pass read_text output."
    problems = missing_jobs_across([text])
    assert all(isinstance(problem, str) for problem in problems), f"missing_jobs returned {problems!r}. Rule: each problem is one message. Fix: build messages as text."
    return problems


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
        if shown is not None and len(shown) > MAX_JOB_NAME_LENGTH:
            problems.append(f"job {job} has a name of {len(shown)} characters, above {MAX_JOB_NAME_LENGTH}. Rule: GitHub cuts longer check names, so the end of the name is lost. Fix: shorten the name")
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
    files = sorted((root / WORKFLOW_DIRECTORY).glob("*.yml"))
    if not files:
        return [f"{WORKFLOW_DIRECTORY} holds no workflows, so the check could not run"]
    return missing_jobs_across([path.read_text() for path in files])


def job_name_errors(root):
    assert root.is_dir(), f"{root} is not a directory. Fix: pass the repository root."
    assert JOB_NAME_LINE.pattern, "the job name pattern is empty"
    return workflow_errors(root, job_name_problems)


def advisory_required_problems(text):
    assert isinstance(text, str), f"workflow text must be str, got {type(text).__name__}. Fix: pass read_text output."
    assert ADVISORY_WORD, "the advisory word is empty. Rule: an advisory job is recognised by its name. Fix: restore ADVISORY_WORD."
    problems = []
    for job, block in job_blocks(text).items():
        found = JOB_NAME_LINE.search(block)
        if job in REQUIRED_JOBS and found and ADVISORY_WORD in found.group(1).lower():
            problems.append(f"job {job} is named {found.group(1)!r}, which says {ADVISORY_WORD}, but the ruleset requires it. Rule: a required check must not call itself {ADVISORY_WORD}. Fix: rename the job or remove it from REQUIRED_JOBS")
    assert all(isinstance(problem, str) for problem in problems), f"problems must be text, got {problems!r}"
    return problems


def advisory_required_errors(root):
    assert root.is_dir(), f"{root} is not a directory. Fix: pass the repository root."
    assert REQUIRED_JOBS, "no jobs are required. Rule: a gate with no expectations proves nothing."
    return workflow_errors(root, advisory_required_problems)


def tested_directories(workflow_text):
    assert isinstance(workflow_text, str), f"workflow text must be str, got {type(workflow_text).__name__}. Fix: pass read_text output."
    assert PYTEST_COMMAND.pattern, "the pytest command pattern is empty"
    named = set()
    for command in PYTEST_COMMAND.finditer(workflow_text):
        arguments = command.group("arguments").split()
        for previous, argument in zip([""] + arguments, arguments):
            parts = Path(argument).parts
            if previous != IGNORE_OPTION and len(parts) == 2 and parts[0] == TESTS_DIRECTORY.name:
                named.add(parts[1])
    assert all(name for name in named), f"a named test directory is empty in {named!r}"
    return named


def pytest_coverage_errors(root):
    assert root.is_dir(), f"{root} is not a directory. Fix: pass the repository root."
    directory = root / TESTS_DIRECTORY
    if not directory.is_dir():
        return []
    present = {path.name for path in directory.iterdir() if path.is_dir() and not path.name.startswith("__") and path.name not in UNRUN_TEST_DIRECTORIES}
    workflows = sorted((root / WORKFLOW_DIRECTORY).glob("*.yml"))
    named = set().union(*(tested_directories(path.read_text()) for path in workflows)) if workflows else set()
    errors = [
        f"{TESTS_DIRECTORY / name} is run by no CI job. Rule: every test directory runs in a job that names it, so a new directory cannot be skipped. Fix: add `uv run pytest {TESTS_DIRECTORY / name}` to a job in {WORKFLOW_DIRECTORY}"
        for name in sorted(present - named)
    ]
    assert all(isinstance(error, str) for error in errors), f"coverage errors must be text, got {errors!r}"
    return errors


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


def minimum_python(root):
    assert root.is_dir(), f"{root} is not a directory. Fix: pass the repository root."
    specifier = tomllib.loads((root / PYPROJECT_FILE).read_text()).get("project", {}).get("requires-python", "")
    found = MINIMUM_SPECIFIER.match(specifier)
    minimum = tuple(map(int, found.groups())) if found else None
    assert minimum is None or len(minimum) == 2, f"minimum must be None or (major, minor), got {minimum!r}"
    return minimum


def oldest_python_jobs(workflow_text, minimum):
    assert isinstance(workflow_text, str), f"workflow text must be str, got {type(workflow_text).__name__}. Fix: pass read_text output."
    assert len(minimum) == 2, f"minimum must be (major, minor), got {minimum!r}. Fix: pass minimum_python output."
    sets_minimum = re.compile(rf"python-version:\s*['\"]?{minimum[0]}\.{minimum[1]}['\"]?\s*$", re.MULTILINE)
    return [job for job, block in job_blocks(workflow_text).items() if sets_minimum.search(block) and PYTEST_COMMAND.search(block)]


def oldest_python_errors(root):
    assert root.is_dir(), f"{root} is not a directory. Fix: pass the repository root."
    assert PYTEST_COMMAND.pattern, "the pytest command pattern is empty"
    minimum = minimum_python(root)
    if minimum is None:
        return []
    workflows = sorted((root / WORKFLOW_DIRECTORY).glob("*.yml"))
    if any(oldest_python_jobs(path.read_text(), minimum) for path in workflows):
        return []
    version = f"{minimum[0]}.{minimum[1]}"
    return [f"no CI job runs `uv run pytest` on Python {version}, the minimum in requires-python. Rule: a supported version is a tested version. Fix: add a job whose setup-uv sets python-version \"{version}\" and runs the tests, or raise requires-python"]


def python_claim_errors(root):
    assert root.is_dir(), f"{root} is not a directory. Fix: pass the repository root."
    assert PYTHON_CLAIM.pattern, "the claim pattern is empty"
    minimum = minimum_python(root)
    if minimum is None:
        return []
    files = [root / README_FILE, *sorted((root / DOCS_DIRECTORY).rglob("*.md"))]
    errors = [
        f"{path.relative_to(root)} says 'Python {found.group(1)}.{found.group(2)} or later', but requires-python is >={minimum[0]}.{minimum[1]}. Rule: one source names the minimum Python. Fix: change the text to match pyproject.toml"
        for path in files if path.is_file()
        for found in PYTHON_CLAIM.finditer(path.read_text())
        if tuple(map(int, found.groups())) != minimum
    ]
    assert all(isinstance(error, str) for error in errors), f"errors must be text, got {errors!r}"
    return errors


def security_file_errors(root):
    assert root.is_dir(), f"{root} is not a directory. Fix: pass the repository root."
    assert REQUIRED_FILES, "no security files are required. Rule: a gate with no expectations proves nothing."
    return [f"{path} is missing" for path in REQUIRED_FILES if not (root / path).is_file()]


def section_under(text, heading):
    assert isinstance(text, str), f"section_under needs text, got {type(text).__name__}. Fix: pass the file contents."
    assert heading.startswith("## "), f"{heading!r} is not a level-two heading. Fix: pass a heading that starts with '## '."
    start = text.find(f"{heading}\n")
    if start < 0:
        return None
    body = text[start + len(heading):]
    following = SECTION_HEADING.search(body)
    return body[:following.start()] if following else body


def security_policy_errors(root):
    assert root.is_dir(), f"{root} is not a directory. Fix: pass the repository root."
    assert INCIDENT_EVENTS, "no incident events are required. Rule: a gate with no expectations proves nothing."
    path = root / SECURITY_FILE
    if not path.is_file():
        return []
    section = section_under(path.read_text(), INCIDENT_HEADING)
    if section is None:
        return [f"{SECURITY_FILE} has no '{INCIDENT_HEADING}' section, so nobody knows who acts or what to do first"]
    errors = [f"{SECURITY_FILE} section '{INCIDENT_HEADING}' does not name the event {event!r}" for event in INCIDENT_EVENTS if event not in section.lower()]
    lines = [line for line in section.splitlines() if line.strip()]
    if len(lines) > INCIDENT_MAX_LINES:
        errors.append(f"{SECURITY_FILE} section '{INCIDENT_HEADING}' has {len(lines)} lines, above {INCIDENT_MAX_LINES}. Rule: a plan read in a crisis stays short. Fix: shorten it")
    return errors


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
    "workflow-pytest-coverage": pytest_coverage_errors,
    "workflow-advisory-not-required": advisory_required_errors,
    "workflow-python-source": python_source_errors,
    "python-version-file": python_version_errors,
    "oldest-python-tested": oldest_python_errors,
    "python-claims-in-docs": python_claim_errors,
    "security-files": security_file_errors,
    "security-policy-headings": security_policy_errors,
    "codeowners": codeowners_errors,
    "dependabot": dependabot_errors,
}
