import argparse
import json
import sys
from pathlib import Path

import gates
from extract import site_data
from render import render_site
from willitharness.paths import inside

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = Path("build") / "site"
EXIT_BUILT = 0
EXIT_PROBLEMS = 1


def build_problems(root):
    assert isinstance(root, Path), f"build_problems needs a Path root, got {root!r}. Fix: pass the repository root."
    assert root.is_dir(), f"{root} is not a directory. Fix: pass the repository root."
    data = site_data(root)
    files = render_site(root, data)
    problems = gates.site_problems(root, files, data, gates.recomputed_counts(root))
    assert isinstance(problems, list), f"site_problems must return a list, got {type(problems).__name__}"
    return files, problems


def write_site(root, output, files):
    assert files, "write_site got no files. Rule: a build writes the page. Fix: render first."
    assert isinstance(root, Path), f"write_site needs a Path root, got {root!r}. Fix: pass the repository root."
    destination = inside(root, output)
    destination.mkdir(parents=True, exist_ok=True)
    for name, text in files.items():
        (destination / name).write_text(text)
    assert all((destination / name).is_file() for name in files), f"the build left a file missing under {destination}"


def main(argv):
    assert isinstance(argv, list), f"main needs a list of arguments, got {argv!r}. Fix: pass sys.argv[1:]."
    assert all(isinstance(item, str) for item in argv), f"every argument must be text, got {argv!r}"
    parser = argparse.ArgumentParser(prog="build")
    parser.add_argument("--root", type=Path, default=REPO_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args(argv)
    files, problems = build_problems(arguments.root)
    for problem in problems:
        print(f"site: {problem}")
    if problems:
        return EXIT_PROBLEMS
    sizes = {name: len(text.encode()) for name, text in files.items()}
    if arguments.check:
        print(f"site: checks passed, {sum(sizes.values())} bytes in {len(files)} files, nothing written")
        return EXIT_BUILT
    write_site(arguments.root, arguments.output, files)
    print(f"site: built {json.dumps(sizes, sort_keys=True)} into {inside(arguments.root, arguments.output)}")
    return EXIT_BUILT


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
