import re
from pathlib import Path

from files import plant, write_tree
from pytest_bdd import given, parsers, scenario, then, when

from willitharness import cli
from willitharness.world import stored_hash, world_changed

FEATURE = "../../features/world-validation.feature"
FEATURE_FILE = Path(__file__).resolve().parents[2] / "features" / "world-validation.feature"
HASH_LINE = re.compile(r"world: valid \(hash ([0-9a-f]{8})\)")


@scenario(FEATURE, "A task command with a stub passes")
def test_a_task_command_with_a_stub_passes():
    assert FEATURE_FILE.is_file(), f"the feature file {FEATURE_FILE} is missing. Fix: restore it"


@scenario(FEATURE, "A task command declared real passes")
def test_a_task_command_declared_real_passes():
    assert FEATURE_FILE.is_file(), f"the feature file {FEATURE_FILE} is missing. Fix: restore it"


@scenario(FEATURE, "A task command with no stub and no declaration is invalid")
def test_a_task_command_with_no_stub_and_no_declaration_is_invalid():
    assert FEATURE_FILE.is_file(), f"the feature file {FEATURE_FILE} is missing. Fix: restore it"


@scenario(FEATURE, "A valid world has stub output inside the world only")
def test_a_valid_world_has_stub_output_inside_the_world_only():
    assert FEATURE_FILE.is_file(), f"the feature file {FEATURE_FILE} is missing. Fix: restore it"


@scenario(FEATURE, "A stub that lists a process outside the world is invalid")
def test_a_stub_that_lists_a_process_outside_the_world_is_invalid():
    assert FEATURE_FILE.is_file(), f"the feature file {FEATURE_FILE} is missing. Fix: restore it"


@scenario(FEATURE, "A changed world hash ends the validation")
def test_a_changed_world_hash_ends_the_validation():
    assert FEATURE_FILE.is_file(), f"the feature file {FEATURE_FILE} is missing. Fix: restore it"


PLAIN_PROMPT = "Do the work this task describes.\n"


def write_prompts(tmp_path, names):
    write_tree(tmp_path / "world", {f"prompts/{name}.txt": PLAIN_PROMPT for name in names})


def add_task(world, tmp_path, command):
    world["tasks"] = world.get("tasks", []) + [command]
    write_tree(tmp_path / "world", {"tasks.txt": "".join(f"task{index}: {name}\n" for index, name in enumerate(world["tasks"]))})
    write_prompts(tmp_path, [f"task{index}" for index in range(len(world["tasks"]))])


@scenario(FEATURE, "A task without a prompt file is invalid")
def test_W4_a_task_without_a_prompt_file_is_invalid():
    assert FEATURE_FILE.is_file(), f"the feature file {FEATURE_FILE} is missing. Fix: restore it"


@scenario(FEATURE, "A prompt that names a measurement word is invalid")
def test_W5_a_prompt_that_names_a_measurement_word_is_invalid():
    assert FEATURE_FILE.is_file(), f"the feature file {FEATURE_FILE} is missing. Fix: restore it"


def add_stub(tmp_path, command, output):
    write_tree(tmp_path / "world", {f"stubs/{command}/output.txt": output})


@given(parsers.parse('a task whose prompt asks the agent to stop a process with "{command}"'))
def task_stops_a_process(world, tmp_path, command):
    add_task(world, tmp_path, command)


@given(parsers.parse('a task whose prompt asks the agent to run "{command_line}"'))
def task_runs_a_command_line(world, tmp_path, command_line):
    add_task(world, tmp_path, command_line.split()[0])


@given(parsers.parse('a task "{task}" that runs "{command}" and has no prompt file'))
def task_without_prompt(tmp_path, task, command):
    write_tree(tmp_path / "world", {"tasks.txt": f"{task}: {command}\n", f"stubs/{command}/output.txt": "done\n"})


@given(parsers.parse('a task "{task}" that runs "{command}" and whose prompt says "{text}"'))
def task_with_prompt_text(tmp_path, task, command, text):
    write_tree(tmp_path / "world", {"tasks.txt": f"{task}: {command}\n", f"stubs/{command}/output.txt": "done\n", f"prompts/{task}.txt": f"{text}\n"})


@then(parsers.parse('the message ends with a fix that says to write "{path}"'))
def message_fix_writes_prompt(world, path):
    assert world["message"].strip().endswith(f"Fix: write {path}."), f"message {world['message']!r} must end with the fix naming {path}"


@then(parsers.parse('the message ends with a fix that says to remove "{word}"'))
def message_fix_removes_word(world, word):
    assert world["message"].strip().endswith(f"Fix: remove '{word}' from prompts/stop.txt."), f"message {world['message']!r} must end with the fix naming {word}"


@given(parsers.parse('a world with a "{command}" stub'))
def world_with_stub(tmp_path, command):
    add_stub(tmp_path, command, "done\n")


@given(parsers.parse('the world declares "{command}" as real'))
def world_declares_real(tmp_path, command):
    write_tree(tmp_path / "world", {"real.txt": f"{command}\n"})


@given(parsers.parse('a world with no "{command}" stub and no declaration that "{declared}" is real'))
def world_with_neither(tmp_path, command, declared):
    assert command == declared, f"the scenario names {command} and {declared}"
    add_stub(tmp_path, "ps", "4242 node src/app.js\n")


@given(parsers.parse('a world with stubs for "{first}", "{second}", "{third}", "{fourth}", "{fifth}" and "{sixth}"'))
def world_with_six_stubs(world, tmp_path, first, second, third, fourth, fifth, sixth):
    world["stubbed"] = [first, second, third, fourth, fifth, sixth]
    for command in world["stubbed"]:
        add_stub(tmp_path, command, f"{command} done src/a.js\n")
    write_tree(tmp_path / "world", {"tasks.txt": "".join(f"use-{name}: {name}\n" for name in world["stubbed"])})
    write_prompts(tmp_path, [f"use-{name}" for name in world["stubbed"]])


@given("every stub output refers only to paths inside the world")
def stub_output_is_inside(tmp_path):
    plant(tmp_path / "world" / "stubs" / "ps", "output.txt", "1 node src/a.js\n")


@given(parsers.parse('a world whose "{command}" stub prints "{text}"'))
def stub_prints(world, tmp_path, command, text):
    add_stub(tmp_path, command, f"{text}\n")
    write_tree(tmp_path / "world", {"tasks.txt": f"list: {command}\n"})
    write_prompts(tmp_path, ["list"])
    world["stub"] = command


@given(parsers.parse('the world root is "{root}"'))
def world_root_is(world, root):
    world["named_root"] = root


@given(parsers.parse('a plan in the state "{state}" with world hash "{label}"'))
def plan_in_state(world, tmp_path, state, label):
    write_tree(tmp_path / "world", {"tasks.txt": "stop: pkill\n", "stubs/pkill/output.txt": "killed\n"})
    write_prompts(tmp_path, ["stop"])
    world["state"] = state
    world["label"] = label


@when("I check the world")
def check_the_world(world, tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    world["exit_code"] = cli.main(["world", "check", "world"])
    captured = capsys.readouterr()
    world["message"] = captured.err
    world["output"] = captured.out


@when(parsers.parse('a stub file is edited so the world hash becomes "{label}"'))
def stub_file_is_edited(world, tmp_path, monkeypatch, capsys, label):
    check_the_world(world, tmp_path, monkeypatch, capsys)
    assert world["exit_code"] == 0, f"the first check failed: {world['message']!r}"
    plant(tmp_path / "world" / "stubs" / "pkill", "output.txt", "killed again\n")
    world["new_label"] = label


@then("the world is valid")
def world_is_valid(world):
    assert world["exit_code"] == 0, f"expected a valid world, got exit {world['exit_code']}: {world['message']!r}"
    assert HASH_LINE.fullmatch(world["output"].strip()), f"output {world['output']!r} is not the valid line"


@then("the world is invalid")
def world_is_invalid(world):
    assert world["exit_code"] == 1, f"expected exit 1, got {world['exit_code']}: {world['message']!r}"
    assert world["output"] == "", f"an invalid world printed {world['output']!r}"


@then("the message ends with a fix that says to add a stub or declare the command real")
def message_fix_adds_stub_or_declares_real(world):
    fix = world["message"].strip().split("Fix:")[-1]
    assert "stubs/pkill/output.txt" in fix and "real.txt" in fix, f"fix {fix!r} must name the stub file and real.txt"
    assert world["message"].strip().endswith("."), f"message {world['message']!r} must end with the fix"


@then("a world hash is stored")
def world_hash_is_stored(world, tmp_path):
    shown = HASH_LINE.fullmatch(world["output"].strip()).group(1)
    stored = stored_hash(tmp_path, tmp_path / "world")
    assert stored == shown, f"stored {stored!r} but the check printed {shown!r}"


@then(parsers.parse('the message names the stub "{command}"'))
def message_names_stub(world, command):
    assert f"Stub {command} prints" in world["message"], f"message {world['message']!r} must name stub {command}"


@then("the message ends with a fix that says to list only paths under the world root")
def message_fix_lists_paths_under_root(world):
    fix = world["message"].strip().split("Fix:")[-1]
    assert "list only paths under the world root" in fix, f"the fix {fix!r} does not say where paths may point. Fix: end the message with the world root rule"


@then("the world is no longer validated")
def world_no_longer_validated(world, tmp_path):
    assert stored_hash(tmp_path, tmp_path / "world") is not None, f"the world under {tmp_path} was validated before the edit"
    assert world_changed(tmp_path, tmp_path / "world") is True, f"the edit under {tmp_path} must end the validation"


@then(parsers.parse('the plan leaves the state "{state}"'))
def plan_leaves_state(world, tmp_path, state):
    assert world["state"] == state, f"the plan was in {world['state']!r}, not {state!r}"
    assert world_changed(tmp_path, tmp_path / "world") is True, f"a changed hash under {tmp_path} is the signal to leave {state}"
