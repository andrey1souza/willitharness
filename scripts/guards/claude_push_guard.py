import json
import re
import shlex
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

SEGMENT_SPLIT = re.compile(r"&&|\|\||;|\||\n")
HOOK_SKIP_FLAG = "--no-verify"
HOOK_PATH_OVERRIDE = "core.hookspath"
HOOKED_SUBCOMMANDS = {"commit", "push", "merge", "rebase"}
BLOCK_EXIT_CODE = 2
ALLOW_EXIT_CODE = 0
BASH_TOOL = "Bash"
KIND_SKIPS_HOOKS = "skips_hooks"
KIND_OTHER = "other"
SEGMENT_KINDS = (KIND_SKIPS_HOOKS, KIND_OTHER)
HOOK_SKIP_MESSAGE = (
    "guard: skipping git hooks is not allowed (--no-verify or a core.hooksPath override). "
    "Rule: the hooks run the checks that keep this repo clean. "
    "Fix: run the command without the flag and fix what the hook reports."
)


def segment_words(segment):
    assert isinstance(segment, str), (
        "segment_words needs text but got %r. Rule: shlex splits text. "
        "Fix: pass one piece of the command string." % (segment,)
    )
    try:
        words = shlex.split(segment)
    except ValueError:
        words = segment.split()
    assert segment.strip() or not words, (
        "segment %r is blank but produced words %r. Rule: a blank segment has no words. "
        "Fix: check the split." % (segment, words)
    )
    return words


def git_segments(command):
    assert isinstance(command, str), (
        "git_segments needs text but got %r. Rule: the hook reads a command string. "
        "Fix: pass tool_input.command." % (command,)
    )
    words_per_segment = [segment_words(segment) for segment in SEGMENT_SPLIT.split(command)]
    git_only = [words for words in words_per_segment if words and words[0] == "git"]
    assert all(words[0] == "git" for words in git_only), (
        "non-git segments remained in %r. Rule: only git segments are judged. "
        "Fix: filter on the first word." % (git_only,)
    )
    return git_only


def segment_kind(words):
    assert words and words[0] == "git", (
        "segment_kind needs a git segment but got %r. Rule: only git commands are classified. "
        "Fix: call git_segments first." % (words,)
    )
    skips_hooks = bool(HOOKED_SUBCOMMANDS.intersection(words[1:])) and (
        HOOK_SKIP_FLAG in words or any(HOOK_PATH_OVERRIDE in word.lower() for word in words)
    )
    kind = KIND_SKIPS_HOOKS if skips_hooks else KIND_OTHER
    assert kind in SEGMENT_KINDS, (
        "segment %r got kind %r. Rule: a kind is one of %r. Fix: return a listed kind."
        % (words, kind, SEGMENT_KINDS)
    )
    return kind


def verdict_for(command):
    assert isinstance(command, str), (
        "verdict_for needs text but got %r. Rule: the hook judges a command string. "
        "Fix: pass tool_input.command." % (command,)
    )
    kinds = [segment_kind(words) for words in git_segments(command)]
    verdict = (BLOCK_EXIT_CODE, HOOK_SKIP_MESSAGE) if KIND_SKIPS_HOOKS in kinds else (ALLOW_EXIT_CODE, "")
    assert verdict[0] in (ALLOW_EXIT_CODE, BLOCK_EXIT_CODE), (
        "verdict_for built code %r for %r. Rule: the hook exits 0 or 2. "
        "Fix: return a listed code." % (verdict[0], command)
    )
    return verdict


def main(stdin):
    event = json.load(stdin)
    assert isinstance(event, dict), (
        "hook input was %r. Rule: Claude Code sends a JSON object. "
        "Fix: check the hook wiring in .claude/settings.json." % (event,)
    )
    if event.get("tool_name") != BASH_TOOL:
        return ALLOW_EXIT_CODE
    command = event.get("tool_input", {}).get("command", "")
    code, message = verdict_for(command)
    assert code in (ALLOW_EXIT_CODE, BLOCK_EXIT_CODE), (
        "verdict_for returned code %r for %r. Rule: the hook exits 0 or 2. "
        "Fix: return a listed code." % (code, command)
    )
    if message:
        print(message, file=sys.stderr)
    return code


if __name__ == "__main__":
    sys.exit(main(sys.stdin))
