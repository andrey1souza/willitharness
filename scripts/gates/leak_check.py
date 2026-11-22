import re
import sys
from pathlib import Path

EXIT_CLEAN = 0
EXIT_LEAK = 1
EXIT_USAGE = 2
HOME_PATH = re.compile(r"(?:/Users|/home)/[^/\s\"'`]+/|[A-Za-z]:\\Users\\[^\\\s\"'`]+\\")
SUMMARY_CLEAN = "leak-check: clean"
SUMMARY_FOUND = "leak-check: found {count}"
USAGE = "leak-check: name at least one folder. Rule: the check scans the folders it is given. Fix: pass folders such as src tests docs."


def text_files(folder):
    assert folder.is_dir(), f"{folder} is not a folder. Rule: the check scans folders. Fix: pass an existing folder."
    files = sorted(path for path in folder.rglob("*") if path.is_file())
    assert all(path.is_relative_to(folder) for path in files), f"files {files!r} escape {folder}. Rule: scan only inside the folder. Fix: check rglob."
    return files


def leak_lines(folder, path):
    resolved_folder = folder.resolve()
    resolved = path.resolve()
    assert resolved.is_relative_to(resolved_folder), f"{path} resolves outside {folder}. Rule: read only files beneath the scanned folder. Fix: skip symlinks that leave it."
    assert resolved.is_file(), f"{path} is not a file. Rule: the check reads files. Fix: pass files from text_files."
    try:
        text = resolved.read_text()
    except UnicodeDecodeError:
        return []
    found = [f"{path}:{number}" for number, line in enumerate(text.splitlines(), start=1) if HOME_PATH.search(line)]
    assert len(found) <= len(text.splitlines()), f"{len(found)} leaks in {len(text.splitlines())} lines. Rule: one leak per line. Fix: check the loop."
    return found


def leaks_in(folders):
    assert folders, USAGE
    scanned = [Path(folder) for folder in folders]
    leaks = [leak for folder in scanned for path in text_files(folder) if path.resolve().is_relative_to(folder.resolve()) for leak in leak_lines(folder, path)]
    assert all(isinstance(leak, str) for leak in leaks), f"leaks {leaks!r} must be text. Fix: check leak_lines."
    return leaks


def main(arguments):
    assert isinstance(arguments, list), f"arguments {arguments!r} must be a list. Rule: main takes the argument list. Fix: pass sys.argv[1:]."
    if not arguments:
        print(USAGE, file=sys.stderr)
        return EXIT_USAGE
    leaks = leaks_in(arguments)
    assert all(":" in leak for leak in leaks), f"leaks {leaks!r} must read path:line. Fix: check leak_lines."
    for leak in leaks:
        print(leak)
    print(SUMMARY_FOUND.format(count=len(leaks)) if leaks else SUMMARY_CLEAN)
    code = EXIT_LEAK if leaks else EXIT_CLEAN
    assert code in (EXIT_CLEAN, EXIT_LEAK), f"exit code {code!r} is not clean or leak. Fix: check main."
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
