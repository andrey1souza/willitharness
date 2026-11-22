TESTS = (
    'tests/gates/test_message_check.py',
)

SOURCE = 'scripts/gates/message_check.py'

MUTANTS = (
    ('value-check-dropped', SOURCE, 'if not VALUE_PATTERN.search(text):', 'if False:'),
    ('rule-check-dropped', SOURCE, 'if RULE_MARKER not in text:', 'if False:'),
    ('fix-check-dropped', SOURCE, 'if not FIX_AT_END_PATTERN.search(text) or RULE_MARKER in text.rsplit(FIX_MARKER, 1)[-1]:', 'if False:'),
    ('fix-need-not-be-last', SOURCE, 'if not FIX_AT_END_PATTERN.search(text) or RULE_MARKER in text.rsplit(FIX_MARKER, 1)[-1]:', 'if FIX_MARKER not in text:'),
    ('fix-may-be-empty', SOURCE, 'FIX_AT_END_PATTERN = re.compile(r"Fix: [^\\n]+\\Z")', 'FIX_AT_END_PATTERN = re.compile(r"Fix:")'),
    ('value-needs-no-field', SOURCE, 'VALUE_PATTERN = re.compile(r"\\{[^}]*\\}|--[a-z]")', 'VALUE_PATTERN = re.compile(r"")'),
    ('exemption-ignores-file', SOURCE, 'entry.file_name == message.path.name and entry.text == message.text', 'entry.text == message.text'),
    ('exemption-ignores-text', SOURCE, 'entry.file_name == message.path.name and entry.text == message.text', 'entry.file_name == message.path.name'),
    ('exemption-by-prefix', SOURCE, 'entry.text == message.text', 'message.text.startswith(entry.text[:10])'),
    ('exemption-table-extra-entry', SOURCE, 'Exemption("report.py", "plan aborted; no verdict", "T47"),', 'Exemption("report.py", "plan aborted; no verdict", "T47"),\n    Exemption("cli.py", "error", "T47"),'),
    ('violation-exits-zero', SOURCE, 'EXIT_FAILED = 1', 'EXIT_FAILED = 0'),
    ('pass-line-reworded', SOURCE, 'name the value, state the rule and end with a fix"', 'name the value and state the rule"'),
    ('count-dropped', SOURCE, 'PASS_LINE.format(count=len(messages))', 'PASS_LINE.format(count=0)'),
    ('raise-not-scanned', SOURCE, 'if raised and node.exc.args:', 'if False:'),
    ('print-not-scanned', SOURCE, 'named_print = isinstance(call.func, ast.Name) and call.func.id == PRINT_NAME', 'named_print = False'),
    ('stderr-write-not-scanned', SOURCE, 'result = isinstance(function, ast.Attribute) and function.attr == WRITE_NAME and', 'result = False and'),
    ('print-to-stdout-scanned', SOURCE, 'to_stderr = any(keyword.arg == FILE_KEYWORD and ast.unparse(keyword.value).endswith(STDERR_NAME) for keyword in call.keywords)', 'to_stderr = True'),
    ('constant-not-resolved', SOURCE, 'result = constants.get(node.id)', 'result = None'),
    ('format-not-resolved', SOURCE, 'elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == FORMAT_NAME:', 'elif False:'),
    ('fstring-field-dropped', SOURCE, 'value.value if is_text(value) else INTERPOLATION_FIELD', 'value.value if is_text(value) else ""'),
    ('ambiguous-constant-kept', SOURCE, 'if name_counts[name] == 1}', 'if name_counts[name] >= 1}'),
    ('usage-exits-zero', SOURCE, 'EXIT_USAGE = 2', 'EXIT_USAGE = 0'),
    ('violation-lines-dropped', SOURCE, 'if problems and not is_exempt(message, exemptions):', 'if False:'),
)
