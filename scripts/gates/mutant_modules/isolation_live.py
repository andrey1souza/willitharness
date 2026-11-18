TESTS = ("tests/gates/test_isolation_live.py",)

MUTANTS = (
    ("memory-file-never-restored", "scripts/gates/isolation_live.py", "    finally:\n        if existed:\n            memory_file.write_bytes(original)\n        else:\n            memory_file.unlink()\n", "    finally:\n        pass\n"),
    ("existing-file-deleted-instead-of-restored", "scripts/gates/isolation_live.py", "        if existed:\n            memory_file.write_bytes(original)\n", "        if False:\n            memory_file.write_bytes(original)\n"),
    ("leak-ignored", "scripts/gates/isolation_live.py", "if isolated is not Reach.MASKED or unisolated is not Reach.LOADED or total > COST_CAP_USD:", "if unisolated is not Reach.LOADED or total > COST_CAP_USD:"),
    ("control-ignored", "scripts/gates/isolation_live.py", "if isolated is not Reach.MASKED or unisolated is not Reach.LOADED or total > COST_CAP_USD:", "if isolated is not Reach.MASKED or total > COST_CAP_USD:"),
    ("cost-cap-ignored", "scripts/gates/isolation_live.py", "if isolated is not Reach.MASKED or unisolated is not Reach.LOADED or total > COST_CAP_USD:", "if isolated is not Reach.MASKED or unisolated is not Reach.LOADED:"),
    ("not-proven-exits-zero", "scripts/gates/isolation_live.py", "        print(NOT_PROVEN_MESSAGE)\n        return EXIT_NOT_PROVEN", "        print(NOT_PROVEN_MESSAGE)\n        return EXIT_PASSED"),
    ("marker-never-planted", "scripts/gates/isolation_live.py", "    memory_file.write_bytes(original + f\"\\n{MARKER_LABEL}: {marker}\\n\".encode())\n", "    memory_file.write_bytes(original)\n"),
)
