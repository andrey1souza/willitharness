import repo_checks
from files import write_tree


CONTRACT_GOOD = "Ending a plan needs no validated world. A changed world only blocks starts.\nEach run record carries the hash of the world files at the start of the run (T62, T65).\n"


def test_a_contract_with_both_sentences_passes(tmp_path):
    write_tree(tmp_path, {"docs/contract.md": CONTRACT_GOOD})
    assert repo_checks.contract_sentence_errors(tmp_path) == [], "a contract holding both sentences must pass"
    write_tree(tmp_path, {"docs/contract.md": CONTRACT_GOOD.replace("starts.\n", "starts.\n\n")})
    assert repo_checks.contract_sentence_errors(tmp_path) == [], "a line break inside the text must not matter"


def test_a_contract_without_the_ending_sentence_is_reported(tmp_path):
    write_tree(tmp_path, {"docs/contract.md": CONTRACT_GOOD.replace("Ending a plan needs no validated world.", "Ending a plan is free.")})
    errors = repo_checks.contract_sentence_errors(tmp_path)
    assert len(errors) == 1 and "Ending a plan needs no validated world." in errors[0] and "Fix: restore it." in errors[0], f"got {errors}"
