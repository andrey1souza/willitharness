import json
from dataclasses import dataclass, replace

import pytest
from cli_runner import run_cli

from willitharness.component_arms import ARM_COMPONENT, ARM_NOISE, ARM_NOTHING, ARM_PLACEBO, ARM_PROMPT
from willitharness.plan import plan_fingerprint, read_plan
from willitharness.plan_builder import filler_text

EXIT_OK = 0
EXIT_REFUSED = 1
BUILD_PLAN = "build-plan"
RULE_MARKER = "Rule:"
FIX_MARKER = "Fix:"
SKILL_NAME = "backup"
SKILL_BODY = "Back up the file before you edit it.\nName the copy with a date."
SKILL_TEXT = f"---\nname: {SKILL_NAME}\ndescription: Back up files\n---\n{SKILL_BODY}\n"
HOOK_TEXT = "Remember to run the tests before you commit."
HOOK_COMMAND = f"printf '{HOOK_TEXT}'"
HOOK_EVENT = "UserPromptSubmit"
DETECTOR = ["git push --force"]
BUDGET = "1.0"
RUN_CAP = "0.1"
SKILL_ARGUMENTS = ["--skill", SKILL_NAME]
HOOK_ARGUMENTS = ["--hook", HOOK_EVENT, "--run-hook"]
MARKER_FILE = "hook-ran.marker"
EVERY_ARM = {ARM_NOTHING, ARM_NOISE, ARM_PROMPT, ARM_COMPONENT}
PROMPT_FILE = "system-prompt.txt"


@dataclass(frozen=True)
class Site:
    capsys: object
    monkeypatch: object


@pytest.fixture
def cli(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    return Site(capsys, monkeypatch)


def write_component_project(root, hook_command):
    assert hook_command, "write_component_project needs a hook command. Fix: pass HOOK_COMMAND or another command."
    skill = root / "project" / ".claude" / "skills" / SKILL_NAME
    skill.mkdir(parents=True, exist_ok=True)
    (skill / "SKILL.md").write_text(SKILL_TEXT)
    settings = {"hooks": {HOOK_EVENT: [{"hooks": [{"type": "command", "command": hook_command}]}]}}
    (root / "project" / ".claude" / "settings.json").write_text(json.dumps(settings))
    detector = root / "detector.json"
    detector.write_text(json.dumps(DETECTOR))
    return root / "project", detector


def cli_arguments(root, component_arguments, extra=()):
    project, detector = root / "project", root / "detector.json"
    return [BUILD_PLAN, *component_arguments, "--project", str(project), "--detector", str(detector), "--out", str(root / "out"), "--budget-usd", BUDGET, "--run-cap-usd", RUN_CAP, *extra]


def build_from_cli(root, cli, component_arguments, extra=()):
    write_component_project(root, HOOK_COMMAND)
    return run_cli(cli.capsys, cli_arguments(root, component_arguments, extra))


def built_arms(root):
    return {arm["label"]: arm for arm in json.loads((root / "out" / "plan.json").read_text())["arms"]}


def overlay_of(root, label):
    return root / "out" / built_arms(root)[label]["overlay"]


def assert_refused_with_rule_and_fix(result):
    code, _, error = result
    assert code == EXIT_REFUSED, f"expected exit {EXIT_REFUSED}, got {code}: {error}"
    assert RULE_MARKER in error and error.strip().split(FIX_MARKER)[-1].strip(), f"the refusal has no Rule and Fix: {error!r}"


def assert_plan_checks(root, cli):
    out = root / "out"
    assert out.is_dir(), f"{out} was not built. Rule: plan check reads a built plan."
    cli.monkeypatch.chdir(out)
    code = run_cli(cli.capsys, ["plan", "check", "plan.json"])[0]
    cli.monkeypatch.chdir(root)
    assert code == EXIT_OK, f"plan check exited {code} for the built plan"


def test_a_skill_gives_arms_n_n2_p_and_c_and_the_plan_checks(tmp_path, cli):
    code, _, error = build_from_cli(tmp_path, cli, SKILL_ARGUMENTS)
    assert code == EXIT_OK, error
    arms = built_arms(tmp_path)
    assert set(arms) == EVERY_ARM, f"plan arms {set(arms)!r} differ from {EVERY_ARM!r}. Fix: build arms N, N2, P and C."
    assert arms[ARM_NOTHING]["role"] == "leave_one_out", f"arm N has role {arms[ARM_NOTHING]['role']!r}"
    assert arms[ARM_NOISE]["role"] == f"noise_of:{ARM_NOTHING}", f"arm N2 has role {arms[ARM_NOISE]['role']!r}"
    assert arms[ARM_NOISE]["overlay"] == arms[ARM_NOTHING]["overlay"], f"N2 and N have different overlays: {arms!r}"
    assert (arms[ARM_PROMPT]["role"], arms[ARM_PROMPT]["channel"]) == ("rule", "system_prompt"), f"arm P is {arms[ARM_PROMPT]!r}"
    assert (arms[ARM_COMPONENT]["role"], arms[ARM_COMPONENT]["channel"]) == ("rule", "skill"), f"arm C is {arms[ARM_COMPONENT]!r}"
    assert (overlay_of(tmp_path, ARM_PROMPT) / PROMPT_FILE).read_text() == SKILL_BODY, "arm P does not hold the body of the skill"
    installed = overlay_of(tmp_path, ARM_COMPONENT) / ".claude" / "skills" / SKILL_NAME / "SKILL.md"
    assert installed.read_text() == SKILL_TEXT, f"arm C holds {installed.read_text()!r}, not the real skill"
    assert list(overlay_of(tmp_path, ARM_NOTHING).iterdir()) == [], "arm N is not empty"
    assert_plan_checks(tmp_path, cli)


def test_the_detector_sits_in_the_plan_rule(tmp_path, cli):
    build_from_cli(tmp_path, cli, SKILL_ARGUMENTS)
    plan = read_plan(tmp_path / "out", "plan.json")
    assert plan.rule.detector.actions == tuple(DETECTOR), f"the plan holds detector {plan.rule.detector!r}, not {DETECTOR!r}. Fix: write the detector of --detector into the plan rule."


def test_a_hook_gives_arm_p_the_text_the_hook_returns(tmp_path, cli):
    code, _, error = build_from_cli(tmp_path, cli, HOOK_ARGUMENTS)
    assert code == EXIT_OK, error
    arms = built_arms(tmp_path)
    assert set(arms) == EVERY_ARM, f"plan arms {set(arms)!r} differ from {EVERY_ARM!r}. Fix: build arms N, N2, P and C."
    assert arms[ARM_COMPONENT]["channel"] == "hook", f"arm C is {arms[ARM_COMPONENT]!r}"
    assert (overlay_of(tmp_path, ARM_PROMPT) / PROMPT_FILE).read_text() == HOOK_TEXT, "arm P does not hold the hook output"
    settings = json.loads((overlay_of(tmp_path, ARM_COMPONENT) / ".claude" / "settings.json").read_text())
    assert settings["hooks"][HOOK_EVENT][0]["hooks"][0]["command"] == HOOK_COMMAND, f"arm C holds {settings!r}"
    assert_plan_checks(tmp_path, cli)


def test_a_hook_never_runs_without_run_hook(tmp_path, cli):
    write_component_project(tmp_path, f"touch {tmp_path / MARKER_FILE}; printf text")
    result = run_cli(cli.capsys, cli_arguments(tmp_path, ["--hook", HOOK_EVENT]))
    assert_refused_with_rule_and_fix(result)
    assert not (tmp_path / MARKER_FILE).exists(), "the hook ran without --run-hook"
    assert not (tmp_path / "out").exists(), "a refused build wrote an out folder"


def test_the_option_placebo_adds_filler_of_the_same_length(tmp_path, cli):
    code, _, error = build_from_cli(tmp_path, cli, SKILL_ARGUMENTS, ["--placebo"])
    assert code == EXIT_OK, error
    arms = built_arms(tmp_path)
    assert set(arms) == EVERY_ARM | {ARM_PLACEBO}, f"expected the placebo arm, got {set(arms)!r}"
    filler = (overlay_of(tmp_path, ARM_PLACEBO) / PROMPT_FILE).read_text()
    assert len(filler) == len(SKILL_BODY), f"the filler has {len(filler)} characters, the text {len(SKILL_BODY)}"
    assert filler != SKILL_BODY, f"the filler {filler!r} is the component text {SKILL_BODY!r}"
    assert (arms[ARM_PLACEBO]["role"], arms[ARM_PLACEBO]["channel"]) == ("rule", "system_prompt"), f"arm PL is {arms[ARM_PLACEBO]!r}"
    assert_plan_checks(tmp_path, cli)


def test_no_placebo_arm_without_the_option(tmp_path, cli):
    build_from_cli(tmp_path, cli, SKILL_ARGUMENTS)
    assert ARM_PLACEBO not in built_arms(tmp_path), f"the plan has arm {ARM_PLACEBO} in {tmp_path} without --placebo"


@pytest.mark.parametrize("length", [1, 7, 51, 52, 53, 500])
def test_filler_has_exactly_the_requested_length(length):
    assert len(filler_text(length)) == length, f"filler_text({length}) has the wrong length"


def test_a_plan_without_a_detector_is_refused_and_nothing_is_written(tmp_path, cli):
    write_component_project(tmp_path, HOOK_COMMAND)
    arguments = cli_arguments(tmp_path, SKILL_ARGUMENTS)
    del arguments[arguments.index("--detector"):arguments.index("--detector") + 2]
    result = run_cli(cli.capsys, arguments)
    assert_refused_with_rule_and_fix(result)
    assert "declared in the plan before the first run" in result[2], f"the refusal does not name the detector rule: {result[2]!r}"
    assert not (tmp_path / "out").exists(), "a refused build wrote an out folder"


@pytest.mark.parametrize("text", ["not json", json.dumps({"kind": "wrong", "actions": ["git push"]})])
def test_a_detector_that_is_not_valid_is_refused_and_nothing_is_written(tmp_path, cli, text):
    _, detector = write_component_project(tmp_path, HOOK_COMMAND)
    detector.write_text(text)
    result = run_cli(cli.capsys, cli_arguments(tmp_path, SKILL_ARGUMENTS))
    assert_refused_with_rule_and_fix(result)
    assert not (tmp_path / "out").exists(), "a refused build wrote an out folder"


def test_an_existing_plan_is_never_overwritten(tmp_path, cli):
    build_from_cli(tmp_path, cli, SKILL_ARGUMENTS)
    before = (tmp_path / "out" / "plan.json").read_text()
    arguments = cli_arguments(tmp_path, SKILL_ARGUMENTS)
    arguments[arguments.index("--budget-usd") + 1] = "2.0"
    assert_refused_with_rule_and_fix(run_cli(cli.capsys, arguments))
    assert (tmp_path / "out" / "plan.json").read_text() == before, "the second build changed plan.json"


def test_an_unknown_skill_is_refused(tmp_path, cli):
    result = build_from_cli(tmp_path, cli, ["--skill", "missing"])
    assert_refused_with_rule_and_fix(result)
    assert "is not at" in result[2], f"the refusal does not say where the skill should be: {result[2]!r}"


def test_a_skill_with_an_empty_body_is_refused(tmp_path, cli):
    write_component_project(tmp_path, HOOK_COMMAND)
    (tmp_path / "project" / ".claude" / "skills" / SKILL_NAME / "SKILL.md").write_text(f"---\nname: {SKILL_NAME}\n---\n")
    assert_refused_with_rule_and_fix(run_cli(cli.capsys, cli_arguments(tmp_path, SKILL_ARGUMENTS)))
    assert not (tmp_path / "out").exists(), "a refused build wrote an out folder"


def test_a_hook_event_with_no_hook_is_refused(tmp_path, cli):
    result = build_from_cli(tmp_path, cli, ["--hook", "SessionStart", "--run-hook"])
    assert_refused_with_rule_and_fix(result)
    assert "0 command hooks" in result[2], f"the refusal does not count the hooks: {result[2]!r}"


def test_a_hook_event_with_two_hooks_is_refused(tmp_path, cli):
    write_component_project(tmp_path, HOOK_COMMAND)
    settings = tmp_path / "project" / ".claude" / "settings.json"
    document = json.loads(settings.read_text())
    document["hooks"][HOOK_EVENT].append({"hooks": [{"type": "command", "command": "printf other"}]})
    settings.write_text(json.dumps(document))
    result = run_cli(cli.capsys, cli_arguments(tmp_path, HOOK_ARGUMENTS))
    assert_refused_with_rule_and_fix(result)
    assert "2 command hooks" in result[2], f"the refusal does not count the hooks: {result[2]!r}"


@pytest.mark.parametrize(("command", "phrase"), [("exit 3", "returned no text"), ("printf ''", "has no text")])
def test_a_hook_that_fails_or_prints_nothing_is_refused(tmp_path, cli, command, phrase):
    write_component_project(tmp_path, command)
    result = run_cli(cli.capsys, cli_arguments(tmp_path, HOOK_ARGUMENTS))
    assert_refused_with_rule_and_fix(result)
    assert phrase in result[2], f"the refusal lacks {phrase!r}: {result[2]!r}"
    assert not (tmp_path / "out").exists(), "a refused build wrote an out folder"


def test_a_hook_matcher_is_kept_in_arm_c(tmp_path, cli):
    write_component_project(tmp_path, HOOK_COMMAND)
    settings = tmp_path / "project" / ".claude" / "settings.json"
    document = json.loads(settings.read_text())
    document["hooks"][HOOK_EVENT][0]["matcher"] = "Bash"
    settings.write_text(json.dumps(document))
    code, _, error = run_cli(cli.capsys, cli_arguments(tmp_path, HOOK_ARGUMENTS))
    assert code == EXIT_OK, error
    built = json.loads((overlay_of(tmp_path, ARM_COMPONENT) / ".claude" / "settings.json").read_text())
    assert built["hooks"][HOOK_EVENT][0]["matcher"] == "Bash", f"arm C lost the matcher: {built!r}"


def test_the_plan_name_option_names_the_plan(tmp_path, cli):
    build_from_cli(tmp_path, cli, SKILL_ARGUMENTS, ["--name", "my-plan"])
    assert read_plan(tmp_path / "out", "plan.json").name == "my-plan", "the plan has another name"
    assert json.loads((tmp_path / "out" / "plan.json").read_text())["budget_usd"] == float(BUDGET), "the budget is not the one given"


def test_the_five_arm_labels_are_the_shared_convention():
    assert (ARM_COMPONENT, ARM_PROMPT, ARM_NOTHING, ARM_NOISE, ARM_PLACEBO) == ("C", "P", "N", "N2", "PL"), "the arm labels changed"


def test_the_fingerprint_covers_the_detector(tmp_path, cli):
    build_from_cli(tmp_path, cli, SKILL_ARGUMENTS)
    plan = read_plan(tmp_path / "out", "plan.json")
    other_detector = replace(plan.rule.detector, actions=("git push -f",))
    changed = replace(plan, rule=replace(plan.rule, detector=other_detector))
    assert plan_fingerprint(changed) != plan_fingerprint(plan), f"a changed detector gave the same fingerprint {plan_fingerprint(changed)} for {plan.name}"
    assert plan_fingerprint(replace(plan, budget_usd=plan.budget_usd + 1)) == plan_fingerprint(plan), "a budget change moved the fingerprint"
