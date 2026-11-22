import ast
import re
import sys
from collections import Counter
from pathlib import Path
from typing import NamedTuple

EXIT_PASSED = 0
EXIT_FAILED = 1
EXIT_USAGE = 2
SOURCE_PATTERN = "*.py"
RULE_MARKER = "Rule:"
FIX_MARKER = "Fix:"
INTERPOLATION_FIELD = "{}"
VALUE_PATTERN = re.compile(r"\{[^}]*\}|--[a-z]")
FIX_AT_END_PATTERN = re.compile(r"Fix: [^\n]+\Z")
STDERR_NAME = "stderr"
PRINT_NAME = "print"
FORMAT_NAME = "format"
WRITE_NAME = "write"
FILE_KEYWORD = "file"
MISSING_VALUE = "the value"
MISSING_RULE = "the rule"
MISSING_FIX = "a closing fix"
PASS_LINE = "all {count} failure messages name the value, state the rule and end with a fix"


class Exemption(NamedTuple):
    file_name: str
    text: str
    task: str


class FailureMessage(NamedTuple):
    path: Path
    line: int
    text: str


EXEMPTIONS = (
    Exemption("report.py", "no verdicts yet; run: willitharness analyze", "T47"),
    Exemption("report.py", "plan aborted; no verdict", "T47"),
)


def is_text(node):
    assert isinstance(node, ast.AST), f"is_text needs a syntax node, got {node!r}. Fix: pass a node from ast.parse."
    result = isinstance(node, ast.Constant) and isinstance(node.value, str)
    assert result is True or result is False, f"is_text built the non-boolean {result!r}"
    return result


def module_constants(tree):
    assert isinstance(tree, ast.Module), f"module_constants needs a parsed module, got {tree!r}. Fix: pass ast.parse output."
    result = {}
    for statement in tree.body:
        single_name = isinstance(statement, ast.Assign) and len(statement.targets) == 1 and isinstance(statement.targets[0], ast.Name)
        if single_name and is_text(statement.value):
            result[statement.targets[0].id] = statement.value.value
    assert all(isinstance(text, str) for text in result.values()), f"module_constants kept a non-text value in {result!r}"
    return result


def shared_constants(trees):
    assert isinstance(trees, list), f"shared_constants needs a list of modules, got {trees!r}. Fix: pass the parsed modules."
    tables = [module_constants(tree) for tree in trees]
    name_counts = Counter(name for table in tables for name in table)
    result = {name: text for table in tables for name, text in table.items() if name_counts[name] == 1}
    assert all(name_counts[name] == 1 for name in result), f"shared_constants kept an ambiguous name in {sorted(result)}"
    return result


def literal_of(node, constants):
    assert isinstance(constants, dict), f"literal_of needs a constant table, got {constants!r}. Fix: build it with shared_constants."
    result = None
    if is_text(node):
        result = node.value
    elif isinstance(node, ast.Name):
        result = constants.get(node.id)
    assert result is None or isinstance(result, str), f"literal_of built a non-text value from {ast.dump(node)}"
    return result


def template_of(node, constants):
    assert isinstance(constants, dict), f"template_of needs a constant table, got {constants!r}. Fix: build it with shared_constants."
    result = literal_of(node, constants)
    if isinstance(node, ast.JoinedStr):
        parts = [value.value if is_text(value) else INTERPOLATION_FIELD for value in node.values]
        result = "".join(parts)
    elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == FORMAT_NAME:
        result = literal_of(node.func.value, constants)
    assert result is None or isinstance(result, str), f"template_of built a non-text message from {ast.dump(node)}"
    return result


def prints_to_stderr(call):
    assert isinstance(call, ast.Call), f"prints_to_stderr needs a call, got {call!r}. Fix: pass a Call node."
    named_print = isinstance(call.func, ast.Name) and call.func.id == PRINT_NAME
    to_stderr = any(keyword.arg == FILE_KEYWORD and ast.unparse(keyword.value).endswith(STDERR_NAME) for keyword in call.keywords)
    result = named_print and to_stderr
    assert result is True or result is False, f"prints_to_stderr built the non-boolean {result!r}"
    return result


def writes_to_stderr(call):
    assert isinstance(call, ast.Call), f"writes_to_stderr needs a call, got {call!r}. Fix: pass a Call node."
    function = call.func
    result = isinstance(function, ast.Attribute) and function.attr == WRITE_NAME and ast.unparse(function.value).endswith(STDERR_NAME)
    assert result is True or result is False, f"writes_to_stderr built the non-boolean {result!r}"
    return result


def message_nodes(tree):
    assert isinstance(tree, ast.Module), f"message_nodes needs a parsed module, got {tree!r}. Fix: pass ast.parse output."
    result = []
    for node in ast.walk(tree):
        raised = isinstance(node, ast.Raise) and isinstance(node.exc, ast.Call)
        if raised and node.exc.args:
            result.append((node.lineno, node.exc.args[0]))
        if isinstance(node, ast.Call) and node.args and (prints_to_stderr(node) or writes_to_stderr(node)):
            result.append((node.lineno, node.args[0]))
    assert all(isinstance(line, int) for line, _ in result), f"message_nodes lost a line number in {result!r}"
    return result


def failure_messages(root):
    assert Path(root).is_dir(), f"failure_messages needs a source directory, got {root!r}. Fix: pass the folder to scan, for example src."
    paths = sorted(Path(root).rglob(SOURCE_PATTERN))
    trees = [ast.parse(path.read_text(), filename=str(path)) for path in paths]
    constants = shared_constants(trees)
    result = []
    for path, tree in zip(paths, trees):
        for line, node in message_nodes(tree):
            text = template_of(node, constants)
            if text is not None:
                result.append(FailureMessage(path, line, text))
    assert all(isinstance(message.text, str) for message in result), f"failure_messages built a non-text message in {root}"
    return result


def problems_of(text):
    assert isinstance(text, str), f"problems_of needs message text, got {text!r}. Fix: pass the message string."
    result = []
    if not VALUE_PATTERN.search(text):
        result.append(MISSING_VALUE)
    if RULE_MARKER not in text:
        result.append(MISSING_RULE)
    if not FIX_AT_END_PATTERN.search(text) or RULE_MARKER in text.rsplit(FIX_MARKER, 1)[-1]:
        result.append(MISSING_FIX)
    assert all(problem in (MISSING_VALUE, MISSING_RULE, MISSING_FIX) for problem in result), f"problems_of built an unknown problem in {result!r}"
    return tuple(result)


def is_exempt(message, exemptions):
    assert isinstance(message, FailureMessage), f"is_exempt needs a FailureMessage, got {message!r}. Fix: build it with failure_messages."
    assert all(isinstance(entry, Exemption) for entry in exemptions), f"is_exempt needs Exemption entries, got {exemptions!r}. Fix: build them with Exemption."
    result = any(entry.file_name == message.path.name and entry.text == message.text for entry in exemptions)
    assert result is True or result is False, f"is_exempt built the non-boolean {result!r}"
    return result


def violation_lines(messages, exemptions):
    assert isinstance(messages, list), f"violation_lines needs a list of messages, got {messages!r}. Fix: build it with failure_messages."
    result = []
    for message in messages:
        problems = problems_of(message.text)
        if problems and not is_exempt(message, exemptions):
            missing = " and ".join(problems)
            result.append(
                f"{message.path}:{message.line}: the message {message.text!r} lacks {missing}. "
                f"Rule: every failure message names the value, states the rule and ends with a fix. Fix: write it as '<value> ... Rule: <rule>. Fix: <fix>.'"
            )
    assert len(result) <= len(messages), f"violation_lines found more violations than messages: {len(result)} of {len(messages)}"
    return result


def scan_exit_code(root):
    messages = failure_messages(root)
    assert messages, f"{root} holds no failure messages. Rule: a gate that finds nothing proves nothing. Fix: pass the source folder."
    violations = violation_lines(messages, EXEMPTIONS)
    if violations:
        print("\n".join(violations))
        result = EXIT_FAILED
    else:
        print(PASS_LINE.format(count=len(messages)))
        result = EXIT_PASSED
    assert result in (EXIT_PASSED, EXIT_FAILED), f"scan_exit_code built the unknown code {result!r}"
    return result


def main(arguments):
    assert isinstance(arguments, list), f"main needs the argument list, got {arguments!r}. Fix: pass sys.argv[1:]."
    if len(arguments) != 1:
        print(f"usage: message_check.py <source-folder>, got {arguments!r}. Rule: the gate scans one folder. Fix: pass src.")
        return EXIT_USAGE
    result = scan_exit_code(Path(arguments[0]))
    assert result in (EXIT_PASSED, EXIT_FAILED), f"main built the unknown code {result!r}"
    return result


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
