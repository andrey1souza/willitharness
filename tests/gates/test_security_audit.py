import json
import stat

import security_audit
import workflow_checks
from files import write_tree

ALL_CHECKS = [{"context": name} for name in workflow_checks.REQUIRED_CHECK_NAMES]


def status_rule(checks, strict=True):
    return {"type": "required_status_checks", "parameters": {"required_status_checks": checks, "strict_required_status_checks_policy": strict}}


GOOD_RULES = [
    {"type": "pull_request", "parameters": {"required_approving_review_count": 0}},
    {"type": "required_signatures"},
    {"type": "required_linear_history"},
    {"type": "non_fast_forward"},
    {"type": "deletion"},
    status_rule(ALL_CHECKS),
]
GOOD_RULESET = {
    "id": 7,
    "name": "main",
    "target": "branch",
    "enforcement": "active",
    "conditions": {"ref_name": {"include": ["~DEFAULT_BRANCH"], "exclude": []}},
    "rules": GOOD_RULES,
}
ENABLED = {"status": "enabled"}
GOOD_ANALYSIS = {"secret_scanning": ENABLED, "secret_scanning_push_protection": ENABLED, "dependabot_security_updates": ENABLED}
GOOD_SETTINGS = {
    "security_and_analysis": GOOD_ANALYSIS,
    "rulesets": [GOOD_RULESET],
    "actions": {"sha_pinning_required": True},
    "workflow": {"default_workflow_permissions": "read"},
}


def replaced(key, value):
    return {**GOOD_SETTINGS, key: value}


def without_rule(rule_type):
    return replaced("rulesets", [{**GOOD_RULESET, "rules": [rule for rule in GOOD_RULES if rule["type"] != rule_type]}])


def test_good_settings_have_no_errors():
    errors = security_audit.settings_errors(GOOD_SETTINGS)
    assert errors == [], f"good settings must pass, got {errors}"


def test_no_ruleset_lists_every_rule_as_missing():
    errors = security_audit.settings_errors(replaced("rulesets", []))
    assert errors[0] == "no active ruleset protects main", f"got {errors}"
    assert len(errors) == 7, f"one error for the missing ruleset and six for the rules, got {errors}"


def test_each_missing_rule_is_named():
    expected = {
        "pull_request": "pull request required: ruleset has no pull_request rule",
        "required_signatures": "signed commits required: ruleset has no required_signatures rule",
        "required_linear_history": "linear history required: ruleset has no required_linear_history rule",
        "non_fast_forward": "force push blocked: ruleset has no non_fast_forward rule",
        "deletion": "deletion blocked: ruleset has no deletion rule",
        "required_status_checks": "status checks required: ruleset has no required_status_checks rule",
    }
    for rule_type, message in expected.items():
        errors = security_audit.settings_errors(without_rule(rule_type))
        assert errors == [message], f"dropping {rule_type} must give exactly {message!r}, got {errors}"


def test_a_single_maintainer_ruleset_without_human_approval_passes():
    single_maintainer = [{"type": "pull_request", "parameters": {"required_approving_review_count": 0, "require_code_owner_review": False}}, *GOOD_RULES[1:]]
    errors = security_audit.settings_errors(replaced("rulesets", [{**GOOD_RULESET, "rules": single_maintainer}]))
    assert errors == [], f"zero approvals and no code owner review is the intended state, got {errors}"


def test_each_required_status_check_is_needed():
    assert len(ALL_CHECKS) == len(workflow_checks.REQUIRED_JOBS), f"one context per required job, got {ALL_CHECKS}"
    for index, check in enumerate(ALL_CHECKS):
        others = [other for position, other in enumerate(ALL_CHECKS) if position != index]
        errors = security_audit.settings_errors(replaced("rulesets", [{**GOOD_RULESET, "rules": [*GOOD_RULES[:-1], status_rule(others)]}]))
        assert errors == [f"required status check {check['context']!r} is missing"], f"dropping {check['context']!r} must give exactly one error, got {errors}"


def test_status_checks_must_require_an_up_to_date_branch():
    for strict in (False, None, "true", 1):
        weak = [*GOOD_RULES[:-1], status_rule(ALL_CHECKS, strict)]
        errors = security_audit.settings_errors(replaced("rulesets", [{**GOOD_RULESET, "rules": weak}]))
        assert len(errors) == 1 and errors[0].startswith(f"strict_required_status_checks_policy is {strict!r}, not True"), f"strict={strict!r} must fail with its value, got {errors}"
        assert "Rule:" in errors[0] and "Fix:" in errors[0], f"the message needs the rule and the fix, got {errors[0]!r}"
    absent = [*GOOD_RULES[:-1], {"type": "required_status_checks", "parameters": {"required_status_checks": ALL_CHECKS}}]
    errors = security_audit.settings_errors(replaced("rulesets", [{**GOOD_RULESET, "rules": absent}]))
    assert len(errors) == 1 and "is None, not True" in errors[0], f"an absent strict setting must fail, got {errors}"
    assert security_audit.settings_errors(replaced("rulesets", [{**GOOD_RULESET, "rules": GOOD_RULES}])) == [], "strict true must pass"


def test_an_inactive_or_wrong_target_ruleset_does_not_count():
    for change in ({"enforcement": "evaluate"}, {"enforcement": "disabled"}, {"target": "tag"}):
        errors = security_audit.settings_errors(replaced("rulesets", [{**GOOD_RULESET, **change}]))
        assert errors[0] == "no active ruleset protects main", f"{change} must not protect main, got {errors}"


def test_a_ruleset_that_excludes_or_misses_main_does_not_count():
    excluded = {"ref_name": {"include": ["~ALL"], "exclude": ["refs/heads/main"]}}
    other = {"ref_name": {"include": ["refs/heads/release"], "exclude": []}}
    for conditions in (excluded, other, {}):
        errors = security_audit.settings_errors(replaced("rulesets", [{**GOOD_RULESET, "conditions": conditions}]))
        assert errors[0] == "no active ruleset protects main", f"{conditions} must not protect main, got {errors}"


def test_rules_from_two_rulesets_add_up():
    first = {**GOOD_RULESET, "rules": GOOD_RULES[:3]}
    second = {**GOOD_RULESET, "id": 8, "rules": GOOD_RULES[3:]}
    errors = security_audit.settings_errors(replaced("rulesets", [first, second]))
    assert errors == [], f"two active rulesets together satisfy the table, got {errors}"


def test_each_analysis_feature_must_be_enabled():
    expected = {
        "secret_scanning": "secret scanning enabled: secret_scanning is not enabled",
        "secret_scanning_push_protection": "push protection enabled: secret_scanning_push_protection is not enabled",
        "dependabot_security_updates": "dependabot security updates enabled: dependabot_security_updates is not enabled",
    }
    for key, message in expected.items():
        errors = security_audit.settings_errors(replaced("security_and_analysis", {**GOOD_ANALYSIS, key: {"status": "disabled"}}))
        assert errors == [message], f"disabling {key} must give {message!r}, got {errors}"
    assert len(security_audit.settings_errors(replaced("security_and_analysis", None))) == 3, "a repository with no analysis block fails all three"


def test_sha_pinning_must_be_true():
    for actions in ({"sha_pinning_required": False}, {}):
        errors = security_audit.settings_errors(replaced("actions", actions))
        assert errors == ["actions SHA pinning required: sha_pinning_required is not true"], f"{actions} must fail, got {errors}"
    assert security_audit.settings_errors(GOOD_SETTINGS) == [], "true must pass"


def test_default_workflow_permissions_must_be_read():
    errors = security_audit.settings_errors(replaced("workflow", {"default_workflow_permissions": "write"}))
    assert errors == ["default workflow permissions read: default_workflow_permissions is 'write'"], f"got {errors}"
    assert len(security_audit.settings_errors(replaced("workflow", {}))) == 1, "an absent value must fail"


def fake_gh(folder, responses, exit_code):
    cases = "\n".join(f'  "api {endpoint}") cat "$here/{name}";;' for endpoint, name in security_audit_endpoints().items())
    script = f'#!/bin/sh\nhere="$(dirname "$0")"\ncase "$*" in\n{cases}\n  *) echo "unexpected $*" >&2; exit {exit_code};;\nesac\n'
    write_tree(folder, {name: json.dumps(body) for name, body in responses.items()})
    executable = folder / "gh"
    executable.write_text(script)
    executable.chmod(executable.stat().st_mode | stat.S_IXUSR)
    return executable


def security_audit_endpoints():
    return {
        security_audit.REPO_ENDPOINT: "repo.json",
        security_audit.RULESETS_ENDPOINT: "rulesets.json",
        f"{security_audit.RULESETS_ENDPOINT}/7": "ruleset-7.json",
        security_audit.ACTIONS_ENDPOINT: "actions.json",
        security_audit.WORKFLOW_ENDPOINT: "workflow.json",
    }


GOOD_RESPONSES = {
    "repo.json": {"security_and_analysis": GOOD_ANALYSIS},
    "rulesets.json": [{"id": 7, "name": "main"}],
    "ruleset-7.json": GOOD_RULESET,
    "actions.json": GOOD_SETTINGS["actions"],
    "workflow.json": GOOD_SETTINGS["workflow"],
}


def test_collect_settings_reads_every_endpoint_through_gh(tmp_path):
    gh = fake_gh(tmp_path, GOOD_RESPONSES, 1)
    settings = security_audit.collect_settings(str(gh))
    assert settings == GOOD_SETTINGS, f"collected settings differ: {settings}"
    assert security_audit.settings_errors(settings) == [], "collected good settings must pass"


def test_main_passes_against_a_good_fake_gh(tmp_path, capsys):
    gh = fake_gh(tmp_path, GOOD_RESPONSES, 1)
    code = security_audit.main(["--gh", str(gh)])
    output = capsys.readouterr().out
    assert code == security_audit.EXIT_PASSED, f"good settings must exit 0, output {output!r}"
    assert output == "security-audit: every expectation holds\n", f"got {output!r}"


def test_main_fails_and_lists_every_failure_against_a_bad_fake_gh(tmp_path, capsys):
    bad = {**GOOD_RESPONSES, "rulesets.json": [], "actions.json": {"sha_pinning_required": False}}
    gh = fake_gh(tmp_path, bad, 1)
    code = security_audit.main(["--gh", str(gh)])
    lines = capsys.readouterr().out.splitlines()
    assert code == security_audit.EXIT_FAILED, f"bad settings must exit 1, got {code}"
    assert len(lines) == 8 and lines[-1] == "security-audit: actions SHA pinning required: sha_pinning_required is not true", f"got {lines}"


def test_main_fails_when_gh_fails(tmp_path, capsys):
    gh = fake_gh(tmp_path, {"repo.json": {}}, 4)
    code = security_audit.main(["--gh", str(gh)])
    output = capsys.readouterr().out
    assert code == security_audit.EXIT_FAILED, f"a failing gh must exit 1, got {code}"
    assert output.startswith("security-audit: gh api repos/{owner}/{repo}/rulesets exited 1"), f"got {output!r}"
