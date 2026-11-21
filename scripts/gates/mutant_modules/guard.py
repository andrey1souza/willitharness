TESTS = (
    'tests/unit/test_guard_unit.py',
    'tests/unit/test_guard_result_unit.py',
    'tests/unit/test_bypass_unit.py',
    'tests/gates/test_guard_corpus_gate.py',
    'tests/gates/test_conformance_gate.py',
    'tests/bdd/test_guard_scenarios.py',
    'tests/golden',
)

GUARD = 'src/willitharness/guard.py'
BYPASS = 'src/willitharness/bypass.py'
RESULT = 'src/willitharness/guard_result.py'
CONFORMANCE = 'src/willitharness/conformance.py'
DETECTORS = 'src/willitharness/detectors.py'

MUTANTS = (
    ('too-few-runs-counts-as-worse', GUARD, 'UNTESTED_COMPLETED_VERDICTS = frozenset({Verdict.INCONCLUSIVE_SMALL_N})', 'UNTESTED_COMPLETED_VERDICTS = frozenset()'),
    ('none-seen-counts-as-worse', GUARD, ' or coverage is Coverage.NONE_SEEN\n', '\n'),
    ('bypass-ignored', GUARD, 'coverage is Coverage.FULL and zero_bypass:', 'coverage is Coverage.FULL:'),
    ('partial-coverage-accepted', GUARD, 'coverage is Coverage.FULL and zero_bypass:', 'coverage is not Coverage.NONE_SEEN and zero_bypass:'),
    ('lower-completed-verdict-accepted', GUARD, 'NOT_MATCHING_COMPLETED_VERDICTS = frozenset({Verdict.FIRST_LOWER})', 'NOT_MATCHING_COMPLETED_VERDICTS = frozenset()'),
    ('env-wrapper-not-skipped', GUARD, 'words[0] == ENV_PROGRAM or ', ''),
    ('leading-assignment-not-skipped', GUARD, ' or ASSIGNMENT.match(words[0])', ''),
    ('flag-ignored-so-pgrep-passes', GUARD, '(not entry.flag_pattern or has_flag(words, entry.flag_pattern))', '(not entry.flag_pattern)'),
    ('flag-always-matches-so-plain-pgrep-blocks', GUARD, '(not entry.flag_pattern or has_flag(words, entry.flag_pattern))', 'True'),
    ('program-matched-anywhere-in-the-segment', GUARD, 'words[0] == entry.program and', 'entry.program in words and'),
    ('only-the-first-segment-is-checked', GUARD, 'for segment in map(program_words, shell_segments(command))', 'for segment in map(program_words, shell_segments(command)[:1])'),
    ('block-carries-no-message', GUARD, 'Decision(True, found[0].rule.message)', 'Decision(True, "")'),
    ('allowed-command-is-blocked', GUARD, 'Decision(True, found[0].rule.message) if found else Decision(False, "")', 'Decision(True, "x")'),
    ('target-is-the-first-operand', GUARD, 'result = operands[-1] if', 'result = operands[0] if'),
    ('target-needs-no-second-operand', GUARD, 'len(operands) >= MIN_TARGET_OPERANDS', 'len(operands) >= 1'),
    ('rm-has-a-written-target', GUARD, 'hit.entry.writes_target and len(operands)', 'len(operands)'),
    ('prefix-ignores-the-placeholder', GUARD, '        if PLACEHOLDER.match(word):\n            break\n', '        if False:\n            break\n'),
    ('message-without-alternatives-accepted', GUARD, 'runnable = bool(alternatives) and all(', 'runnable = all('),
    ('unquoted-alternative-accepted', GUARD, 'offered_prefix(alternative) and alternative in named for', 'offered_prefix(alternative) for'),
    ('any-blocked-command-gives-full-coverage', GUARD, 'elif all(decide_command(command, rules).blocked for command in violating):', 'elif any(decide_command(command, rules).blocked for command in violating):'),
    ('no-violating-command-gives-full-coverage', GUARD, '    if not violating:\n        result = Coverage.NONE_SEEN\n    elif', '    if False:\n        result = Coverage.NONE_SEEN\n    elif'),
    ('rejected-messages-exit-zero', GUARD, 'REJECTED_EXIT_CODE = 1', 'REJECTED_EXIT_CODE = 0'),
    ('another-tool-ignored', BYPASS, '        if call.tool in EDIT_TOOLS:', '        if False:'),
    ('path-needs-no-exact-match', BYPASS, 'normal_written == normal_target or ', ''),
    ('path-suffix-needs-no-separator', BYPASS, 'endswith(PATH_SEPARATOR + normal_target)', 'endswith(normal_target)'),
    ('offered-absolute-call-is-a-channel', BYPASS, 'if not any(prefix and segment[:len(prefix)] == prefix for prefix in offered)]', 'if True]'),
    ('plain-program-is-a-channel', BYPASS, 'PATH_SEPARATOR in words[0] and ', ''),
    ('any-absolute-path-is-a-channel', BYPASS, 'posixpath.basename(words[0]) in programs', 'True'),
    ('any-command-is-an-equivalent', BYPASS, 'equivalent = any(marker in " ".join(segment) for segment in segments for marker in markers)', 'equivalent = bool(markers) and bool(segments)'),
    ('alternative-channel-counts-as-bypass', BYPASS, 'result = self.other_tool or self.equivalent_command\n', 'result = self.other_tool or self.equivalent_command or self.alternative_channel\n'),
    ('equivalent-command-not-counted', BYPASS, 'result = self.other_tool or self.equivalent_command\n', 'result = self.other_tool\n'),
    ('quiet-channels-listed', BYPASS, 'for text, count in counted.items() if count]', 'for text, count in counted.items()]'),
    ('transcript-path-field-misread', DETECTORS, 'FILE_PATH_FIELD = "file_path"', 'FILE_PATH_FIELD = "path"'),
    ('guard-and-rule-arms-swapped', RESULT, 'verdict_of(pooled_completed(records, guards), pooled_completed(records, rules[:1]))', 'verdict_of(pooled_completed(records, rules[:1]), pooled_completed(records, guards))'),
    ('unusable-guard-runs-counted', RESULT, ' and run.state is RunState.RECORDED_USABLE]', ']'),
    ('bypass-left-out-of-the-result', RESULT, 'evaluate(completed, coverage, bypass.successes == 0)', 'evaluate(completed, coverage, True)'),
    ('coverage-assumed-full', RESULT, 'if actions else Coverage.NONE_SEEN', 'if actions else Coverage.FULL'),
    ('required-detector-counts-as-violations', RESULT, 'rule.detector.kind == KIND_FORBIDDEN', 'True'),
    ('guard-conformance-never-mismatches', CONFORMANCE, 'found.append(f"guard {row}: lean={expected} python={got}")', 'pass'),
    ('guard-conformance-omits-the-case', CONFORMANCE, 'found.append(f"guard {row}: lean=', 'found.append(f"guard: lean='),
    ('guard-conformance-rejects-no-guard-arm', CONFORMANCE, 'completed = None if row["completed"] == NO_GUARD_ARM else Verdict(row["completed"])', 'completed = Verdict(row["completed"])'),
)
