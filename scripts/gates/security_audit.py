import argparse
import json
import subprocess
import sys

import workflow_checks

EXIT_PASSED = 0
EXIT_FAILED = 1
GH_COMMAND = "gh"
REPO_ENDPOINT = "repos/{owner}/{repo}"
RULESETS_ENDPOINT = "repos/{owner}/{repo}/rulesets"
ACTIONS_ENDPOINT = "repos/{owner}/{repo}/actions/permissions"
WORKFLOW_ENDPOINT = "repos/{owner}/{repo}/actions/permissions/workflow"
PROTECTED_BRANCH = "main"
BRANCH_TARGET = "branch"
RULESET_ACTIVE = "active"
BRANCH_REFS = ("~DEFAULT_BRANCH", "~ALL", f"refs/heads/{PROTECTED_BRANCH}")
REQUIRED_RULES = {
    "pull request required": "pull_request",
    "signed commits required": "required_signatures",
    "linear history required": "required_linear_history",
    "force push blocked": "non_fast_forward",
    "deletion blocked": "deletion",
    "status checks required": "required_status_checks",
}
CODE_OWNER_PARAMETER = "require_code_owner_review"
STRICT_PARAMETER = "strict_required_status_checks_policy"
PULL_REQUEST_RULE = REQUIRED_RULES["pull request required"]
STATUS_CHECKS_RULE = REQUIRED_RULES["status checks required"]
REQUIRED_CHECKS = workflow_checks.REQUIRED_CHECK_NAMES
ENABLED = "enabled"
REQUIRED_ANALYSIS = {
    "secret scanning enabled": "secret_scanning",
    "push protection enabled": "secret_scanning_push_protection",
    "dependabot security updates enabled": "dependabot_security_updates",
}
SHA_PINNING_KEY = "sha_pinning_required"
DEFAULT_PERMISSIONS_KEY = "default_workflow_permissions"
READ_PERMISSIONS = "read"
SETTING_KEYS = ("security_and_analysis", "rulesets", "actions", "workflow")


class GhFailed(Exception):
    pass


def protects_main(ruleset):
    assert isinstance(ruleset, dict), f"a ruleset must be a dict, got {type(ruleset).__name__}. Fix: pass the ruleset body from gh api."
    assert ruleset.get("target") is not None or ruleset == {}, f"ruleset {ruleset.get('name')!r} has no target. Fix: pass the full ruleset body, not the list summary."
    if ruleset.get("enforcement") != RULESET_ACTIVE or ruleset.get("target") != BRANCH_TARGET:
        return False
    ref_name = (ruleset.get("conditions") or {}).get("ref_name") or {}
    included = any(ref in BRANCH_REFS for ref in ref_name.get("include", []))
    excluded = any(ref in BRANCH_REFS for ref in ref_name.get("exclude", []))
    return included and not excluded


def enforced_rules(rulesets):
    assert isinstance(rulesets, list), f"rulesets must be a list, got {type(rulesets).__name__}. Fix: pass the ruleset bodies."
    assert all(isinstance(ruleset, dict) for ruleset in rulesets), f"every ruleset must be a dict, got {rulesets!r}"
    return {rule["type"]: rule.get("parameters") or {} for ruleset in rulesets if protects_main(ruleset) for rule in ruleset.get("rules", [])}


def ruleset_errors(rulesets):
    assert isinstance(rulesets, list), f"rulesets must be a list, got {type(rulesets).__name__}. Fix: pass the ruleset bodies."
    rules = enforced_rules(rulesets)
    errors = [] if rules else [f"no active ruleset protects {PROTECTED_BRANCH}"]
    errors += [f"{name}: ruleset has no {rule_type} rule" for name, rule_type in REQUIRED_RULES.items() if rule_type not in rules]
    if PULL_REQUEST_RULE in rules and rules[PULL_REQUEST_RULE].get(CODE_OWNER_PARAMETER) is not True:
        errors.append("code owner review required: the pull_request rule does not set it")
    if STATUS_CHECKS_RULE in rules:
        contexts = [check.get("context") for check in rules[STATUS_CHECKS_RULE].get("required_status_checks", [])]
        errors += [f"required status check {name!r} is missing" for name in REQUIRED_CHECKS if name not in contexts]
        strict = rules[STATUS_CHECKS_RULE].get(STRICT_PARAMETER)
        if strict is not True:
            errors.append(f"{STRICT_PARAMETER} is {strict!r}, not True. Rule: a pull request must be up to date with {PROTECTED_BRANCH} before it merges, because breaking {PROTECTED_BRANCH} is never acceptable. Fix: set it to true in the ruleset")
    assert all(isinstance(error, str) for error in errors), f"errors must be text, got {errors!r}"
    return errors


def settings_errors(settings):
    assert isinstance(settings, dict), f"settings must be a dict, got {type(settings).__name__}. Fix: pass collect_settings output."
    missing = [key for key in SETTING_KEYS if key not in settings]
    assert not missing, f"settings lacks {missing}. Rule: every expectation reads one of {SETTING_KEYS}. Fix: pass all four."
    analysis = settings["security_and_analysis"] or {}
    errors = ruleset_errors(settings["rulesets"])
    errors += [f"{name}: {key} is not {ENABLED}" for name, key in REQUIRED_ANALYSIS.items() if (analysis.get(key) or {}).get("status") != ENABLED]
    if settings["actions"].get(SHA_PINNING_KEY) is not True:
        errors.append(f"actions SHA pinning required: {SHA_PINNING_KEY} is not true")
    if settings["workflow"].get(DEFAULT_PERMISSIONS_KEY) != READ_PERMISSIONS:
        errors.append(f"default workflow permissions read: {DEFAULT_PERMISSIONS_KEY} is {settings['workflow'].get(DEFAULT_PERMISSIONS_KEY)!r}")
    assert all(isinstance(error, str) for error in errors), f"errors must be text, got {errors!r}"
    return errors


def gh_json(gh_command, endpoint):
    assert endpoint.startswith("repos/"), f"endpoint {endpoint!r} must start with repos/. Rule: the audit only reads one repository. Fix: use the endpoint constants."
    assert gh_command, "gh_command is empty. Fix: pass the gh executable."
    completed = subprocess.run([gh_command, "api", endpoint], capture_output=True, text=True)
    if completed.returncode != 0:
        raise GhFailed(f"gh api {endpoint} exited {completed.returncode}: {completed.stderr.strip()}")
    return json.loads(completed.stdout)


def collect_settings(gh_command):
    assert gh_command, "gh_command is empty. Fix: pass the gh executable."
    summaries = gh_json(gh_command, RULESETS_ENDPOINT)
    settings = {
        "security_and_analysis": gh_json(gh_command, REPO_ENDPOINT).get("security_and_analysis"),
        "rulesets": [gh_json(gh_command, f"{RULESETS_ENDPOINT}/{summary['id']}") for summary in summaries],
        "actions": gh_json(gh_command, ACTIONS_ENDPOINT),
        "workflow": gh_json(gh_command, WORKFLOW_ENDPOINT),
    }
    assert set(settings) == set(SETTING_KEYS), f"collected keys {sorted(settings)} differ from {SETTING_KEYS}"
    return settings


def main(argv):
    assert isinstance(argv, list), f"main needs a list of arguments, got {argv!r}. Fix: pass sys.argv[1:]."
    assert all(isinstance(item, str) for item in argv), f"every argument must be text, got {argv!r}"
    parser = argparse.ArgumentParser(prog="security_audit")
    parser.add_argument("--gh", default=GH_COMMAND)
    arguments = parser.parse_args(argv)
    try:
        errors = settings_errors(collect_settings(arguments.gh))
    except GhFailed as failure:
        print(f"security-audit: {failure}")
        return EXIT_FAILED
    for error in errors:
        print(f"security-audit: {error}")
    if errors:
        return EXIT_FAILED
    print("security-audit: every expectation holds")
    return EXIT_PASSED


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
