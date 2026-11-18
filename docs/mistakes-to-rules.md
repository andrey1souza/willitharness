# Mistakes and the rules that catch them

Each mistake below happened, or nearly happened, in this project. The fix is a
check that rules out the whole category, never a line of prose. A test shows that
the check can fail. `scripts/gates/repo_checks.py` fails when a row names a
test that does not exist.

## Mistakes caught by a rule

| Mistake | Category | Rule | Test |
|---|---|---|---|
| A push could reach the remote outside the agreed hours (18:00 to 08:59). | A push outside the agreed window | `scripts/guards/push_window.py`, called by `.githooks/pre-push`, and for agents by `scripts/guards/claude_push_guard.py` | `tests/guards/test_push_window.py::test_window_boundaries`; `tests/guards/test_claude_push_guard.py::test_push_outside_the_window_is_blocked` |
| The hooks could be skipped with `--no-verify` or a `core.hooksPath` override. | Skipping the checks | `scripts/guards/claude_push_guard.py` | `tests/guards/test_claude_push_guard.py::test_skipping_hooks_is_blocked_inside_the_window` |
| The global git identity is a work-linked account, so a commit here could carry it. Found while creating the repo. | Wrong commit identity | `scripts/guards/identity.py`, called by `.githooks/pre-commit` | `tests/guards/test_identity.py::test_other_account_address_is_rejected_with_a_fix` |
| `gh` tried to create the repo as the work account, because the global git config sets a credential username and a new repo inherits it. Found while publishing. | A default account taken from global config | `scripts/guards/identity.py` reads only the repo-local `credential.https://github.com.username`, called by `.githooks/pre-commit` | `tests/guards/test_identity.py::test_global_account_setting_does_not_count` |
| Private terms could reach a public repository. | A private name in public text | `scripts/guards/private_names.py`, called by both hooks | `tests/guards/test_private_names.py::test_staged_term_is_reported_without_echoing_the_term` |
| The private-names scan first put the revision before the pattern file, so git failed in revision mode. The first test of that mode found it. | A guard whose second mode was never exercised | `scripts/guards/private_names.py` | `tests/guards/test_private_names.py::test_committed_term_is_found_by_revision` |
| A fix could ship with no check, so the same error could return unseen. | A fix shipped without a lasting guard | `scripts/guards/fix_needs_rule.py`, called by `.githooks/pre-push` | `tests/guards/test_fix_needs_rule.py::test_fix_without_a_check_is_rejected` |
| The raw Wilson formula broke the interval invariant by up to 2.2e-16 for some inputs (for example 6 of 6). A property test found it. | A numeric formula that breaks its own invariant by rounding | `willitharness.intervals.wilson` clamps the bounds to the rate | `tests/unit/test_intervals_unit.py::test_V5_all_successes_at_six_runs_keeps_the_upper_bound_at_the_rate` |
| The overwatch pytest watcher writes `.testmondata` files that git did not ignore. The tree stayed dirty, so TCR could not judge any edit. Found in the first TCR trial. | A file written by a check that git does not ignore | `.gitignore` lists `.testmondata*`, checked by `scripts/gates/repo_checks.py` | `tests/gates/test_repo_checks.py::test_a_gitignore_without_the_watcher_files_is_reported` |
| The verdict boundary `low > 0` could change to `low >= 0` and no test failed, because a float interval almost never lands on exactly zero. The first run of the mutation gate found it. | A boundary no test could reach | `verdict_from_interval` is a separate function, and `scripts/gates/mutants.py stats` runs in the pre-push hook and in CI | `tests/unit/test_verdict_unit.py::test_V1_an_interval_that_starts_at_zero_is_inconclusive` |
| A contract ID could lose its feature, test or formal item with no one noticing. The first run of the gate found DI-1 and DI-2 in Lean under other names, and five IDs with no tests yet. | An ID with no trace | `scripts/gates/trace_check.py` reads the contract table, and `scripts/gates/trace_pending.json` records the known gaps and fails when one is fixed without removing its entry | `tests/gates/test_trace_check.py::test_an_id_removed_from_the_features_fails_the_gate` |
| A plan whose noise repeat copied the rule arm instead of the LOO arm would spend money on a noise floor that measures nothing. | A plan that cannot answer its own question | `willitharness plan check` rejects it before any run, through `willitharness.plan.load_plan` | `tests/gates/test_plan_gate.py::test_G1_8_the_bad_noise_pair_plan_exits_one_with_the_named_arms` |
| The plan's conformance commands pass a table file, but the code took a folder and crashed on the plan's own command. A bad table value also crashed instead of naming the case. Found when M2 started. | A gate command that was never run as the plan writes it | `willitharness.conformance` takes a table file or a folder, and reports an unknown value as a mismatch | `tests/gates/test_conformance_gate.py::test_a_table_file_path_conforms_and_prints_the_case_count` |
| A test planted files under the name taken from the constant it tests, so renaming the constant moved code and test together and nothing failed. The mutation gate found it. | A test that restates the code under test | `scripts/gates/mutants.py` plants the rename, and the tests now use the literal file names | `tests/gates/test_fakeagent.py::test_a_claude_file_in_the_same_directory_is_read` |
| `MIN_PROBE_RUNS` was defined in two modules, so the plan and the probe could disagree. Found while building the probe. | A constant with two sources | `probe.py` imports `MIN_PROBE_RUNS` from `plan.py` | `tests/unit/test_probe_unit.py::test_requesting_the_minimum_runs_is_accepted` |
| The plan wrote its BDD gates for `behave`, but the project runs `pytest-bdd`, so the gate commands could not run. Found when the first BDD gate was built. | A gate command for a tool the project does not use | the plan files use the pytest commands, and `scripts/gates/repo_checks.py` rejects the old form | `tests/gates/test_repo_checks.py::test_the_retired_behave_command_in_a_plan_file_is_reported` |
| The traceability scanner read raw text, so a test name inside a string counted as coverage for a contract ID. Found when a gate test held such a string. | A scanner that trusts text instead of structure | `scripts/gates/trace_check.py` parses test files with `ast` | `tests/gates/test_trace_check.py::test_a_test_name_inside_a_string_does_not_cover_an_id` |
| Five zanity rules were disabled in `zanity.toml` to get a green run, which hid what they found. The user's rule is never to disable one. | A rule switched off instead of fixed | `scripts/gates/repo_checks.py` fails on any disabled rule; checks on repository files moved out of tests into that gate; plan paths resolve under a root | `tests/gates/test_repo_checks.py::test_a_path_disable_in_the_zanity_config_is_reported` |

## Mistakes with no rule yet

These came from the spike. Each has a planned task in `docs/plan/07-task-backlog.md`.

| Mistake | Planned rule | Task |
|---|---|---|
| A rule file silently did not load (`AGENTS.md` hidden by an ancestor `CLAUDE.md`). | Reachability probe with a control token | T16, T19 |
| A guard blocked a command but its message gave no usable alternative, so tasks stopped. | Block-message actionability check | T39, T44 |
| A stub world invalidated runs (a stub listed processes outside the checkout). | World validation W1 to W3 | T23, T24 |
| The analyzer crashed on a stream event whose `message` was a string. | Stream parser with a corpus of odd events | T21 |
| A parallel run overspent its cap. | Budget reservation L2 | T27, T28 |
