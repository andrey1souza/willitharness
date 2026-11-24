import sys
from dataclasses import replace

import pytest
from agent_site import ONE_RUN, flag_value, install_fake_agent_environment, prepare_project_with_fake_agent
from fake_claude import LEAKED_SKILL, PINNED_BUILTIN_SKILLS, UNPINNED_BUILTIN_SKILL, report_of
from files import write_tree
from lifecycle_site import SiteSpec, TASK_NAME, ready_site, run_setup, stored_final_runs

from willitharness.artifacts import TRANSCRIPT_NAME, artifact_directory
from willitharness.claude_agent import BUILTIN_SKILLS, PINNED_CLAUDE_VERSION, foreign_skills, listed_skills, probe_argv, run_command, skill_probe_argv
from willitharness.lifecycle import start_running
from willitharness.plan import PlanError
from willitharness.real_runner import claude_runner
from willitharness.store import Cell

pytestmark = pytest.mark.skipif(sys.platform != "darwin", reason="the real runner uses macOS sandbox-exec")
ARM_SKILL = "arm-skill"
USER_SKILL = "user-skill"
SLASH_OFF = "--disable-slash-commands"
MIXED = SiteSpec(arm_count=2, budget_usd=1.0, run_cap_usd=0.02, reps=1, max_retries=0)


def skill_file(overlay, name):
    return {f"{overlay}/.claude/skills/{name}/SKILL.md": f"---\nname: {name}\ndescription: Use for tests.\n---\nBody.\n"}


def skill_site(tmp_path, monkeypatch, behavior="ok", spec=ONE_RUN):
    site = mixed_site(tmp_path, monkeypatch, behavior) if spec is MIXED else prepare_project_with_fake_agent(tmp_path, monkeypatch, ONE_RUN, behavior)
    write_tree(site.root, skill_file("A.md", ARM_SKILL))
    arm = replace(site.plan.arms[0], channel="skill")
    return replace(site, plan=replace(site.plan, arms=(arm, *site.plan.arms[1:])))


def mixed_site(tmp_path, monkeypatch, behavior):
    install_fake_agent_environment(tmp_path, monkeypatch)
    site = ready_site(tmp_path / "project", MIXED)
    write_tree(site.root, {"A.md/fake-behavior.txt": behavior, "B.md/fake-behavior.txt": behavior, "A.md/rule.txt": "rule", "B.md/rule.txt": "rule"})
    return site


def run_arm(site, label):
    start_running(site)
    return claude_runner(run_setup(site), "haiku")(Cell(label, TASK_NAME), 1, 1)


def test_a_skill_arm_run_has_the_skill_tool_and_keeps_slash_commands_on(tmp_path, monkeypatch):
    site = skill_site(tmp_path, monkeypatch)
    arguments = report_of(run_arm(site, "A").transcript)["arguments"]
    assert flag_value(arguments, "--tools") == "Bash,Skill", f"a skill arm needs the Skill tool, got {arguments}"
    assert SLASH_OFF not in arguments, f"a skill arm must not disable skills, got {arguments}"
    assert flag_value(arguments, "--allowedTools") == f"Bash(ls:*),Bash(pkill:*),Skill({ARM_SKILL})", f"the arm skill must be allowed, got {arguments}"
    assert flag_value(arguments, "--setting-sources") == "project,local" and "--strict-mcp-config" in arguments, f"isolation flags lost in {arguments}"


def test_in_a_mixed_plan_every_arm_has_the_skill_tool_and_only_the_skill_arm_has_the_allow_rule(tmp_path, monkeypatch):
    site = skill_site(tmp_path, monkeypatch, spec=MIXED)
    skill_arm = report_of(run_arm(site, "A").transcript)["arguments"]
    plain_arm = report_of(run_arm(site, "B").transcript)["arguments"]
    assert flag_value(skill_arm, "--tools") == "Bash,Skill" and SLASH_OFF not in skill_arm, f"arm A is the skill arm, got {skill_arm}"
    assert flag_value(plain_arm, "--tools") == "Bash,Skill" and SLASH_OFF not in plain_arm, f"arm B must have the same tools and no slash flag, got {plain_arm}"
    assert flag_value(plain_arm, "--allowedTools") == "Bash(ls:*),Bash(pkill:*)", f"arm B must hold no Skill rule, got {plain_arm}"
    assert not any("Skill(" in item for item in plain_arm), f"arm B must hold no Skill rule, got {plain_arm}"


def test_in_a_skill_plan_every_arm_lists_the_pinned_built_in_skills_and_only_the_skill_arm_adds_its_own(tmp_path, monkeypatch):
    site = skill_site(tmp_path, monkeypatch, spec=MIXED)
    skill_arm = listed_skills(list(run_arm(site, "A").transcript))
    plain_arm = listed_skills(list(run_arm(site, "B").transcript))
    assert plain_arm == sorted(PINNED_BUILTIN_SKILLS), f"arm B must list the pinned built-in skills only, got {plain_arm}"
    assert skill_arm == sorted((*PINNED_BUILTIN_SKILLS, ARM_SKILL)), f"arm A must add its own skill only, got {skill_arm}"


def test_the_pinned_built_in_skills_are_the_nineteen_of_the_verified_claude_code_version():
    assert BUILTIN_SKILLS == PINNED_BUILTIN_SKILLS and len(BUILTIN_SKILLS) == 19, f"the pinned set changed: {BUILTIN_SKILLS}"
    assert PINNED_CLAUDE_VERSION == "2.1.331", f"the verified version changed: {PINNED_CLAUDE_VERSION}"


def test_a_plan_with_no_skill_arm_keeps_the_old_flags_and_lists_no_skill(tmp_path, monkeypatch):
    site = prepare_project_with_fake_agent(tmp_path, monkeypatch, ONE_RUN, "ok")
    result = run_arm(site, "A")
    arguments = report_of(result.transcript)["arguments"]
    assert flag_value(arguments, "--tools") == "Bash" and SLASH_OFF in arguments, f"got {arguments}"
    assert listed_skills(list(result.transcript)) == [], f"got {listed_skills(list(result.transcript))}"


def test_the_transcript_of_a_skill_arm_lists_no_user_skill(tmp_path, monkeypatch):
    home = tmp_path / "home"
    write_tree(home, skill_file(".", USER_SKILL))
    monkeypatch.setenv("HOME", str(home))
    site = skill_site(tmp_path, monkeypatch)
    listed = listed_skills(list(run_arm(site, "A").transcript))
    assert USER_SKILL not in listed and ARM_SKILL in listed, f"the transcript must not list the user skill, got {listed}"


def test_the_fake_agent_would_list_the_user_skill_if_user_settings_loaded(tmp_path, monkeypatch):
    home = tmp_path / "home"
    write_tree(home, skill_file(".", USER_SKILL))
    monkeypatch.setenv("HOME", str(home))
    install_fake_agent_environment(tmp_path, monkeypatch)
    work = tmp_path / "work"
    write_tree(work, skill_file(".", ARM_SKILL))
    command = ["claude", "-p", "x", "--setting-sources", "user,project,local"]
    assert {ARM_SKILL, USER_SKILL} <= set(listed_skills(run_command(work, command))), f"the fake agent must model the user source, or the isolation test proves nothing, got {listed_skills(run_command(work, command))} for {command}"


def test_a_skill_arm_run_that_lists_a_user_skill_is_refused_with_the_skill_named(tmp_path, monkeypatch):
    site = skill_site(tmp_path, monkeypatch, "leak-skill")
    with pytest.raises(PlanError) as raised:
        run_arm(site, "A")
    message = str(raised.value)
    assert LEAKED_SKILL in message and "Rule:" in message and message.rstrip(".").split("Fix:")[-1].strip(), f"the refusal must name the skill, the rule and the fix, got {message!r}"


def test_a_plain_arm_of_a_skill_plan_that_lists_an_unpinned_built_in_skill_is_refused_and_the_skill_is_named_and_stored(tmp_path, monkeypatch):
    site = skill_site(tmp_path, monkeypatch, "leak-builtin", spec=MIXED)
    with pytest.raises(PlanError) as raised:
        run_arm(site, "B")
    message = str(raised.value)
    assert UNPINNED_BUILTIN_SKILL in message and "pin" in message and "check that it is a Claude Code built-in" in message, f"got {message!r}"
    assert "Rule:" in message and message.index("Rule:") < message.index("Fix:"), f"got {message!r}"
    assert UNPINNED_BUILTIN_SKILL in message.split("Fix:")[-1], f"the fix must name the skill to pin, got {message!r}"
    stored = artifact_directory(tmp_path / "project", site.plan.name, Cell("B", TASK_NAME), 1) / TRANSCRIPT_NAME.format(attempt=1)
    assert UNPINNED_BUILTIN_SKILL in stored.read_text(), f"the transcript must be stored before the refusal, looked in {stored}"


def test_a_plan_arm_without_a_skill_file_is_refused_before_any_run(tmp_path, monkeypatch):
    site = skill_site(tmp_path, monkeypatch)
    (site.root / "A.md" / ".claude" / "skills" / ARM_SKILL / "SKILL.md").unlink()
    with pytest.raises(PlanError) as raised:
        claude_runner(run_setup(site), "haiku")
    message = str(raised.value)
    assert "SKILL.md" in message and "Rule:" in message and "Fix:" in message, f"unexpected message {message!r}"
    assert not stored_final_runs(site), f"a refused plan must not start a run, found {stored_final_runs(site)}"


def test_the_probe_of_a_skill_arm_keeps_the_skill_tool_and_slash_commands_on():
    argv = skill_probe_argv("What value?", "haiku", 0.03, (ARM_SKILL,))
    assert flag_value(argv, "--tools") == "Skill" and SLASH_OFF not in argv, f"the probe must keep the Skill tool, got {argv}"
    assert "Bash" not in flag_value(argv, "--tools") and "--settings" not in argv, f"the probe has no Bash and no sandbox, got {argv}"


def test_the_probe_of_a_plain_arm_of_a_skill_plan_keeps_the_skill_tool_without_an_allow_rule():
    argv = skill_probe_argv("What value?", "haiku", 0.03, ())
    assert flag_value(argv, "--tools") == "Skill" and SLASH_OFF not in argv and "--allowedTools" not in argv, f"got {argv}"


def test_the_probe_of_a_plain_arm_is_unchanged():
    argv = probe_argv("What value?", "haiku", 0.03, "")
    assert flag_value(argv, "--tools") == "" and SLASH_OFF in argv and "--allowedTools" not in argv, f"got {argv}"


def test_foreign_skills_ignores_noise_lines_and_other_events():
    transcript = ["not json", '{"type": "assistant"}', '{"type": "system", "subtype": "init", "skills": ["a", "b"]}', '{"type": "system", "subtype": "other", "skills": ["c"]}']
    assert listed_skills(transcript) == ["a", "b"] and foreign_skills(transcript, ("a",)) == ["b"], f"got {listed_skills(transcript)}"
