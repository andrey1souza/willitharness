TESTS = ("tests/gates/test_real_runner.py",)
SOURCE = "src/willitharness/real_runner.py"

MUTANTS = (
    ("timeout-ignored", SOURCE, "while time.monotonic() < deadline and read_state(folder) is PlanState.RUNNING:", "while read_state(folder) is PlanState.RUNNING:"),
    ("abort-ignored", SOURCE, "while time.monotonic() < deadline and read_state(folder) is PlanState.RUNNING:", "while time.monotonic() < deadline:"),
    ("process-left-alive-after-timeout", SOURCE, "        kill_group(process)\n        process.communicate()\n        return None\n", "        process.communicate()\n        return None\n"),
    ("timeout-recorded-as-finished", SOURCE, "return TIMED_OUT if output is None else finished(output.splitlines())", "return finished((output or \"\").splitlines())"),
    ("run-cap-not-passed-as-budget", SOURCE, "command = build_command(prompt, runner.model, site.plan.run_cap_usd)", "command = build_command(prompt, runner.model, 1)"),
    ("sandbox-dropped", SOURCE, "        sandboxed_command(command, profile),\n", "        command,\n"),
    ("environment-unscrubbed", SOURCE, "environment = {**agent_environment(os.environ), TEMP_VARIABLE", "environment = {**os.environ, TEMP_VARIABLE"),
    ("private-temp-folder-dropped", SOURCE, "environment = {**agent_environment(os.environ), TEMP_VARIABLE: str(run_root / SCRATCH_NAME)}", "environment = agent_environment(os.environ)"),
    ("config-folder-not-writable", SOURCE, "extras = (run_root / SCRATCH_NAME, agent_config_directory(environ, home), home / HOME_STATE_NAME)", "extras = (run_root / SCRATCH_NAME, home / HOME_STATE_NAME)"),
    ("world-not-copied", SOURCE, "    shutil.copytree(site.world_dir, work)\n", "    work.mkdir()\n"),
    ("overlay-not-applied", SOURCE, "    shutil.copytree(inside(site.root, arms[arm_label].overlay), work, dirs_exist_ok=True)\n", ""),
    ("overlay-check-dropped", SOURCE, "        if not overlay.is_dir():", "        if False:"),
    ("system-prompt-channel-allowed", SOURCE, 'UNSUPPORTED_CHANNEL = "system_prompt"', 'UNSUPPORTED_CHANNEL = "unsupported"'),
    ("workspace-kept-after-run", SOURCE, "    with tempfile.TemporaryDirectory(prefix=RUN_DIRECTORY_PREFIX) as directory:\n        run_root = Path(directory).resolve()\n", "    directory = tempfile.mkdtemp(prefix=RUN_DIRECTORY_PREFIX)\n    if True:\n        run_root = Path(directory).resolve()\n"),
)
