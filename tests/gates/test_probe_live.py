import json

import probe_live
from willitharness import fakeagent
from willitharness.fakeagent import Behavior, Location

SEED = 5
WORKSPACE_PREFIX = "willitharness-live-"
SWAPPED = {"ancestor-masks-agents": "Loaded", "agents-only": "Masked", "LOO non-target token": "Loaded"}
EXPENSIVE_RUN = 0.2


def workspace_root(directory):
    for folder in [directory, *directory.parents]:
        if folder.name.startswith(WORKSPACE_PREFIX):
            return folder
    raise AssertionError(f"{directory} is not inside a {WORKSPACE_PREFIX} workspace")


def label_in(prompt):
    return prompt.split("label ")[1].split(" in your")[0]


def scripted_runner(directory, prompt):
    location = Location(directory, workspace_root(directory))
    return fakeagent.run_agent(Behavior(SEED), location, label_in(prompt), 0)


def expensive_runner(directory, prompt):
    lines = scripted_runner(directory, prompt)
    final = json.loads(lines[-1])
    final["total_cost_usd"] = EXPENSIVE_RUN
    return lines[:-1] + [json.dumps(final)]


def test_the_gate_passes_when_every_case_matches_the_expected_labels(capsys):
    code = probe_live.main([], scripted_runner)
    output = capsys.readouterr().out.splitlines()
    assert code == probe_live.EXIT_PASSED, f"expected exit 0, got {code}; output {output}"
    assert output[:3] == ["ancestor-masks-agents: Masked", "agents-only: Loaded", "LOO non-target token: Loaded"], f"got {output}"
    assert output[-1] == "GATE G2.3 PASS", f"the last line must be the pass line, got {output}"


def test_swapped_expected_labels_print_mismatch_and_exit_one(tmp_path, capsys):
    expected = tmp_path / "swapped.json"
    expected.write_text(json.dumps(SWAPPED))
    code = probe_live.main(["--expected", str(expected)], scripted_runner)
    output = capsys.readouterr().out
    assert code == probe_live.EXIT_FAILED, f"expected exit 1, got {code}"
    assert "MISMATCH ancestor-masks-agents: expected Loaded, got Masked" in output, f"unexpected output {output!r}"
    assert "GATE G2.3 PASS" not in output, f"a mismatch must not print the pass line, got {output!r}"


def test_a_run_set_above_the_cost_cap_fails_the_gate(capsys):
    code = probe_live.main([], expensive_runner)
    output = capsys.readouterr().out
    assert code == probe_live.EXIT_FAILED, f"expected exit 1, got {code}"
    assert "COST OVER CAP" in output, f"unexpected output {output!r}"
