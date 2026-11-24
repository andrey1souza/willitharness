import repo_checks
from files import write_tree


CONTRACT_GOOD = "Ending a plan needs no validated world. A changed world only blocks starts.\nEach run record carries the hash of the world files at the start of the run (T62, T65).\nEach run record carries the model name (T73).\nA resume names each overlay file that changed.\nA restart of a Running plan checks the overlay files in the same way.\nA task that is missing on either side is refused and named (T80).\nA plan with no rule is refused with a rule and a fix (T81).\nIn a skill plan, every arm of a skill plan loads the same built-in skills, the 19 built-in skills pinned for Claude Code 2.1.331.\n"


def test_a_contract_without_the_restart_sentence_is_reported(tmp_path):
    write_tree(tmp_path, {"docs/contract.md": CONTRACT_GOOD.replace("A restart of a Running plan checks the overlay files in the same way.", "A restart skips overlays.")})
    errors = repo_checks.contract_sentence_errors(tmp_path)
    assert len(errors) == 1 and "A restart of a Running plan checks the overlay files in the same way." in errors[0], f"got {errors}"


def test_a_contract_with_both_sentences_passes(tmp_path):
    write_tree(tmp_path, {"docs/contract.md": CONTRACT_GOOD})
    assert repo_checks.contract_sentence_errors(tmp_path) == [], "a contract holding both sentences must pass"
    write_tree(tmp_path, {"docs/contract.md": CONTRACT_GOOD.replace("starts.\n", "starts.\n\n")})
    assert repo_checks.contract_sentence_errors(tmp_path) == [], "a line break inside the text must not matter"


def test_a_contract_without_the_overlay_sentence_is_reported(tmp_path):
    write_tree(tmp_path, {"docs/contract.md": CONTRACT_GOOD.replace("A resume names each overlay file that changed.", "A resume ignores overlays.")})
    errors = repo_checks.contract_sentence_errors(tmp_path)
    assert len(errors) == 1 and "A resume names each overlay file that changed." in errors[0], f"got {errors}"


def test_a_contract_without_the_ending_sentence_is_reported(tmp_path):
    write_tree(tmp_path, {"docs/contract.md": CONTRACT_GOOD.replace("Ending a plan needs no validated world.", "Ending a plan is free.")})
    errors = repo_checks.contract_sentence_errors(tmp_path)
    assert len(errors) == 1 and "Ending a plan needs no validated world." in errors[0] and "Fix: restore it." in errors[0], f"got {errors}"


def test_a_contract_without_the_task_match_sentence_is_reported(tmp_path):
    write_tree(tmp_path, {"docs/contract.md": CONTRACT_GOOD.replace("A task that is missing on either side is refused and named (T80).", "A task may differ.")})
    errors = repo_checks.contract_sentence_errors(tmp_path)
    assert len(errors) == 1 and "A task that is missing on either side is refused and named (T80)." in errors[0], f"got {errors}"


def test_a_contract_without_the_rule_required_sentence_is_reported(tmp_path):
    write_tree(tmp_path, {"docs/contract.md": CONTRACT_GOOD.replace("A plan with no rule is refused with a rule and a fix (T81).", "A plan may lack a rule.")})
    errors = repo_checks.contract_sentence_errors(tmp_path)
    assert len(errors) == 1 and "A plan with no rule is refused with a rule and a fix (T81)." in errors[0], f"got {errors}"
