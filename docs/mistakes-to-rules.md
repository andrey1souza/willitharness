# Mistakes and the rules that catch them

Each mistake below happened, or nearly happened, in this project. The fix is a
check that rules out the whole category, never a line of prose. A test shows that
the check can fail. `tests/repo/test_mistakes_table.py` fails when a row names a
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
| The overwatch pytest watcher writes `.testmondata` files that git did not ignore. The tree stayed dirty, so TCR could not judge any edit. Found in the first TCR trial. | A file written by a check that git does not ignore | `.gitignore` lists `.testmondata*` | `tests/repo/test_gitignore.py::test_files_written_by_the_overwatch_python_watcher_are_ignored` |

## Mistakes with no rule yet

These came from the spike. Each has a planned task in `docs/plan/07-task-backlog.md`.

| Mistake | Planned rule | Task |
|---|---|---|
| A rule file silently did not load (`AGENTS.md` hidden by an ancestor `CLAUDE.md`). | Reachability probe with a control token | T16, T19 |
| A guard blocked a command but its message gave no usable alternative, so tasks stopped. | Block-message actionability check | T39, T44 |
| A stub world invalidated runs (a stub listed processes outside the checkout). | World validation W1 to W3 | T23, T24 |
| The analyzer crashed on a stream event whose `message` was a string. | Stream parser with a corpus of odd events | T21 |
| A parallel run overspent its cap. | Budget reservation L2 | T27, T28 |
