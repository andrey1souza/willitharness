import repo_checks
import workflow_checks
from files import write_tree

PINNED = "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1"
GOOD_WORKFLOW = f"name: ci\non:\n  push:\npermissions:\n  contents: read\njobs:\n  test:\n    steps:\n      - uses: {PINNED} # v7\n      - run: uv sync --locked\n  zanity:\n    steps:\n      - run: echo zanity\n  macos:\n    steps:\n      - run: uv run pytest\n"
GOOD_FILES = {
    ".github/workflows/ci.yml": GOOD_WORKFLOW,
    ".python-version": "3.13\n",
    "pyproject.toml": "[project]\nrequires-python = \">=3.11\"\n",
    "SECURITY.md": "report privately\n",
    ".github/CODEOWNERS": "* @owner\n",
    ".github/dependabot.yml": "updates:\n  - package-ecosystem: github-actions\n  - package-ecosystem: uv\n",
}


def failures_for(tmp_path, overrides):
    write_tree(tmp_path, {**GOOD_FILES, **overrides})
    return {name: check(tmp_path) for name, check in workflow_checks.CHECKS.items()}


def test_a_good_tree_passes_every_check(tmp_path):
    failures = failures_for(tmp_path, {})
    assert failures == {name: [] for name in workflow_checks.CHECKS}, f"a good tree must pass, got {failures}"


def test_a_tag_pinned_action_is_reported(tmp_path):
    failures = failures_for(tmp_path, {".github/workflows/ci.yml": GOOD_WORKFLOW.replace(PINNED, "actions/checkout@v4")})
    assert failures["workflow-pinned"] == ["ci.yml: uses actions/checkout@v4 is not pinned to a 40-hex commit SHA"], f"got {failures}"
    assert sum(1 for errors in failures.values() if errors) == 1, f"only the pin check may fail, got {failures}"


def test_a_short_sha_is_reported_but_a_local_action_is_not(tmp_path):
    short = GOOD_WORKFLOW.replace(PINNED, "actions/checkout@3d3c42e")
    local = GOOD_WORKFLOW.replace(PINNED, "./.github/actions/setup")
    assert len(workflow_checks.unpinned_uses(short)) == 1, f"a short SHA must be reported, got {workflow_checks.unpinned_uses(short)}"
    assert workflow_checks.unpinned_uses(local) == [], f"a local action needs no pin, got {workflow_checks.unpinned_uses(local)}"


def test_an_upper_case_sha_and_a_branch_name_are_reported(tmp_path):
    upper = GOOD_WORKFLOW.replace(PINNED, "actions/checkout@" + "A" * 40)
    branch = GOOD_WORKFLOW.replace(PINNED, "actions/checkout@main")
    assert len(workflow_checks.unpinned_uses(upper)) == 1, "an upper-case SHA is not a commit SHA reference GitHub resolves safely"
    assert len(workflow_checks.unpinned_uses(branch)) == 1, "a branch name must be reported"


def test_a_workflow_without_permissions_is_reported(tmp_path):
    failures = failures_for(tmp_path, {".github/workflows/ci.yml": GOOD_WORKFLOW.replace("permissions:\n  contents: read\n", "")})
    assert failures["workflow-permissions"] == ["ci.yml: no top-level permissions: block, so the token gets the repository default"], f"got {failures}"
    assert failures["workflow-pinned"] == [], f"the pin check must stay clean, got {failures}"


def test_job_level_permissions_do_not_count_as_top_level(tmp_path):
    text = GOOD_WORKFLOW.replace("permissions:\n  contents: read\n", "").replace("    steps:", "    permissions:\n      contents: read\n    steps:")
    assert len(workflow_checks.missing_permissions(text)) == 1, "indented permissions must not satisfy the top-level check"
    assert workflow_checks.missing_permissions("permissions: {}\n") == [], "an empty top-level permissions map is valid"


def test_pull_request_target_is_reported_in_both_trigger_forms(tmp_path):
    block = GOOD_WORKFLOW.replace("  push:\n", "  pull_request_target:\n")
    inline = GOOD_WORKFLOW.replace("on:\n  push:\n", "on: [pull_request_target]\n")
    assert len(workflow_checks.pull_request_target_use(block)) == 1, "block-form trigger must be reported"
    assert len(workflow_checks.pull_request_target_use(inline)) == 1, "inline-form trigger must be reported"
    assert workflow_checks.pull_request_target_use(GOOD_WORKFLOW.replace("push", "pull_request")) == [], "pull_request alone is safe"


def test_an_event_expression_in_a_block_run_is_reported(tmp_path):
    text = GOOD_WORKFLOW + '      - run: |\n          echo "${{ github.event.pull_request.title }}"\n'
    failures = failures_for(tmp_path, {".github/workflows/ci.yml": text})
    assert failures["workflow-injection"] == ["ci.yml: run block interpolates ${{ github.event.pull_request.title }}; pass it through env: instead (CICD-SEC-4)"], f"got {failures}"
    assert failures["workflow-pinned"] == [], f"the pin check must stay clean, got {failures}"


def test_an_event_expression_in_an_inline_run_and_head_ref_are_reported():
    inline = GOOD_WORKFLOW + "      - run: echo ${{ github.event.issue.title }}\n"
    head = GOOD_WORKFLOW + "      - run: git checkout ${{ github.head_ref }}\n"
    assert len(workflow_checks.script_injection(inline)) == 1, "an inline run must be scanned"
    assert len(workflow_checks.script_injection(head)) == 1, "head_ref is attacker-controlled and must be reported"


def test_an_event_expression_in_env_or_with_is_allowed():
    env = GOOD_WORKFLOW + "      - run: echo \"$TITLE\"\n        env:\n          TITLE: ${{ github.event.pull_request.title }}\n"
    with_input = GOOD_WORKFLOW + "      - uses: " + PINNED + "\n        with:\n          ref: ${{ github.event.pull_request.head.sha }}\n"
    assert workflow_checks.script_injection(env) == [], "env is the safe channel"
    assert workflow_checks.script_injection(with_input) == [], "with inputs are not shell"


def test_an_expression_after_a_run_block_ends_is_not_attributed_to_it():
    text = GOOD_WORKFLOW + "      - run: |\n          echo safe\n      - name: ${{ github.event.name }}\n"
    assert workflow_checks.script_injection(text) == [], "the block ended at the dedent"
    assert workflow_checks.run_blocks(text)[-1] == "          echo safe", f"got {workflow_checks.run_blocks(text)}"


def test_unlocked_uv_sync_is_reported(tmp_path):
    failures = failures_for(tmp_path, {".github/workflows/ci.yml": GOOD_WORKFLOW.replace("uv sync --locked", "uv sync")})
    assert failures["workflow-locked-sync"] == ["ci.yml: uv sync without --locked can change the lockfile in CI"], f"got {failures}"
    assert workflow_checks.unlocked_sync("run: uv sync --locked --all-groups") == [], "a locked sync is fine"


def test_each_missing_security_file_is_reported(tmp_path):
    write_tree(tmp_path, {".github/workflows/ci.yml": GOOD_WORKFLOW})
    errors = workflow_checks.security_file_errors(tmp_path)
    assert errors == ["SECURITY.md is missing", ".github/CODEOWNERS is missing", ".github/dependabot.yml is missing"], f"got {errors}"
    assert workflow_checks.codeowners_errors(tmp_path) == [], "a missing file is reported once, by security-files"


def test_codeowners_without_a_catch_all_is_reported(tmp_path):
    failures = failures_for(tmp_path, {".github/CODEOWNERS": "src/ @owner\n* \n"})
    assert failures["codeowners"] == [".github/CODEOWNERS has no catch-all line like '* @owner'"], f"got {failures}"
    assert failures["security-files"] == [], f"the file exists, got {failures}"


def test_a_catch_all_among_other_lines_passes(tmp_path):
    failures = failures_for(tmp_path, {".github/CODEOWNERS": "# owners\nsrc/ @a\n* @b @c\n"})
    assert failures["codeowners"] == [], f"a catch-all among other lines must pass, got {failures}"
    assert failures["dependabot"] == [], f"got {failures}"


def test_dependabot_missing_an_ecosystem_is_reported(tmp_path):
    failures = failures_for(tmp_path, {".github/dependabot.yml": "updates:\n  - package-ecosystem: github-actions\n"})
    assert failures["dependabot"] == [".github/dependabot.yml does not update uv"], f"got {failures}"
    assert failures["codeowners"] == [], f"got {failures}"
    only_uv = failures_for(tmp_path, {".github/dependabot.yml": "updates:\n  - package-ecosystem: uv\n"})
    assert only_uv["dependabot"] == [".github/dependabot.yml does not update github-actions"], f"got {only_uv}"


def test_a_tree_without_workflows_fails_instead_of_passing_vacuously(tmp_path):
    write_tree(tmp_path, {"SECURITY.md": "x\n"})
    errors = workflow_checks.pinned_errors(tmp_path)
    assert errors == [".github/workflows holds no workflows, so the check could not run"], f"got {errors}"
    assert workflow_checks.injection_errors(tmp_path) == errors, "every workflow check must fail on an empty directory"


def test_the_workflow_checks_are_registered_in_the_repo_checks():
    missing = [name for name in workflow_checks.CHECKS if name not in repo_checks.CHECKS]
    assert missing == [], f"repo_checks must run every workflow check, missing {missing}"
    assert len(workflow_checks.CHECKS) == 11, f"expected eleven workflow checks, got {sorted(workflow_checks.CHECKS)}"


def test_a_missing_required_job_is_reported(tmp_path):
    failures = failures_for(tmp_path, {".github/workflows/ci.yml": GOOD_WORKFLOW.replace("  macos:", "  macos-renamed:")})
    assert failures["workflow-required-jobs"] == ["ci.yml: job macos is missing; the ruleset requires a status check with that name"], f"got {failures}"
    assert workflow_checks.job_blocks(GOOD_WORKFLOW).keys() == {"test", "zanity", "macos"}, "job_blocks must find each top-level job"
    assert workflow_checks.job_blocks("name: ci\n") == {}, "a file without jobs has no blocks"


def test_a_workflow_without_a_jobs_section_misses_every_required_job():
    errors = workflow_checks.missing_jobs("name: ci\n")
    assert len(errors) == 3, f"every required job must be reported, got {errors}"
    assert workflow_checks.missing_jobs(GOOD_WORKFLOW) == [], "the good workflow has every required job"


def test_a_missing_python_version_file_fails_both_python_checks(tmp_path):
    write_tree(tmp_path, {**GOOD_FILES})
    (tmp_path / ".python-version").unlink()
    sourced = workflow_checks.python_source_errors(tmp_path)
    assert sourced == ["ci.yml: job test runs uv without an explicit python-version and .python-version is missing", "ci.yml: job macos runs uv without an explicit python-version and .python-version is missing"], f"got {sourced}"
    assert len(workflow_checks.python_version_errors(tmp_path)) == 1, "the pin file itself must be required"


def test_an_explicit_python_version_replaces_the_pin_file(tmp_path):
    explicit = GOOD_WORKFLOW.replace("      - run: uv sync --locked\n", "      - run: uv sync --locked\n        env:\n          UV_PYTHON: \"3.14\"\n").replace("      - run: uv run pytest\n", "      - run: uv run --python 3.14 pytest\n")
    write_tree(tmp_path, {".github/workflows/ci.yml": explicit})
    assert workflow_checks.python_source_errors(tmp_path) == [], "no pin file needed when every uv job names its Python"
    assert workflow_checks.unsourced_python_jobs(GOOD_WORKFLOW) == [f"job {name} runs uv without an explicit python-version and .python-version is missing" for name in ("test", "macos")], "without either source both uv jobs are reported"


def test_a_pin_below_requires_python_is_reported(tmp_path):
    failures = failures_for(tmp_path, {".python-version": "3.10\n"})
    assert failures["python-version-file"] == [".python-version pins 3.10, below requires-python >=3.11"], f"got {failures}"
    equal = failures_for(tmp_path, {".python-version": "3.11.4\n"})
    assert equal["python-version-file"] == [], f"a patch version at the minimum must pass, got {equal}"


def test_a_pin_with_a_higher_minor_than_the_minimum_passes(tmp_path):
    failures = failures_for(tmp_path, {".python-version": "3.13\n", "pyproject.toml": "[project]\nrequires-python = \">=3.9\"\n"})
    assert failures["python-version-file"] == [], f"3.13 satisfies >=3.9, got {failures}"
    major = failures_for(tmp_path, {".python-version": "4.0\n"})
    assert major["python-version-file"] == [], f"a higher major satisfies >=3.11, got {major}"


def test_an_unparsable_pin_or_specifier_is_reported(tmp_path):
    bad_pin = failures_for(tmp_path, {".python-version": "cpython\n"})
    assert len(bad_pin["python-version-file"]) == 1, f"a pin without major.minor must be reported, got {bad_pin}"
    bad_specifier = failures_for(tmp_path, {"pyproject.toml": "[project]\nrequires-python = \"~=3.11\"\n"})
    assert bad_specifier["python-version-file"] == ["requires-python '~=3.11' is not of the form '>=X.Y', so .python-version cannot be checked against it"], f"got {bad_specifier}"
