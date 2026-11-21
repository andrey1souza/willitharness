TESTS = ("tests/gates/test_sandbox_live.py",)
SOURCE = "scripts/gates/sandbox_live.py"

MUTANTS = (
    ("outside-write-word-ignored", SOURCE, "BLOCKED_WRITE not in words or WROTE_OUTSIDE in words or outside_exists", "BLOCKED_WRITE not in words or outside_exists"),
    ("outside-file-on-disk-ignored", SOURCE, "BLOCKED_WRITE not in words or WROTE_OUTSIDE in words or outside_exists", "BLOCKED_WRITE not in words or WROTE_OUTSIDE in words"),
    ("blocked-write-not-required", SOURCE, "BLOCKED_WRITE not in words or WROTE_OUTSIDE in words or outside_exists", "WROTE_OUTSIDE in words or outside_exists"),
    ("inside-write-not-required", SOURCE, "WROTE_INSIDE not in words or BLOCKED_INSIDE in words", "BLOCKED_INSIDE in words"),
    ("inside-block-ignored", SOURCE, "WROTE_INSIDE not in words or BLOCKED_INSIDE in words", "WROTE_INSIDE not in words"),
    ("ssh-read-ignored", SOURCE, "BLOCKED_SSH not in words or READ_SSH in words", "BLOCKED_SSH not in words"),
    ("blocked-ssh-not-required", SOURCE, "BLOCKED_SSH not in words or READ_SSH in words", "READ_SSH in words"),
    ("network-open-ignored", SOURCE, "NET_BLOCKED not in words or NET_OK in words", "NET_BLOCKED not in words"),
    ("network-block-not-required", SOURCE, "NET_BLOCKED not in words or NET_OK in words", "NET_OK in words"),
    ("stub-output-ignored", SOURCE, "(STUB_FAILURE, STUB_OUTPUT not in reply),\n", ""),
    ("calls-log-ignored", SOURCE, "        (CALLS_FAILURE, STUB_COMMAND not in [line.split()[0] for line in calls.splitlines() if line.split()]),\n", ""),
    ("cost-cap-ignored", SOURCE, "(COST_FAILURE, cost > COST_CAP_USD)", "(COST_FAILURE, False)"),
    ("failure-exits-zero", SOURCE, "        print(NOT_PROVEN_MESSAGE)\n        return EXIT_FAILED\n    print(\"GATE", "        print(NOT_PROVEN_MESSAGE)\n        return EXIT_PASSED\n    print(\"GATE"),
    ("missing-secret-folder-accepted", SOURCE, "    if not (user_home / SSH_FOLDER).exists():\n", "    if False:\n"),
    ("outside-file-not-cleaned", SOURCE, "        outside.unlink(missing_ok=True)\n", "        pass\n"),
    ("network-probe-ignores-http-errors", SOURCE, "curl -sfI -m", "curl -sI -m"),
    ("settings-not-passed", SOURCE, "settings=sandbox_settings(work, run_root, home, NO_DOMAINS))", 'settings="")'),
    ("allowlist-widened", SOURCE, 'ALLOWED_COMMANDS = ("bash",)', 'ALLOWED_COMMANDS = ("bash", "curl")'),
    ("bash-tool-dropped", SOURCE, "claude_agent.tool_policy(False, ALLOWED_COMMANDS)", "claude_agent.PROBE_POLICY"),
    ("cost-cap-raised-above-budget-check", SOURCE, "COST_CAP_USD = 0.05", "COST_CAP_USD = 0.5"),
    ("pass-line-changed", SOURCE, 'print("GATE SANDBOX PASS")', 'print("ok")'),
)
