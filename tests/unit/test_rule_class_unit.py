import pytest
from files import write_tree

from willitharness.rule_class import COMMAND, ENFORCED, NOT_TESTABLE, classify_rule, extract_rules

FILES = {"scripts/check.sh": "#!/usr/bin/env bash\n", "README.md": "readme\n", "generated/out.txt": "x\n"}
SOURCE = "AGENTS.md"
GOLDEN = (
    ("Run `scripts/check.sh` before every commit.", ENFORCED, None),
    ("Run `scripts/check.sh --all` before every commit.", ENFORCED, None),
    ("Never use `pkill` while agents run.", COMMAND, "forbids"),
    ("Do not run `git push --force`.", COMMAND, "forbids"),
    ("Always run `make test` before you commit.", COMMAND, "requires"),
    ("Use `git -C PATH` instead of `cd PATH && git`.", COMMAND, "requires"),
    ("Run `scripts/missing.sh` before you push.", NOT_TESTABLE, None),
    ("Keep `README.md` short.", NOT_TESTABLE, None),
    ("Use `snake_case` for Python names.", NOT_TESTABLE, None),
    ("Never edit files under `generated/`.", NOT_TESTABLE, None),
    ("Write sentences of 20 words or fewer.", NOT_TESTABLE, None),
    ("Never use the force flag.", NOT_TESTABLE, None),
    ("Keep the `git status` output short.", NOT_TESTABLE, None),
    ("`npm ci && npx tsc --noEmit`", COMMAND, "requires"),
    ("`node scripts/eval/run-checks.ts --lint`", COMMAND, "requires"),
    ("`env -u CLAUDECODE zanity check . --baseline zanity-baseline.json`", COMMAND, "requires"),
    ("`scripts/missing.sh`", NOT_TESTABLE, None),
    ("Never push to `main`. Never force-push it. Push a branch with an explicit refspec: `git push origin BRANCH:refs/heads/BRANCH`.", COMMAND, "requires"),
    ("Before every commit you must always run the whole set of checks as `make test`.", COMMAND, "requires"),
    ("Stop. Then `make test` runs.", NOT_TESTABLE, None),
)


@pytest.mark.parametrize(("text", "label", "direction"), GOLDEN)
def test_each_rule_gets_its_golden_class(tmp_path, text, label, direction):
    write_tree(tmp_path, FILES)
    verdict = classify_rule(text, tmp_path)
    assert (verdict.label, verdict.direction) == (label, direction), f"{text!r} got {verdict}"
    assert verdict.reason.strip(), f"{text!r} has no reason"


def test_a_prose_rule_never_becomes_a_command_rule(tmp_path):
    write_tree(tmp_path, FILES)
    prose = ("Never use the force flag.", "Use `snake_case` for Python names.", "Keep `README.md` short.")
    assert [classify_rule(text, tmp_path).label for text in prose] == [NOT_TESTABLE] * len(prose), f"a prose rule became a command rule: {prose}"


def test_a_backticked_path_that_does_not_exist_is_not_script_backed(tmp_path):
    write_tree(tmp_path, FILES)
    verdict = classify_rule("Run `scripts/missing.sh` before you push.", tmp_path)
    assert verdict.label == NOT_TESTABLE and "scripts/missing.sh" in verdict.reason and "does not exist" in verdict.reason, f"got {verdict}"


def test_a_path_outside_the_repo_is_not_script_backed(tmp_path):
    repo = tmp_path / "repo"
    write_tree(repo, FILES)
    write_tree(tmp_path, {"outside.sh": "x\n"})
    assert classify_rule("Run `../outside.sh` first.", repo).label == NOT_TESTABLE, "a script outside the repo must not count"


def test_the_extractor_reads_bullets_with_continuation_lines_and_skips_fences(tmp_path):
    text = "# Title\n\nProse is not a rule.\n\n- First rule.\n  It goes on.\n* Second rule.\n1. Third rule.\n\n```\n- code bullet\n```\n"
    rules = extract_rules(SOURCE, text)
    assert [(rule.line, rule.text) for rule in rules] == [(5, "First rule. It goes on."), (7, "Second rule."), (8, "Third rule.")], f"got {rules}"


BACKTICK_CLAIM = "names no command in backticks"


@pytest.mark.parametrize(("text", "label", "direction"), GOLDEN)
def test_a_reason_never_contradicts_the_text(tmp_path, text, label, direction):
    write_tree(tmp_path, FILES)
    verdict = classify_rule(text, tmp_path)
    assert not ("`" in text and BACKTICK_CLAIM in verdict.reason), f"{text!r} has backticks but its reason says {verdict.reason!r}. Fix: state what the backticked text is."
