import argparse
import json
import os
import re
import sys
from pathlib import Path

SCRIPTS_DIRECTORY = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIRECTORY))
sys.path.insert(0, str(SCRIPTS_DIRECTORY / "site"))

from brand_gates import HOLD_BACK_PHRASES, MAX_SENTENCE_WORDS, MIN_SHORT_SENTENCE_PERCENT, PERCENT
from guards import private_names
from guards.gitcommand import git_lines
from markup import sentences_of
from willitharness.paths import PathOutsideRoot, inside

DEFAULT_BASE = "origin/main"
EXIT_CLEAN = 0
EXIT_FAILED = 1
EXIT_BLOCKED = 2
EXTRA_HOLD_BACK_PHRASES = ("guaranteed", "fully tested")
BLOCKED_PHRASES = (*HOLD_BACK_PHRASES, *EXTRA_HOLD_BACK_PHRASES)
FACT_KEYS = ("tests", "mutants_killed", "mutants_total", "trace_ids", "repo_checks")
ATTRIBUTION_LINE = re.compile(r"^(Co-Authored-By:.*|.*Generated with .*Claude Code.*)$")
NUMBER = re.compile(r"(?<![\w.])\d+(?![\w])")
DIGITS = re.compile(r"\d+")
TESTS_LINE = re.compile(r"\b(\d+) passed\b")
TESTS_FAILED = re.compile(r"\b\d+ failed\b")
MUTANTS_LINE = re.compile(r"^mutants killed: (\d+)/(\d+)$", re.MULTILINE)
TRACE_LINE = re.compile(r"^trace-check: all (\d+) IDs covered", re.MULTILINE)
REPO_LINE = re.compile(r"^repo-checks: (\d+) checks passed$", re.MULTILINE)
MARKDOWN_PREFIX = re.compile(r"^(#+\s+|-\s+)")
SHA_LENGTH = 12
MINIMUM_COMMITS_FOR_SUMMARY = 2
CHECKS_HEADING = "## Checks"
COMMIT_LABEL = "Commit: "
SUBJECT_FORMAT = "--format=%s"
BODY_FORMAT = "--format=%b"
SHA_FORMAT = "--format=%H"


def read_commits(repo, base):
    assert repo, f"read_commits got repo {repo!r}. Rule: git runs in one repository. Fix: pass the repository directory."
    assert base, f"read_commits got base {base!r}. Rule: the pull request is the range from its base. Fix: pass a revision such as {DEFAULT_BASE}."
    shas = git_lines(repo, ["log", SHA_FORMAT, f"{base}..HEAD"])
    return [
        {
            "sha": sha,
            "subject": git_lines(repo, ["log", "-1", SUBJECT_FORMAT, sha])[0],
            "body_lines": git_lines(repo, ["log", "-1", BODY_FORMAT, sha]),
        }
        for sha in shas
    ]


def title_line(commits):
    assert commits, "title_line got no commits. Rule: a pull request carries at least one commit. Fix: commit on the branch first."
    assert all(commit["subject"] for commit in commits), f"a commit has an empty subject in {commits!r}. Fix: write a subject."
    newest = commits[0]["subject"]
    if len(commits) < MINIMUM_COMMITS_FOR_SUMMARY:
        return newest
    return f"{newest} (+{len(commits) - 1} commits)"


def attribution_lines(commits):
    assert isinstance(commits, list), f"attribution_lines needs a list of commits, got {type(commits).__name__}. Fix: pass read_commits output."
    assert all("body_lines" in commit for commit in commits), f"a commit lacks body_lines in {commits!r}. Fix: pass read_commits output."
    found = [line.strip() for commit in commits for line in commit["body_lines"] if ATTRIBUTION_LINE.match(line.strip())]
    return list(dict.fromkeys(found))


def check_lines(facts):
    assert set(FACT_KEYS) <= set(facts), f"facts lack {sorted(set(FACT_KEYS) - set(facts))}. Rule: the checks come from the make check log. Fix: run pr_text.py --log <log> --write-facts <file>."
    assert all(isinstance(facts[key], int) for key in FACT_KEYS), f"every fact is a whole number, got {facts!r}. Fix: regenerate the facts."
    return [
        f"- Tests: {facts['tests']} passed",
        f"- Mutants: {facts['mutants_killed']} of {facts['mutants_total']} killed",
        f"- Contract IDs covered: {facts['trace_ids']}",
        f"- Repository checks passed: {facts['repo_checks']}",
    ]


def build_body(commits, facts):
    assert commits, "build_body got no commits. Rule: a pull request carries at least one commit. Fix: commit on the branch first."
    assert facts, "build_body got no facts. Rule: the checks come from the make check log. Fix: pass the facts file."
    lines = [title_line(commits), "", *(f"- {commit['subject']}" for commit in commits), ""]
    lines += [f"{COMMIT_LABEL}{commits[0]['sha'][:SHA_LENGTH]}", "", CHECKS_HEADING, *check_lines(facts)]
    attribution = attribution_lines(commits)
    if attribution:
        lines += ["", *attribution]
    return "\n".join(lines) + "\n"


def last_count(pattern, log):
    assert hasattr(pattern, "findall"), f"last_count needs a compiled pattern, got {pattern!r}. Fix: compile it."
    assert isinstance(log, str), f"last_count needs log text, got {type(log).__name__}. Fix: pass the make check output."
    found = pattern.findall(log)
    assert found, f"the log has no line matching {pattern.pattern!r}. Rule: the facts come from real gate output. Fix: pass the full make check log."
    return int(found[-1])


def facts_from_log(log):
    assert isinstance(log, str), f"facts_from_log needs log text, got {type(log).__name__}. Fix: pass the make check output."
    assert log.strip(), "the log is empty. Rule: the facts come from real gate output. Fix: pass the make check log."
    mutants = [(int(killed), int(planned)) for killed, planned in MUTANTS_LINE.findall(log)]
    assert mutants, f"the log of {len(log)} characters has no 'mutants killed: a/b' line. Rule: the facts come from real gate output. Fix: pass the full make check log."
    killed, total = (sum(column) for column in zip(*mutants))
    failed = [label for label, bad in (("Tests", TESTS_FAILED.search(log)), ("Mutants", killed != total)) if bad]
    assert not failed, f"the log shows failed gates {failed}. Rule: a pull request body reports green checks only. Fix: make check pass, then pass its log."
    return {"tests": last_count(TESTS_LINE, log), "mutants_killed": killed, "mutants_total": total, "trace_ids": last_count(TRACE_LINE, log), "repo_checks": last_count(REPO_LINE, log)}


def allowed_numbers(facts, commits):
    assert facts, "allowed_numbers got no facts. Rule: numbers come from facts. Fix: pass the facts file."
    assert isinstance(commits, list), f"commits must be a list, got {type(commits).__name__}. Fix: pass read_commits output."
    commit_text = [commit["subject"] for commit in commits] + [line for commit in commits for line in commit["body_lines"]]
    numbers = {str(value) for value in facts.values()}
    numbers |= {digits for text in commit_text for digits in DIGITS.findall(text)}
    return numbers | {str(len(commits)), str(len(commits) - 1)}


def number_problems(body, facts, commits):
    assert isinstance(body, str), f"number_problems needs body text, got {type(body).__name__}. Fix: pass the body."
    assert commits, "number_problems got no commits. Rule: numbers are checked against the commit data. Fix: pass read_commits output."
    prose = body
    for commit in commits:
        prose = prose.replace(commit["sha"][:SHA_LENGTH], "")
    allowed = allowed_numbers(facts, commits)
    return [
        f"the body has the number {digits}, which is in neither the facts nor the commit data. Rule: every number comes from data. Fix: delete it or regenerate the body."
        for digits in sorted(set(NUMBER.findall(prose)) - allowed)
    ]


def private_problems(body, patterns):
    assert isinstance(body, str), f"private_problems needs body text, got {type(body).__name__}. Fix: pass the body."
    assert isinstance(patterns, list), f"patterns must be a list, got {type(patterns).__name__}. Fix: pass the denylist patterns."
    return [
        f"line {number} matches a term from the private denylist. Rule: public text carries no private names. Fix: reword the line."
        for number, line in enumerate(body.splitlines(), start=1)
        if any(re.search(pattern, line, re.IGNORECASE) for pattern in patterns)
    ]


def phrase_problems(body):
    assert isinstance(body, str), f"phrase_problems needs body text, got {type(body).__name__}. Fix: pass the body."
    assert BLOCKED_PHRASES, "BLOCKED_PHRASES is empty. Rule: the hold-back list names the phrases. Fix: restore it."
    return [
        f"the body says {phrase!r}. Rule: a claim no script checks stays out. Fix: delete the phrase."
        for phrase in BLOCKED_PHRASES
        if re.search(rf"(?<![\w-]){re.escape(phrase)}(?![\w-])", body, re.IGNORECASE)
    ]


def prose_sentences(body, attribution):
    assert isinstance(body, str), f"prose_sentences needs body text, got {type(body).__name__}. Fix: pass the body."
    assert isinstance(attribution, list), f"attribution must be a list, got {type(attribution).__name__}. Fix: pass attribution_lines output."
    stripped = [line.strip() for line in body.splitlines()]
    lines = [MARKDOWN_PREFIX.sub("", line) for line in stripped if line and line not in attribution]
    return [sentence for line in lines for sentence in sentences_of(line)]


def sentence_problems(body, attribution):
    assert isinstance(body, str), f"sentence_problems needs body text, got {type(body).__name__}. Fix: pass the body."
    sentences = prose_sentences(body, attribution)
    assert sentences, "the body has no sentences. Rule: a pull request body says what changed. Fix: write the body."
    long = [sentence for sentence in sentences if len(sentence.split()) > MAX_SENTENCE_WORDS]
    share = PERCENT * (len(sentences) - len(long)) // len(sentences)
    if share >= MIN_SHORT_SENTENCE_PERCENT:
        return []
    return [f"only {share} percent of sentences have {MAX_SENTENCE_WORDS} words or fewer, under {MIN_SHORT_SENTENCE_PERCENT}. Rule: ASD-STE100 shape. Fix: shorten, for example: {long[0][:60]}."]


def body_problems(body, facts, commits, patterns):
    assert body.strip(), "the body is empty. Rule: a pull request body says what changed. Fix: generate it with pr_text.py."
    assert commits, "body_problems got no commits. Rule: numbers are checked against the commit data. Fix: pass read_commits output."
    return [
        *number_problems(body, facts, commits),
        *private_problems(body, patterns),
        *phrase_problems(body),
        *sentence_problems(body, attribution_lines(commits)),
    ]


def parse_arguments(argv):
    assert isinstance(argv, list), f"parse_arguments needs a list, got {argv!r}. Fix: pass sys.argv[1:]."
    assert all(isinstance(item, str) for item in argv), f"every argument must be text, got {argv!r}"
    parser = argparse.ArgumentParser(prog="pr_text")
    parser.add_argument("--base", default=DEFAULT_BASE)
    parser.add_argument("--facts")
    parser.add_argument("--out")
    parser.add_argument("--check")
    parser.add_argument("--log")
    parser.add_argument("--write-facts")
    return parser.parse_args(argv)


def located(repo, name):
    assert repo, f"located got repo {repo!r}. Fix: pass the repository directory."
    assert name, f"located got name {name!r}. Rule: a path option names a file. Fix: pass the file name."
    return inside(Path(repo), name)


def write_facts(repo, log_name, facts_name):
    log_file = located(repo, log_name)
    facts_file = located(repo, facts_name)
    assert log_file.is_file(), f"{log_file} is not a file. Rule: facts come from a make check log. Fix: save the make check output there."
    assert facts_file.parent.is_dir(), f"{facts_file.parent} is not a directory. Fix: pass a facts path in an existing folder."
    try:
        facts = facts_from_log(log_file.read_text())
    except AssertionError as problem:
        print(f"pr_text: {problem}", file=sys.stderr)
        return EXIT_FAILED
    facts_file.write_text(json.dumps(facts, indent=2) + "\n")
    print(f"pr_text: wrote {facts_file}")
    return EXIT_CLEAN


def check_body(arguments, repo, environment):
    assert arguments.facts, "--check needs --facts. Rule: numbers are checked against facts. Fix: pass --facts <file>."
    body_file = located(repo, arguments.check)
    assert body_file.is_file(), f"{body_file} is not a file. Fix: pass the body file."
    _, patterns = private_names.read_patterns(environment)
    if not patterns:
        print("pr_text: the private denylist is missing or empty. Rule: the body is scanned for private names. Fix: see private_names.py.", file=sys.stderr)
        return EXIT_BLOCKED
    facts = json.loads(located(repo, arguments.facts).read_text())
    problems = body_problems(body_file.read_text(), facts, read_commits(repo, arguments.base), patterns)
    for problem in problems:
        print(f"pr_text: {problem}", file=sys.stderr)
    return EXIT_FAILED if problems else EXIT_CLEAN


def write_body(arguments, repo):
    assert arguments.facts, "generating needs --facts. Rule: the checks come from facts. Fix: pass --facts <file>."
    assert arguments.base, "generating needs --base. Rule: the range starts at the base. Fix: pass --base <revision>."
    facts = json.loads(located(repo, arguments.facts).read_text())
    body = build_body(read_commits(repo, arguments.base), facts)
    if arguments.out:
        located(repo, arguments.out).write_text(body)
    else:
        sys.stdout.write(body)
    return EXIT_CLEAN


def main(argv, repo, environment):
    assert repo, f"main got repo {repo!r}. Fix: pass the repository directory."
    arguments = parse_arguments(argv)
    try:
        if arguments.log:
            assert arguments.write_facts, "--log needs --write-facts. Rule: the log is turned into a facts file. Fix: pass --write-facts <file>."
            return write_facts(repo, arguments.log, arguments.write_facts)
        if arguments.check:
            return check_body(arguments, repo, environment)
        return write_body(arguments, repo)
    except PathOutsideRoot as problem:
        print(f"pr_text: {problem}", file=sys.stderr)
        return EXIT_FAILED


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:], os.getcwd(), os.environ))
