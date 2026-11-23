import argparse
import json
import random
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from willitharness.probe import DEFAULT_LABEL, PROMPT_TEMPLATE

EXIT_OK = 0
EXIT_USAGE = 2
SEED_REQUIRED_MESSAGE = "seed required; pass --seed N. Rule: a fake run is reproducible from its seed. Fix: pass --seed N."
CONTEXT_FILE = "CLAUDE.md"
FALLBACK_FILE = "AGENTS.md"
NO_VALUE_REPLY = "NONE"
CERTAIN_RECALL = 1.0


@dataclass(frozen=True)
class Behavior:
    seed: int
    recall: float = CERTAIN_RECALL
    unseen_reply: str = NO_VALUE_REPLY


@dataclass(frozen=True)
class Location:
    directory: Path
    boundary: Path


def directory_chain(directory, boundary):
    assert directory.is_dir(), f"{directory} is not a directory. Fix: pass the directory the agent starts in."
    assert boundary == directory or boundary in directory.parents, (
        f"{boundary} is not {directory} or one of its parents. Rule: the walk up stops at the boundary. Fix: pass a parent as the boundary."
    )
    chain = [directory]
    while chain[-1] != boundary:
        chain.append(chain[-1].parent)
    return chain


def context_files(directory, boundary):
    chain = directory_chain(directory, boundary)
    primary = [folder / CONTEXT_FILE for folder in chain if (folder / CONTEXT_FILE).is_file()]
    fallback = [folder / FALLBACK_FILE for folder in chain if (folder / FALLBACK_FILE).is_file()]
    chosen = primary or fallback
    assert not (primary and set(chosen) & set(fallback)), f"the fallback file leaked into the context: {chosen}"
    assert all(path.is_file() for path in chosen), f"context files must exist: {chosen}"
    return chosen


def visible_values(files, label):
    assert label, "visible_values needs a label. Fix: name the label to look for."
    assert all(isinstance(path, Path) for path in files), f"files must be paths, got {files!r}. Rule: the agent reads files from disk. Fix: pass pathlib.Path items."
    pattern = re.compile(re.escape(label) + r":\s*(\S+)")
    values = []
    for path in files:
        values.extend(pattern.findall(path.read_text()))
    return values


def reply_for(values, behavior, run_index):
    assert 0.0 <= behavior.recall <= CERTAIN_RECALL, f"recall must lie between 0 and 1, got {behavior.recall}. Fix: pass a probability."
    assert behavior.unseen_reply, "the reply for an unseen value cannot be empty. Fix: pass NONE or a made-up value."
    draw = random.Random(f"{behavior.seed}:{run_index}").random()
    reply = values[0] if values and draw < behavior.recall else behavior.unseen_reply
    assert reply in (behavior.unseen_reply, *values), f"the reply {reply!r} is neither a visible value nor the unseen reply"
    return reply


def run_agent(behavior, location, label, run_index):
    assert isinstance(behavior.seed, int) and not isinstance(behavior.seed, bool), (
        f"seed must be a whole number, got {behavior.seed!r}. Fix: pass --seed N."
    )
    assert run_index >= 0, f"run_index must not be negative, got {run_index}. Fix: count runs from 0."
    directory = location.directory
    values = visible_values(context_files(directory, location.boundary), label)
    reply = reply_for(values, behavior, run_index)
    prompt = PROMPT_TEMPLATE.format(label=label)
    lines = [
        {"type": "system", "subtype": "init", "cwd": str(directory)},
        {"type": "user", "message": {"role": "user", "content": prompt}},
        {"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": reply}]}},
        {"type": "result", "subtype": "success", "is_error": False, "result": reply},
    ]
    transcript = [json.dumps(line, sort_keys=True) for line in lines]
    assert len(transcript) == len(lines), "every event must become one line"
    return transcript


def main(argv):
    assert isinstance(argv, list), f"main needs a list of arguments, got {argv!r}. Fix: pass sys.argv[1:]."
    assert all(isinstance(item, str) for item in argv), f"every argument must be text, got {argv!r}"
    parser = argparse.ArgumentParser(prog="fakeagent")
    parser.add_argument("--seed", type=int)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--boundary", type=Path, required=True)
    parser.add_argument("--label", default=DEFAULT_LABEL)
    parser.add_argument("--run-index", type=int, default=0)
    parser.add_argument("--recall", type=float, default=CERTAIN_RECALL)
    arguments = parser.parse_args(argv)
    if arguments.seed is None:
        print(SEED_REQUIRED_MESSAGE, file=sys.stderr)
        return EXIT_USAGE
    transcript = run_agent(
        Behavior(arguments.seed, arguments.recall),
        Location(arguments.directory, arguments.boundary),
        arguments.label,
        arguments.run_index,
    )
    sys.stdout.write("\n".join(transcript) + "\n")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
