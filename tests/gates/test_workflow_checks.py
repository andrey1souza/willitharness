import pytest

import repo_checks
import workflow_checks
from files import write_tree

PINNED = "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1"
FIRST_JOB = workflow_checks.REQUIRED_JOBS[0]
SECOND_JOB = workflow_checks.REQUIRED_JOBS[1]
GOOD_WORKFLOW = "name: ci\non:\n  push:\npermissions:\n  contents: read\njobs:\n" + "".join(
    f"  {job}:\n    name: {workflow_checks.JOB_NAMES[job]}\n    steps:\n"
    + (f"      - uses: {PINNED} # v7\n      - run: uv sync --locked\n" if job == FIRST_JOB else "")
    + (f"      - run: uv run pytest tests/{job}\n" if job == SECOND_JOB else f"      - run: echo {job}\n")
    for job in workflow_checks.REQUIRED_JOBS
)
GOOD_SECURITY = "report privately\n\n## If something goes wrong\nThe owner acts.\n- secret: revoke\n- dependency: pin\n- workflow: disable\n- result: rebuild\n\n## Other\nx\n"
GOOD_FILES = {
    ".github/workflows/ci.yml": GOOD_WORKFLOW,
    ".python-version": "3.13\n",
    "pyproject.toml": "[project]\nrequires-python = \">=3.11\"\n",
    "SECURITY.md": GOOD_SECURITY,
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
    assert workflow_checks.required_job_errors(tmp_path) == errors, "the required jobs check must name the empty directory, not three missing jobs"


def test_the_workflow_checks_are_registered_in_the_repo_checks():
    missing = [name for name in workflow_checks.CHECKS if name not in repo_checks.CHECKS]
    assert missing == [], f"repo_checks must run every workflow check, missing {missing}"
    assert len(workflow_checks.CHECKS) == 15, f"expected fifteen workflow checks, got {sorted(workflow_checks.CHECKS)}"


def test_a_missing_required_job_is_reported(tmp_path):
    failures = failures_for(tmp_path, {".github/workflows/ci.yml": GOOD_WORKFLOW.replace(f"  {SECOND_JOB}:", f"  {SECOND_JOB}-renamed:")})
    assert failures["workflow-required-jobs"] == [f"job {SECOND_JOB} is missing in every workflow; the ruleset requires a status check with that name"], f"got {failures}"
    assert workflow_checks.job_blocks(GOOD_WORKFLOW).keys() == set(workflow_checks.REQUIRED_JOBS), "job_blocks must find each top-level job"
    assert workflow_checks.job_blocks("name: ci\n") == {}, "a file without jobs has no blocks"


def test_a_workflow_without_a_jobs_section_misses_every_required_job():
    errors = workflow_checks.missing_jobs("name: ci\n")
    assert len(errors) == len(workflow_checks.REQUIRED_JOBS), f"every required job must be reported, got {errors}"
    assert workflow_checks.missing_jobs(GOOD_WORKFLOW) == [], "the good workflow has every required job"


def test_a_missing_python_version_file_fails_both_python_checks(tmp_path):
    write_tree(tmp_path, {**GOOD_FILES})
    (tmp_path / ".python-version").unlink()
    sourced = workflow_checks.python_source_errors(tmp_path)
    assert sourced == [f"ci.yml: job {job} runs uv without an explicit python-version and .python-version is missing" for job in (FIRST_JOB, SECOND_JOB)], f"got {sourced}"
    assert len(workflow_checks.python_version_errors(tmp_path)) == 1, "the pin file itself must be required"


def test_an_explicit_python_version_replaces_the_pin_file(tmp_path):
    explicit = GOOD_WORKFLOW.replace("      - run: uv sync --locked\n", "      - run: uv sync --locked\n        env:\n          UV_PYTHON: \"3.14\"\n").replace(f"      - run: uv run pytest tests/{SECOND_JOB}\n", f"      - run: uv run --python 3.14 pytest tests/{SECOND_JOB}\n")
    write_tree(tmp_path, {".github/workflows/ci.yml": explicit})
    assert workflow_checks.python_source_errors(tmp_path) == [], "no pin file needed when every uv job names its Python"
    assert workflow_checks.unsourced_python_jobs(GOOD_WORKFLOW) == [f"job {name} runs uv without an explicit python-version and .python-version is missing" for name in (FIRST_JOB, SECOND_JOB)], "without either source both uv jobs are reported"


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


def test_a_job_with_a_generic_name_is_reported(tmp_path):
    renamed = GOOD_WORKFLOW.replace(f"name: {workflow_checks.JOB_NAMES[SECOND_JOB]}", f"name: {SECOND_JOB}")
    problems = workflow_checks.job_name_problems(renamed)
    assert len(problems) == 1 and f"job {SECOND_JOB} is named '{SECOND_JOB}'" in problems[0], f"got {problems}"
    failures = failures_for(tmp_path, {".github/workflows/ci.yml": renamed})
    assert [name for name, errors in failures.items() if errors] == ["workflow-job-names"], f"only the name check may fail, got {failures}"


def test_a_job_without_a_name_is_reported():
    unnamed = GOOD_WORKFLOW.replace(f"    name: {workflow_checks.JOB_NAMES['zanity']}\n", "")
    problems = workflow_checks.job_name_problems(unnamed)
    assert len(problems) == 1 and "job zanity is named None" in problems[0], f"got {problems}"


def test_a_job_that_has_no_expected_name_is_reported():
    extra = GOOD_WORKFLOW + "  extra:\n    name: Something\n    steps:\n      - run: echo extra\n"
    problems = workflow_checks.job_name_problems(extra)
    assert len(problems) == 1 and "job extra has no expected name" in problems[0], f"got {problems}"


def test_the_required_check_names_are_the_names_of_the_required_jobs():
    assert workflow_checks.REQUIRED_CHECK_NAMES == tuple(workflow_checks.JOB_NAMES[job] for job in workflow_checks.REQUIRED_JOBS), f"got {workflow_checks.REQUIRED_CHECK_NAMES}"
    assert len(set(workflow_checks.JOB_NAMES.values())) == len(workflow_checks.JOB_NAMES), "two jobs share a name, so a status check could not tell them apart"


def test_a_step_name_is_not_taken_for_the_job_name():
    unnamed = GOOD_WORKFLOW.replace(f"    name: {workflow_checks.JOB_NAMES['zanity']}\n", "").replace("      - run: echo zanity\n", "      - name: Zanity rules (Linux)\n        run: echo zanity\n")
    problems = workflow_checks.job_name_problems(unnamed)
    assert len(problems) == 1 and "job zanity is named None" in problems[0], f"a step name must not count as the job name, got {problems}"


def coverage_tree(tmp_path, commands, directories, extra_workflows=None):
    workflow = "name: ci\njobs:\n  tests:\n    name: x\n    steps:\n" + "".join(f"      - run: {command}\n" for command in commands)
    files = {".github/workflows/ci.yml": workflow, **{f"tests/{name}/test_x.py": "def test_x():\n    assert True\n" for name in directories}}
    files.update(extra_workflows or {})
    write_tree(tmp_path, files)
    return workflow_checks.pytest_coverage_errors(tmp_path)


def test_a_test_directory_named_by_no_job_is_reported_with_the_value_the_rule_and_the_fix(tmp_path):
    errors = coverage_tree(tmp_path, ["uv run pytest tests/unit"], ["unit", "orphan"])
    assert len(errors) == 1, f"only the orphan directory must be reported, got {errors}"
    assert "tests/orphan is run by no CI job" in errors[0] and "Rule:" in errors[0] and "Fix: add `uv run pytest tests/orphan`" in errors[0], f"got {errors}"


def test_every_directory_named_by_some_job_passes_even_across_commands_and_files(tmp_path):
    second = "name: more\njobs:\n  other:\n    name: y\n    steps:\n      - run: uv run pytest tests/golden/\n"
    errors = coverage_tree(tmp_path, ["uv run pytest tests/unit tests/bdd"], ["unit", "bdd", "golden"], {".github/workflows/more.yml": second})
    assert errors == [], f"directories named in one command, with a trailing slash, or in another workflow count, got {errors}"


def test_a_bare_pytest_run_names_no_directory(tmp_path):
    errors = coverage_tree(tmp_path, ["uv run pytest"], ["unit"])
    assert len(errors) == 1 and "tests/unit" in errors[0], f"a bare run does not name a directory, got {errors}"


def test_a_single_test_file_does_not_cover_its_directory(tmp_path):
    errors = coverage_tree(tmp_path, ["uv run pytest tests/unit/test_x.py"], ["unit"])
    assert len(errors) == 1 and "tests/unit" in errors[0], f"one file is not the directory, got {errors}"


def test_the_support_folder_and_cache_folders_need_no_job(tmp_path):
    errors = coverage_tree(tmp_path, ["uv run pytest tests/unit"], ["unit", "support", "__pycache__"])
    assert errors == [], f"support code and caches are not test directories, got {errors}"


def test_a_tree_without_tests_or_workflows_has_no_coverage_errors(tmp_path):
    write_tree(tmp_path, {"README.md": "x\n"})
    assert workflow_checks.pytest_coverage_errors(tmp_path) == [], "no tests directory means nothing to cover"
    write_tree(tmp_path, {"tests/unit/test_x.py": "def test_x():\n    assert True\n"})
    errors = workflow_checks.pytest_coverage_errors(tmp_path)
    assert len(errors) == 1 and "tests/unit" in errors[0], f"tests with no workflow at all must be reported, got {errors}"


def test_options_between_the_command_and_the_directory_are_ignored():
    text = "      - run: uv run pytest -q -x tests/unit -k fast tests/bdd\n"
    assert workflow_checks.tested_directories(text) == {"unit", "bdd"}, f"got {workflow_checks.tested_directories(text)}"
    assert workflow_checks.tested_directories("      - run: uv run python scripts/x.py tests/unit\n") == set(), "only pytest commands count"


def test_a_directory_that_pytest_is_told_to_ignore_is_not_covered():
    text = "      - run: uv run pytest --ignore tests/unit tests/bdd\n"
    assert workflow_checks.tested_directories(text) == {"bdd"}, f"an ignored directory is not run, got {workflow_checks.tested_directories(text)}"
    assert workflow_checks.tested_directories("      - run: uv run pytest --ignore=tests/unit tests/bdd\n") == {"bdd"}, "the joined form is not a plain path either"


def test_a_required_job_whose_name_says_advisory_is_reported(tmp_path):
    for word in ("advisory", "Advisory"):
        text = GOOD_WORKFLOW.replace(f"name: {workflow_checks.JOB_NAMES[FIRST_JOB]}", f"name: {workflow_checks.JOB_NAMES[FIRST_JOB]} ({word})")
        problems = workflow_checks.advisory_required_problems(text)
        assert len(problems) == 1 and f"job {FIRST_JOB} is named" in problems[0] and "Rule:" in problems[0] and "Fix:" in problems[0], f"{word!r} must be reported once, got {problems}"
    failures = failures_for(tmp_path, {".github/workflows/ci.yml": GOOD_WORKFLOW.replace(f"name: {workflow_checks.JOB_NAMES[FIRST_JOB]}", f"name: {workflow_checks.JOB_NAMES[FIRST_JOB]} (advisory)")})
    assert failures["workflow-advisory-not-required"] != [], f"the registered check must report it, got {failures}"


def test_a_job_that_is_advisory_and_not_required_is_not_reported():
    advisory = workflow_checks.JOB_NAMES["latest-python-linux"]
    text = GOOD_WORKFLOW + f"  latest-python-linux:\n    name: {advisory}\n    steps:\n      - run: echo latest\n"
    assert "advisory" in advisory, f"the latest-Python job must say advisory, got {advisory!r}"
    assert workflow_checks.advisory_required_problems(text) == [], "an advisory job that is not required is the intended state"


def test_no_required_name_says_advisory_and_every_latest_python_name_does():
    required_with_the_word = [job for job in workflow_checks.REQUIRED_JOBS if "advisory" in workflow_checks.JOB_NAMES[job].lower()]
    assert required_with_the_word == [], f"required checks must not call themselves advisory, got {required_with_the_word}"
    latest = [job for job in workflow_checks.JOB_NAMES if job.startswith("latest-python")]
    assert latest and all("advisory, not required" in workflow_checks.JOB_NAMES[job] for job in latest), f"latest-Python jobs must say advisory, not required, got {latest}"
    assert not set(latest) & set(workflow_checks.REQUIRED_JOBS), f"latest-Python jobs must not be required, got {latest}"


def test_the_secret_scan_is_a_required_job():
    assert "gitleaks" in workflow_checks.REQUIRED_JOBS, f"the user made the secret scan required, got {workflow_checks.REQUIRED_JOBS}"


def length_problems(problems):
    return [problem for problem in problems if "characters, above" in problem]


def test_a_job_name_over_the_github_limit_is_reported_with_its_length():
    long_name = "x" * (workflow_checks.MAX_JOB_NAME_LENGTH + 1)
    text = GOOD_WORKFLOW.replace(f"name: {workflow_checks.JOB_NAMES['zanity']}", f"name: {long_name}")
    found = length_problems(workflow_checks.job_name_problems(text))
    assert len(found) == 1 and f"{len(long_name)} characters" in found[0], f"a {len(long_name)}-character name must be reported once, got {found}"


def test_a_job_name_of_exactly_the_github_limit_is_not_reported_for_its_length():
    exact_name = "x" * workflow_checks.MAX_JOB_NAME_LENGTH
    text = GOOD_WORKFLOW.replace(f"name: {workflow_checks.JOB_NAMES['zanity']}", f"name: {exact_name}")
    found = length_problems(workflow_checks.job_name_problems(text))
    assert found == [], f"a name of exactly {workflow_checks.MAX_JOB_NAME_LENGTH} characters is not cut, got {found}"


def test_every_expected_job_name_fits_in_the_github_limit():
    too_long = {job: len(name) for job, name in workflow_checks.JOB_NAMES.items() if len(name) > workflow_checks.MAX_JOB_NAME_LENGTH}
    assert too_long == {}, f"GitHub cuts names above {workflow_checks.MAX_JOB_NAME_LENGTH} characters, so these lose their end: {too_long}"


def test_the_github_limit_is_one_hundred_characters():
    assert workflow_checks.MAX_JOB_NAME_LENGTH == 100, f"GitHub showed a 105-character name cut to 100, got limit {workflow_checks.MAX_JOB_NAME_LENGTH}"

SECOND_WORKFLOW = "name: pages\non:\n  push:\npermissions:\n  contents: read\njobs:\n  build:\n    name: " + workflow_checks.JOB_NAMES["build"] + "\n    steps:\n      - run: echo build\n"
SECOND_JOB_BLOCK = f"  {SECOND_JOB}:\n    name: {workflow_checks.JOB_NAMES[SECOND_JOB]}\n    steps:\n      - run: uv run pytest tests/{SECOND_JOB}\n"


def test_a_second_workflow_without_the_required_jobs_does_not_fail_the_required_jobs_check(tmp_path):
    failures = failures_for(tmp_path, {".github/workflows/pages.yml": SECOND_WORKFLOW})
    assert failures["workflow-required-jobs"] == [], f"the required jobs live in ci.yml, got {failures['workflow-required-jobs']}"
    assert failures["workflow-job-names"] == [], f"the pages jobs are in the name table, got {failures['workflow-job-names']}"


def test_required_jobs_may_be_split_across_workflows_and_a_job_missing_everywhere_is_reported_once(tmp_path):
    assert SECOND_JOB_BLOCK in GOOD_WORKFLOW, f"the fixture must hold the {SECOND_JOB} job"
    split = GOOD_WORKFLOW.replace(SECOND_JOB_BLOCK, "")
    elsewhere = "name: other\non:\n  push:\npermissions:\n  contents: read\njobs:\n" + SECOND_JOB_BLOCK
    failures = failures_for(tmp_path, {".github/workflows/ci.yml": split, ".github/workflows/other.yml": elsewhere})
    assert failures["workflow-required-jobs"] == [], f"a required job in another file counts, got {failures['workflow-required-jobs']}"
    expected = [f"job {SECOND_JOB} is missing in every workflow; the ruleset requires a status check with that name"]
    assert workflow_checks.missing_jobs_across([split, SECOND_WORKFLOW]) == expected, "a job missing in every file is reported once, not once per file"


def test_a_security_policy_without_the_incident_section_is_reported(tmp_path):
    failures = failures_for(tmp_path, {"SECURITY.md": "report privately\n"})
    assert failures["security-policy-headings"] == ["SECURITY.md has no '## If something goes wrong' section, so nobody knows who acts or what to do first"], f"got {failures}"
    assert failures["security-files"] == [], f"the file exists, got {failures}"


@pytest.mark.parametrize("event", ["secret", "dependency", "workflow", "result"])
def test_an_incident_section_missing_an_event_is_reported(tmp_path, event):
    failures = failures_for(tmp_path, {"SECURITY.md": GOOD_SECURITY.replace(event, "other")})
    assert failures["security-policy-headings"] == [f"SECURITY.md section '## If something goes wrong' does not name the event {event!r}"], f"got {failures}"
    assert sum(1 for errors in failures.values() if errors) == 1, f"only the policy check may fail, got {failures}"


def test_an_event_word_outside_the_incident_section_does_not_count(tmp_path):
    outside = "secret dependency workflow result\n\n## If something goes wrong\nThe owner acts.\n"
    failures = failures_for(tmp_path, {"SECURITY.md": outside})
    assert len(failures["security-policy-headings"]) == 4, f"words above the section must not count, got {failures}"
    after = "## If something goes wrong\nThe owner acts.\n\n## Other\nsecret dependency workflow result\n"
    assert len(workflow_checks.security_policy_errors(write_and_root(tmp_path, after))) == 4, "words after the section must not count"


def write_and_root(tmp_path, text):
    write_tree(tmp_path, {"SECURITY.md": text})
    return tmp_path


def test_an_incident_section_above_twelve_lines_is_reported_and_twelve_pass(tmp_path):
    twelve = GOOD_SECURITY.replace("The owner acts.\n", "The owner acts.\n" + "x\n" * 7)
    assert workflow_checks.security_policy_errors(write_and_root(tmp_path, twelve.replace("\n\n## Other\nx\n", "\n"))) == [], "twelve lines must pass"
    errors = workflow_checks.security_policy_errors(write_and_root(tmp_path, twelve.replace("The owner acts.\n", "The owner acts.\nx\n")))
    assert errors == ["SECURITY.md section '## If something goes wrong' has 13 lines, above 12. Rule: a plan read in a crisis stays short. Fix: shorten it"], f"got {errors}"
