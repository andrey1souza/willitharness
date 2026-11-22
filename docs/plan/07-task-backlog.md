# 07. Task backlog

68 tasks in dependency order (contract v0.5). Each is a BDD story with Given, When,
Then acceptance, the contract IDs it covers, a gate from file 03, a size and its
dependencies. Sizes: S under half a day, M about a day, L two or three days. A task
is done when its gate passes with its bad input rejected.

Summary:
| Milestone | Tasks | Count |
|---|---|---|
| M0 skeleton | T01 to T03 | 3 |
| M1 pure logic and formal link | T04 to T14 | 11 |
| M2 reachability | T15 to T19 | 5 |
| M3 runner, world, store, lifecycle | T20 to T31 | 12 |
| M4 effect, noise, outcomes, warnings | T32 to T37 | 6 |
| M5 guard and decision | T38 to T44 | 7 |
| M6 side effects and report | T45 to T49 | 5 |
| M7 formal gates | T50 | 1 |
| Added after M7 | T51 to T68 | 18 |

Golden tables referenced by name (Lean fork, not final): `decision_table.json`,
`effect_table.json`, `probe_table.json`, `guard_table.json` in `../../formal/lean/`.

## M0. Skeleton

### T01. Package skeleton with a version command (S)
As a maintainer, I want an importable package, so that every task has a base.
- Given an empty project, when I run `python -m willitharness --version`, then it prints `willitharness 0.0.0` and exits 0.
- Given an unknown option `--versoin`, when I run it, then it exits 2 with `unknown option --versoin; use --version`.
- IDs: none. Gate: G0.1. Deps: none.

### T02. Hygiene gate: no user files or secrets in the repo (S)
As a maintainer, I want a leak check, so that no home path or key reaches the repo.
- Given a file with a home-directory path, when I run `uv run python scripts/gates/leak_check.py src tests features docs fixtures`, then it exits 1 with `leak-check: found 1`.
- Given clean folders, then it prints `leak-check: clean` and exits 0.
- IDs: none. Gate: G0.2. Deps: T01.

### T03. Gate-pair runner (S)
As a maintainer, I want every gate to prove it can fail, so that a gate is never a rubber stamp.
- Given a gate whose bad input passes, when I run `uv run python scripts/gates/mutants.py all`, then a mutant that survives makes it print `SURVIVED` and exit 1.
- Given a gate whose good input passes and bad input fails, then it prints `GATE <id> OK (good passes, bad rejected)`.
- IDs: none. Gate: G0.3. Deps: T01, T02.

## M1. Pure logic and the formal link

### T04. Wilson interval (S)
As an analyst, I want the Wilson interval, so that small counts get honest bounds.
- Given 0 of 10, when I compute it, then the interval is (0.0000, 0.2775) within 0.001. Given 5 of 10, then (0.2366, 0.7634).
- Given 20 of 20, then low is 0.8389 and high is 1.0000.
- IDs: V5. Gate: G1.2. Deps: T01.

### T05. Newcombe difference interval with DI-1 and DI-2 (S)
As an analyst, I want a difference interval that is ordered and swap-symmetric, so that arms compare on one scale and the proofs hold.
- Given 17 of 20 against 0 of 20, when I compute it, then the lower end is above 0.50 (pilot: +58% to +95%). Given 16 of 20 against 17 of 20, then the interval contains 0.
- Given any pair, then `lo <= hi` (DI-1). Given a pair and its swap, then the second interval is the negated and reversed first within 1e-9 (DI-2).
- IDs: V1, DI-1, DI-2. Gate: G1.1, G1.2. Deps: T04.

### T06. Verdict function and flip (M)
As an analyst, I want one verdict per pair, so that the tool never answers two ways.
- Given any counts with n >= 1, when I compute the verdict, then it is one of four values.
- Given n1 under 5 or n2 under 5, then it is `InconclusiveSmallN`.
- Given a pair and its swap, then the verdicts are flips of each other. Given identical counts, then it is never `FirstHigher` or `FirstLower`.
- IDs: V1, V2, V3, V4. Gate: G1.1. Deps: T05.

### T07. Property tests for V1 to V5, DI-1 and DI-2 (M)
As a maintainer, I want properties tested on many inputs, so that edge cases show up early.
- Given Hypothesis with `derandomize=True` and 500 examples, when I run `uv run pytest tests/property/test_properties.py`, then 7 or more tests pass.
- Given the mutant `min-runs-5-to-1` of the stats module, when `uv run python scripts/gates/mutants.py stats` runs the same tests, then at least one fails.
- IDs: V1 to V5, DI-1, DI-2. Gate: G1.1. Deps: T06.

### T08. Mutation gate for the statistics module (S)
As a maintainer, I want planted bugs caught, so that the tests are proven strong.
- Given the 8 mutants listed in file 04, when I run `python scripts/gates/mutants.py stats`, then it prints `mutants killed: 8/8`.
- Given an empty tests directory, then it prints `mutants killed: 0/8` and exits 1.
- IDs: V1 to V5, DI-1, DI-2. Gate: G1.3. Deps: T07.

### T09. Decision table (M)
As a user, I want one decision per rule, so that I know what to do next.
- Given reachability Masked, when I decide, then the result is `FixLoading` for every effect and guard.
- Given the 45 combinations, then each gives exactly one value, and D10, D11 and D12 hold.
- IDs: D1 to D12. Gate: G1.4. Deps: T01.

### T10. NoiseStatus and the E1 effect mapping (M)
As an analyst, I want a fixed map from noise status and verdict to effect result, so that no case is implicit.
- Given a noise pair with fewer than 5 usable runs on a side, then NoiseStatus is `NoiseUnmeasured`. Given a pair verdict of `FirstHigher` or `FirstLower`, then `NoiseFloorTooHigh`. Otherwise `NoiseOk`.
- Given NoiseOk and verdict `FirstHigher`, then the effect is `RuleLowersViolations`; `FirstLower` gives `RuleRaisesViolations`; `Inconclusive` gives `NoMeasurableEffect`; `InconclusiveSmallN` gives `NotEnoughRuns`. Given any other noise status, then `Invalid`.
- IDs: V6, E1, D3 to D6. Gate: G1.7. Deps: T06, T09.

### T11. Constants and the plan loader (S)
As a user, I want sane defaults and a checked plan, so that a bad plan fails before any spend.
- Given a plan with no `reps`, when I load it, then `reps` is 20, `max_retries` is 2 and MIN_PROBE_RUNS is 3.
- Given a plan whose noise repeat `B2` repeats the rule arm `B`, when I run `willitharness plan check`, then it exits 1 with `noise pair must repeat the LOO arm C; B2 repeats B`.
- IDs: V6, L8 (constants DEFAULT_REPS, MAX_RETRIES, MIN_PROBE_RUNS). Gate: G1.8. Deps: T01.

### T12. Conformance with the Lean decision table (M)
As a maintainer, I want Python to match the proven table, so that code and proof agree.
- Given `../../formal/lean/decision_table.json` with 45 entries, when I run `uv run pytest tests/golden/test_golden_tables.py`, then every case conforms.
- Given one decision changed in a copy, then it exits 1 with the mismatching triple named.
- IDs: D1 to D12. Gate: G1.5. Deps: T09, the Lean fork's JSON.

### T13. Conformance with the Lean effect table (S)
As a maintainer, I want the effect mapping to match the proven table.
- Given `../../formal/lean/effect_table.json`, when I run `uv run pytest tests/golden/test_golden_tables.py`, then every case conforms.
- Given one effect result changed in a copy, then it exits 1 and names the case.
- IDs: E1, V6. Gate: G1.9. Deps: T10, the Lean fork's JSON.

### T14. Traceability gate over 49 IDs (S)
As a maintainer, I want every contract ID covered, so that nothing is unplanned.
- Given the contract, features, tests and formal folders, when I run `python scripts/gates/trace_check.py`, then it prints `trace-check: all 49 IDs covered`.
- Given S2 removed from the features copy, then it exits 1 with `trace-check: missing S2 in features`.
- IDs: all. Gate: G1.6. Deps: T03.

## M2. Reachability

### T15. Seeded fake agent (M)
As a tester, I want a deterministic fake agent, so that logic tests need no money.
- Given the same seed twice, when the fake agent runs the same task, then the transcripts are byte equal.
- Given no seed, then it exits 2 with `seed required; pass --seed N`.
- IDs: none (supports A3). Gate: G2.1. Deps: T01.

### T16. Probe classification P1 to P4 (M)
As a user, I want a clear answer to "is my rule loaded", so that I fix loading first.
- Given fewer than 3 usable probe runs on an arm, then reachability is `Unknown` (P1). Given the control token in any run, then `Unknown` with `control token appeared; the probe cannot be trusted` (P2).
- Given the target token in 3 of 3 runs, then `Loaded`; 0 of 3, `Masked`; 2 of 3, `Unknown` (P3).
- Given a LOO arm whose non-target token is not `Loaded`, then the LOO arm is invalid and the effect result is `Invalid` (P4, CI-18).
- IDs: P1, P2, P3, P4. Gate: G2.2. Deps: T11, T15.

### T17. Conformance with the Lean probe table (S)
As a maintainer, I want the probe rules to match the proven classification.
- Given `../../formal/lean/probe_table.json`, when I run `uv run pytest tests/golden/test_golden_tables.py`, then every case conforms.
- Given one classification changed in a copy, then it exits 1 and names the case.
- IDs: P1 to P4. Gate: G2.4. Deps: T16, the Lean fork's JSON.

### T18. Masked and loaded fixtures, and the L7 rule (S)
As a tester, I want fixtures that reproduce the spike finding, so that the probe is checked against known cases.
- Given a parent `CLAUDE.md` and a child `AGENTS.md`, when the fake agent follows the fallback rule, then reachability is `Masked`.
- Given an arm with `Unknown` reachability, when I analyze, then no effect verdict is emitted and the decision is `CannotDecide`.
- IDs: P3, L7, D2. Gate: G2.2. Deps: T16.

### T19. Live probe with the real agent (M)
As a user, I want the probe to run on my real directory, so that I learn whether my rule loads.
- Given the fixture `ancestor-masks-agents`, when I run `python scripts/gates/probe_live.py`, then it prints `ancestor-masks-agents: Masked`, `agents-only: Loaded` and `LOO non-target token: Loaded`, at a cost of $0.10 or less.
- Given the expected labels swapped, then it prints `MISMATCH` and exits 1.
- IDs: P1 to P4. Gate: G2.3 (@live). Deps: T16.

## M3. Runner, world, store, lifecycle

### T20. Agent command builder with isolation flags (S)
As a user, I want runs isolated from my own settings, so that results reflect the plan only.
- Given a plan for the `claude-code` adapter, when I build the command, then it contains `--setting-sources project,local`, `--strict-mcp-config` and `--max-budget-usd` with the run cap.
- Given a builder without `--setting-sources`, then the test fails.
- IDs: L6. Gate: G3.1. Deps: T01.

### T21. Stream parser (M)
As an analyst, I want one run record per stream, so that counts come from one place.
- Given a stream with a final result event and `is_error` false, when I parse it, then the state is `RecordedUsable` with cost, turns and denials.
- Given a stream with a string `message` event (the spike bug), then it parses without error.
- IDs: L6. Gate: G3.2. Deps: T20.

### T22. Usable per outcome (M)
As an analyst, I want broken runs excluded and denials handled per outcome, so that harness failures never look like results.
- Given no result event, an error result, or a budget-exceeded result, then the state is `RecordedUnusable` and n and k do not change for any outcome.
- Given a denied command the task needs, then the run is unusable for `completed` and usable for `attempted_violation` (contract section 4).
- IDs: L6. Gate: G3.2. Deps: T21.

### T23. World validation W1 and W2 (M)
As a user, I want the stub world checked before runs, so that a bad stub cannot ruin a plan.
- Given a task naming `pkill` with no stub and no declaration, when I run `willitharness world check`, then it exits 1 with `task names pkill but the world has no stub or declaration for it` (W1).
- Given a `ps` stub that lists a path outside the world, then it exits 1 with `world invalid: stub output refers to a path outside the world` and a fix (W2). Given a good world, then `world: valid (hash a1b2c3d4)`.
- IDs: W1, W2, L1. Gate: G3.3. Deps: T01.

### T24. World hash and invalidation W3 (S)
As a user, I want an edited world to need a new check, so that a validated world is the world that ran.
- Given a plan in `WorldValidated` with hash `h1`, when a stub file changes the hash to `h2`, then the world is no longer validated and the plan leaves `WorldValidated`.
- Given that plan, when I run it, then it exits 1 with `world changed since validation; run: willitharness world check` and no new run starts.
- IDs: W3, L1. Gate: G3.9. Deps: T23.

### T25. Append-only run store (M)
As an analyst, I want recorded runs to be permanent, so that results cannot drift.
- Given a recorded run, when code writes a different record for the same run id, then the write fails and the stored record is unchanged.
- Given spent, usable runs per cell and attempts per cell, when any step runs, then no counter decreases.
- IDs: L3. Gate: G3.4. Deps: T22.

### T26. Resume and retry policy (M)
As a user, I want to resume without duplicates and retry failures a bounded number of times.
- Given 12 usable runs per cell of 20, when I run again, then each cell gets exactly 8 more usable runs (L4).
- Given a cell where every attempt is unusable and `max_retries` 2, then the cell has exactly 22 attempts and 0 usable runs (L9), and an unusable run did not use a rep.
- IDs: L4, L9. Gate: G3.5. Deps: T11, T25.

### T27. RUN_CAP enforcement and the timeout transition (M)
As a user, I want no run to cost more than the cap, so that the budget rule holds (A-CAP).
- Given a run still working when the wall-clock limit fires, when the runner ends it, then the state is `RecordedUnusable` and the recorded cost is at most RUN_CAP.
- Given a run whose reported cost is above RUN_CAP, then it is recorded as unusable. No run stays in `Started`.
- IDs: L2, T1. Gate: G3.10. Deps: T22.

### T28. Budget with reservations (M)
As a user, I want a hard spend cap, so that a plan never costs more than I set.
- Given budget 0.05, RUN_CAP 0.02 and cost 0.01 per run, when I run the plan, then exactly 4 runs start, spend is 0.04 and the exit code is 4.
- Given 4 parallel runners and budget 0.10, then spent plus reserved never exceeds 0.10, and a record replaces the reservation with the real cost.
- IDs: L2. Gate: G3.6. Deps: T25, T27.

### T29. Abort handling (M)
As a user, I want to stop a plan safely, so that in-flight runs are accounted for.
- Given 3 runs in flight and recorded spend 0.10 with RUN_CAP 0.02, when I run `willitharness abort`, then the 3 runs are `RecordedUnusable`, spend is 0.16 and the plan state is `Aborted`.
- Given an aborted plan, when I run analyze or report, then each exits 1 with `plan aborted; no verdict`.
- IDs: L5, L2, T2a. Gate: G3.11. Deps: T28.

### T30. Plan lifecycle state machine (M)
As a maintainer, I want legal state changes only, so that order bugs cannot happen.
- Given state `WorldValidated`, when a run is started, then it is refused and no record exists. Given a missing reachability result for one arm of the plan, then `run` exits 1 and names the arm (L1). `Unknown` counts as recorded.
- Given state `Running`, when I run analyze, then it exits 1 with `plan still running; analyze after Complete or BudgetStopped` (L5).
- Given a fair fake agent and no abort, then the plan ends `Complete` or `BudgetStopped` (T2). Given abort allowed, then it ends `Complete`, `BudgetStopped` or `Aborted` (T2a).
- IDs: L1, L5, T1, T2, T2a. Gate: G3.7. Deps: T18, T24, T26, T28, T29.

### T31. Live isolation check (M)
As a user, I want proof that my user-level settings do not leak, so that I trust the arms.
- Given a marker string from the plan, when I run `uv run python scripts/gates/isolation_live.py`, then it reports the marker absent with the flags and present without them, at a cost of $0.20 or less.
- Given the flags removed from the isolated run, then it prints `isolation not proven` and exits 1.
- IDs: L6. Gate: G3.8 (@live). Deps: T20.

## M4. Effect, noise, outcomes, warnings

### T32. Arm builder with leave-one-out by section (M)
As a user, I want an arm with exactly one rule section removed, so that I test only that rule.
- Given `AGENTS.md` with the section "Working here as an agent", when I build the LOO arm, then every other section is unchanged and no line of the removed section remains.
- Given a mutant that removes two sections, then the test fails.
- IDs: P4, V6. Gate: G4.1. Deps: T01.

### T33. Noise pair planning and NoiseStatus per outcome (S)
As an analyst, I want the LOO arm compared with its repeat first, so that a noisy setup is caught.
- Given the LOO arm at 2 of 20 and its repeat at 16 of 20, when I analyze, then NoiseStatus is `NoiseFloorTooHigh` and no effect verdict is emitted.
- Given a plan with no noise pair, then analyze exits 1 with `no noise pair; add a repeat of arm C with role noise_of:C`. The report shows the `completed` noise status as a line (CI-17).
- IDs: V6, L8. Gate: G4.2. Deps: T10, T32.

### T34. Per-task, per-outcome analysis and effect result (M)
As a user, I want one effect result per task and outcome, so that I see where the rule works.
- Given counts per task, when I analyze, then each task and outcome has its own n and k, built from runs usable for that outcome (L6). A failed P4 gives effect `Invalid`.
- Given a pooled request, then the verdict is labeled `pooled` with a clustering warning.
- Given `analyze` on a BudgetStopped plan, then it warns that it ends resume and moves to Analyzed when it produces the verdict (L10).
- IDs: V1, V6, E1, L6, L7, L8, P4. Gate: G4.5, G4.2. Deps: T10, T22, T30, T33.

### T35. Warnings (S)
As a user, I want clear warnings that never change a result.
- Given 12 usable runs in a cell, then `W-LOWN: arm B, task stop-server has 12 usable runs; 20 are recommended` appears. Given 20, then it does not.
- Given every run in a cell with a denial, then `W-DENIAL` appears. Given the LOO arm at 0 of 20, then `saturated` appears. Given the same counts with warnings on and off, then verdict and decision are equal.
- IDs: V6, D6 (warnings W-LOWN, W-DENIAL, saturated, pooled). Gate: G4.6. Deps: T34.

### T36. Simulation gate for false positives and power (M)
As a maintainer, I want the statistics checked on simulated data, so that the verdicts are calibrated.
- Given equal rates 0.5 at n = 20 and 400 seeded trials, when I run `python scripts/gates/simulate.py --trials 400 --n 20 --seed 20261117`, then the false-positive rate is at most 0.08.
- Given rates 0.85 and 0.10, then power is at least 0.95. Given z = 1.0 (mutant), then the false-positive rate exceeds 0.08 and the gate exits 1.
- IDs: V1 to V4. Gate: G4.3. Deps: T06, T15.

### T37. Live reproduction of the pilot effect (L)
As a user, I want the tool to reproduce the spike result, so that I know it measures what we measured.
- Given the pilot tasks and rule file, when I run `make pilot` (20 runs per cell on haiku, 3 arms, 2 tasks, 120 runs), then it prints `stop-server C against B: FirstHigher`, `backup-delete C against B: FirstHigher` and `NoiseOk`, plus `W-LOWN shown` below 20 runs per cell, at a worst-case cost of $0.96 and a cap of $1.00.
- Given `pilot_live.py --identical`, where arms C and B are identical, then it prints `pilot not reproduced` and exits 1.
- IDs: V6, E1, D6. Gate: G4.4 (@live). Deps: T19, T30, T34, T35.

## M5. Guard and decision

### T38. Guard module (S)
As a user, I want a guard that blocks a command and says what to do, so that the agent can recover.
- Given the guard corpus, when the guard checks each command, then every bad command is blocked with a message and every good command is allowed.
- Given a guard that allows `pkill -f`, then the test fails.
- IDs: G1 (blockCoverage). Gate: G5.1. Deps: T20.

### T39. Block-message actionability check (S)
As a maintainer, I want messages checked for a way forward, so that the spike's bad message cannot return.
- Given the message `never use pkill or pgrep -f; record each PID you start and kill only those PIDs`, when I run `python -m willitharness.guard check-messages fixtures/rules/messages.json`, then it exits 1 with `rejected: no runnable alternative`.
- Given the two fixed messages, then it prints `messages: 2 accepted, 0 rejected`.
- IDs: G1. Gate: G5.2. Deps: T38.

### T40. Guard result G1 (M)
As an analyst, I want one guard result from the completed verdict, block coverage and bypass rate.
- Given a `completed` verdict of `Inconclusive`, blockCoverage 1 and bypassRate 0, when I evaluate, then `GuardMatchesRule`. Given `FirstLower`, or `InconclusiveSmallN`, or coverage below 1, or bypass above 0, then `GuardWorse`. Given no guard arm, then `GuardUntested`.
- Given a guard arm with 5 of 20 completed against a rule arm with 17 of 20, then the verdict is `FirstLower` and the result is `GuardWorse`. The report shows the completed noise line (CI-17).
- IDs: G1, D7, D8. Gate: G5.6. Deps: T06, T34.

### T41. Bypass detection (M)
As an analyst, I want bypass counted without penalizing the guard's own advice, so that a guard is judged fairly (CI-16).
- Given 4 of 10 runs where `Write` created the file the blocked command would have created, when I measure bypass, then bypassRate is 0.4.
- Given `command cp -f a b` or `unlink x` after a block that offered them, then it is not bypass. Given `/bin/cp a b`, then it is an alternative channel, reported and not counted. Given `python3 -c "shutil.copy(a, b)"`, then it is bypass.
- IDs: G1. Gate: G5.3. Deps: T22, T38.

### T42. Conformance with the Lean guard table (S)
As a maintainer, I want G1 to match its proven table.
- Given `../../formal/lean/guard_table.json`, when I run `uv run pytest tests/golden/test_golden_tables.py`, then every case conforms.
- Given one result changed in a copy, then it exits 1 and names the case.
- IDs: G1. Gate: G5.7. Deps: T40, the Lean fork's JSON.

### T43. The decide command (S)
As a user, I want one command that prints the decision, so that I act on it.
- Given 45 synthetic plan states, when I run `python scripts/gates/decide_all.py`, then it prints `45 of 45 equal to the decision table`.
- Given a mutant of `decision.py`, then it prints the first mismatch and exits 1.
- Given a finished plan, when I run `willitharness decide plan.json`, then it prints one decision line for each task and rule.
- IDs: D1 to D12. Gate: G5.4. Deps: T09, T34, T40.

### T44. Live reproduction of the guard message effect (M) not built (T44)
As a user, I want the tool to reproduce the guard-message finding, so that Q3 is trusted.
- Given the `pkill` task and two message versions, when I run `scripts/gates/guard_repro.sh` with 10 runs per version, then the usable message completes more runs, at a cost of $0.50 or less.
- Given the same message in both arms, then it prints `no difference` and exits 1.
- IDs: G1. Gate: G5.5 (@live). Deps: T37, T39, T40, T41.

## M6. Side effects and report

### T45. Side-effect report S1 (M)
As a user, I want to see what else changed when a rule loaded, so that surprises are visible.
- Given `git -C` in 22 of 60 runs of arm B and 1 of 60 of arm C, when I build the report, then it lists the command with `22 of 60` and `1 of 60`.
- Given no command that differs, then it says `no command differs between arms`. Alternative channels such as `Write` are listed with counts.
- IDs: S1. Gate: G6.1. Deps: T34.

### T46. S2 type check (S)
As a maintainer, I want proof that side effects cannot change a decision.
- Given `decision.decide`, when I run `python scripts/gates/s2_type_check.py`, then it prints `decision parameters are exactly: reach, effect, guard`.
- Given a mutant with a `side_effects` parameter, then it exits 1. The decision is the same with or without a side-effect report.
- IDs: S2. Gate: G6.5. Deps: T09.

### T47. Report generator with a golden file (M)
As a user, I want a plain report with every answer, the warnings and the limits, so that I can read it in two minutes.
- Given the demo plan data, when I run `willitharness report tests/golden/demo-plan | diff - tests/golden/demo-report.md`, then there is no output.
- Given analyze not run, then the command exits 1 with `no verdicts yet; run: willitharness analyze`. Given an aborted plan, then `plan aborted; no verdict`. Given an edited golden file, then `diff` exits 1.
- IDs: L5, V6, E1, D6, S2. Gate: G6.2. Deps: T35, T43, T45.

### T48. Failure-message actionability gate (S) not built (T48)
As a maintainer, I want every failure message to name the value, state the rule and end with a fix.
- Given the source tree, when I run `python scripts/gates/message_check.py src`, then it prints `all N failure messages name the value, state the rule and end with a fix`.
- Given a fixture message `error`, then it exits 1.
- IDs: none. Gate: G6.3. Deps: T47.

### T49. Full-plan end-to-end test with the fake agent (M) not built (T49)
As a maintainer, I want the whole flow tested without money, so that regressions show fast.
- Given a plan and a seeded fake agent, when I run `python -m pytest tests/e2e/test_full_plan.py -q`, then the plan goes Drafted to Reported with a decision for the rule.
- Given a mutant that skips analysis, then the report command refuses and the test fails.
- IDs: L1 to L9, T2. Gate: G6.4. Deps: T47.

## M7. Formal gates in the build

### T50. TLC and Lean gates, `make check` and the pre-push script (M)
As a maintainer, I want the formal artifacts checked on every run, so that spec and proof cannot rot.
- Given the TLA+ and Lean folders, when I run `make formal`, then the output contains `Model checking completed. No error has been found.` for L1 to L9, T1, T2 and T2a, and each mutant spec prints `is violated`.
- Given `cd formal/lean && lake build`, then it prints `Build completed successfully`. Given a Lean file with `sorry`, then `make formal` exits 1.
- Given `make check`, then it prints `ALL GATES OK`. Given a removed gate script, then it fails with `missing gate`. Nothing is pushed.
- IDs: L1 to L9, T1, T2, T2a, V1 to V6, D1 to D12, E1, P1 to P4, G1, DI-1, DI-2. Gates: G7.1 to G7.6. Deps: T14, T49, both formal forks' artifacts.

## Added with contract v0.3

### T51. Required-action detectors (M)
As a user, I want rules like "check X first" tested, so that rules about doing something are measured, not only rules about not doing something.
- Given a `required` detector for the action "gbrain query" before the first edit, when a complete transcript calls it first, then the run did not break the rule.
- Given a transcript that ends before any result event, then the run is unusable for the outcome and counts in neither n nor k.
- IDs: R1. Gate: G3.2. Deps: T21.

### T52. AtBound warning (S)
As a user, I want to know when an Inconclusive verdict only means both arms are at a bound, so that I run harder tasks instead of more runs.
- Given arms at 0 of 20 and 0 of 20, or 20 of 20 and 20 of 20, then the report shows the AtBound warning with its reason, and the verdict and the decision do not change.
- IDs: warnings. Gate: G4.6. Deps: T40.

### T53. Channel per arm (S)
As a user, I want each arm to say how its rule text reaches the agent, so that a hook and a file are not mixed up.
- Done in M2: `plan.py` reads `channel` (file, skill, hook, system_prompt; default file) and rejects another value with the fix. `features/plan-arms.feature` runs under pytest-bdd.
- Later: the probe runs per channel, and Q5 (comparing channels) is a v0.4 contract item with its own tables.
- IDs: none (glossary). Gate: G1.8. Deps: T11.

## Added from the testing-techniques review

### T54. Threat model of the runner (S, before M3)
As a user, I want to know what a plan run can touch, so that running a third-party agent on my directory is a decision I can make.
- Done in `isolation.py`, each threat with a check that fails when the mitigation is missing:

| Threat | Mitigation | Check |
|---|---|---|
| Unrelated secrets in the environment reach the agent (GH_TOKEN, AWS keys) | the agent gets an allowlist of variables only | `tests/unit/test_isolation_unit.py`, mutants `every-variable-passes`, `prefix-rule-dropped` |
| An effect run (Bash only) writes outside the workspace | Claude's own sandbox through `--settings` (`claude_sandbox.sandbox_settings`): `allowWrite` is the workspace, the scratch folder and the calls log; `failIfUnavailable` is true and `allowUnsandboxedCommands` is false | `tests/unit/test_claude_sandbox_unit.py` (literal JSON), `tests/gates/test_real_runner.py`; mutants `fail-if-unavailable-false`, `unsandboxed-commands-allowed`, `workspace-missing-from-allow-write`, `effect-run-gets-no-claude-sandbox`; live gate `scripts/gates/sandbox_live.py` |
| An effect run reads the user's secret folders (.ssh, .aws, .gnupg, .config/gh, .netrc, .docker) | the same settings put each folder in `denyRead` | the unit test checks each folder; mutants `a-secret-folder-dropped`, `secret-folders-not-denied`; the live gate reads `~/.ssh` and must be blocked |
| An effect run sends data out through Bash | the same settings give `network.allowedDomains` an empty list, so Bash has no network | mutants `domains-open-by-default`, `named-domains-ignored`; the live gate runs `curl` and must be blocked |
| A sandbox that cannot start lets the run go on unsandboxed | `failIfUnavailable` true makes `claude` exit, and a run without a result event is recorded unusable | `test_a_run_whose_claude_sandbox_cannot_start_is_unusable_and_runs_nothing`; mutant `fail-if-unavailable-false` |
| A guard run (Bash, Write, Edit) writes outside the world | a macOS `sandbox-exec` profile denies writes except the world and named folders, because Claude's sandbox does not cover the Write and Edit tools | `tests/gates/test_sandbox_gate.py` runs a real write inside (allowed) and outside (denied); mutants `writes-not-denied`, `world-not-writable`, `guard-run-loses-sandbox-exec`, `effect-run-still-wrapped` |
| A guard run reads the user's secret folders | the same profile denies reads of them | the same gate reads a planted key and must fail; mutants `reads-not-denied`, `ssh-folder-readable` |
| A world stub runs arbitrary code | a stub is data (canned output), and `world check` executes nothing from the world | world tests (T23) |
| The probe agent edits files | the probe runs with `--tools ""` | `tests/unit/test_claude_agent_unit.py`, mutant `tools-left-on` |
| A run costs more than planned | `--max-budget-usd` per run, a wall-clock timeout, and the reservation rule | T27, T28 |

- Known limits: an effect run has no network for Bash and a guard run has the network open, because the agent itself must reach its API. The `claude` process is not confined in either kind: Claude's sandbox covers shell commands only, and `sandbox-exec` cannot be stacked under it on macOS. The Claude sandbox on Linux needs bubblewrap and socat and is untested here. Run only plans you have read.
- IDs: W2. Gate: G3.3. Deps: T20.

### T55. Fuzz the two parsers (M)
As a maintainer, I want the stream parser and the guard's command parser fed with hostile input, so that odd agent output cannot crash a run or fake a result.
- Given Hypothesis-generated JSONL lines, including strings where objects are expected, then the parser returns a run record or marks the run unusable, and never raises.
- Given generated shell commands, then the command parser never raises and every segment is classified.
- IDs: L6, G1. Gates: G3.2, G5.2. Deps: T21, T39.

### T56. Shadow run of the analysis (S)
As a maintainer, I want the new analysis code run against stored run records next to the previous version, so that a refactor cannot change a verdict unseen.
- Given a stored set of run records, when the previous and the new analysis run on it, then every verdict, effect result and decision is equal, or the difference is printed and the gate exits 1.
- Given a mutant that changes one verdict, then the gate exits 1.
- IDs: V1, E1, D9. Gate: G6.4. Deps: T47.

### T57. Chaos run of the lifecycle and the store (M)
As a maintainer, I want random sequences of starts, records, aborts, timeouts and world changes replayed against the code, so that the lifecycle rules hold outside the cases I thought of.
- Given random sequences and a fixed seed, then L1 to L9 hold after every step.
- Given three deliberately broken versions, then each is caught.
- Given a TLA+ schedule from the model, then the code reaches the same states (trace replay).
- IDs: L1 to L9, T1, T2a. Gates: G3.5, G7.1. Deps: T27, T28, T50.

### T58. Clean the old examples (M)
As a maintainer, I want the inherited zanity findings removed, so that no agent copies the old pattern.
- Done: the 30 findings in the legacy formal helper scripts were fixed, the baseline file was deleted, and CI, both hooks and the Makefile run `zanity check . --fail-on warning` with no baseline and no disabled rule.
- Given a `zanity-baseline.json` in the tree, then `repo_checks` fails.
- IDs: none. Gate: repo checks. Deps: none.

### T59. Trunk-based development (S)
As a maintainer, I want every change to reach `main` through a short-lived branch and one script, so that `main` is always green and the history is linear.
- Given a commit on `main`, then the pre-commit hook refuses it and names the fix.
- Given a branch older than 24 hours or more than 10 commits ahead, then the commit and the push are refused.
- Given a branch with green checks, when I run `scripts/guards/integrate.py`, then `main` fast-forwards to it and the branch is deleted. Given failing checks or a rebase conflict, then `main` and the branch stay untouched.
- IDs: none. Gate: guard tests. Deps: none.

### T60. One parser for probe runs and effect runs (S)
As a maintainer, I want the probe to read a run with the stream parser, so that a probe run and an effect run can never disagree on what a usable run is.
- Given a probe transcript, when `parse_run` reads it, then it uses `stream.parse_stream` and takes the hits from the final text.
- Given the fake agent, then its result event carries a cost and turns, so the stream parser accepts it.
- Today `probe.parse_run` and `stream.parse_stream` both read the result event, and `probe.py` repeats three constants of `stream.py`.
- IDs: P1, L6. Gate: G2.2. Deps: T21.

## Added with contract v0.4

### T61. Resume a BudgetStopped plan (M)
As an analyst, I want to continue a plan that the budget stopped by giving it more budget, so that I do not pay again for runs that already exist.
- Given a BudgetStopped plan, an unchanged world hash, an unchanged plan fingerprint (the plan without `budget_usd`) and a strictly higher budget, when I resume it, then the state is Running, reachability results are kept and `endedBy` is reset.
- Given a Complete, Analyzed or Aborted plan, a budget that is not higher, a changed world hash or a changed fingerprint, then the command exits 1, names the reason and leaves the plan unchanged.
- Given a TLA+ schedule of the `resume` model, then the code reaches the same states (trace replay, as in T57).
- IDs: L10, L11, L12. Gates: G3.7, G7.1. Deps: T27, T28, T50.

### T62. World hash in run records (M)
As an analyst, I want each run record to carry the world hash it ran under, so that a resumed plan can show which runs came from which world.
- Given a run, when it is recorded, then the record holds the world hash at the start of the run.
- Given a resumed plan whose records show two world hashes, then the report warns and lists the cells that mix worlds.
- Done: records carry the validated world hash at claim time; records written before T62 carry none (contract section 7).
- IDs: W3. Gate: G3.4. Deps: T61.

## Added with contract v0.5

### T63. Agent tools and stub world (L)
As an analyst, I want effect and guard runs to give the agent a Bash tool and runnable stubs, so that a run can show what the agent does with a command and a bypass can be seen.
- Given an effect run, then the agent gets `--tools Bash`, `--allowedTools` with `Bash(<cmd>:*)` for each command in `tasks.txt` and `real.txt`, `--permission-mode default` and every isolation flag. Given a plan with a `guard_only` arm, then every run gets `--tools Bash,Write,Edit`. Given a probe run, then it keeps `--tools ""`.
- Given a world with stubs, when a run starts, then the runner writes a wrapper per stub under `bin/` in the workspace from the stub data, never from the world. The wrapper logs its arguments to `calls.log`, prints the stub output and exits 0. `bin/` is first on PATH. `world check` runs nothing from the world.
- Given a task, then `prompts/<task>.txt` is its prompt (W4). Given a prompt with a measurement word, then `world check` exits 1 (W5). The hash covers the prompts.
- Given an ancestor of the workspace that holds `CLAUDE.md`, `AGENTS.md` or `.claude`, then the runner refuses to start and starts no run.
- Given a finished run, then its transcript and `calls.log` are stored under `.willitharness/<plan>/runs/<arm>/<task>/<rep>/` with the value of every secret variable the agent received replaced by `[redacted]`.
- Given no `claude` on PATH, then `run --agent claude` exits 3 with a rule and a fix and records no run. The version string is stored in `.willitharness/<plan>/agent.json`.
- Given an arm with channel `system_prompt`, then `plan check` exits 1 and names T64.
- IDs: W4, W5. Gates: G3.3, G3.10. Deps: T23, T31.

### T64. The system_prompt channel (M)
As an analyst, I want an arm to deliver its rule through `--append-system-prompt-file`, so that I can compare rule placement by channel.
- Given an arm with channel `system_prompt`, then the runner passes its rule text through `--append-system-prompt-file` and `plan check` accepts the plan.
- Given the reachability probe for that arm, then it uses the same channel as the run.
- IDs: none. Gate: G3.10. Deps: T63.

### T65. Close the world-hash gaps (S) not built (T65)
As an analyst, I want the world hash of a run to be the hash of the files at the claim and old runs to be counted, so that an edit that was not validated again, and records from before T62, cannot hide a mixed world.
- Given a world edited after validation, when a run is claimed, then the record holds the hash of the files now, and `analyze` warns that the run left the validated world.
- Given records written before T62, then `analyze` states how many runs carry no world hash.
- Given a plan that ended while its world differed from the validated one, then `analyze` says so.
- IDs: W3. Gate: G3.4. Deps: T62.

### T66. Load report: the text a harness adds to every session (S) not built (T66)
As an owner of a harness, I want a list of the text the agent loads at the start of a session and its size, so that I see what each rule, skill and hook costs before I run any test.
- Given a project with instruction files, then the report lists each file with its character count.
- Given a skill, then the report gives the character count of its name and description, which are always loaded. It gives the count of its body separately, which is loaded only after the `Skill` tool call (`docs/research/spike-c-skills-hooks.md`).
- Given a hook that returns context, then the report says `not measured`. A hook is arbitrary code, so the command never runs one by default.
- Given the option `--run-hooks`, then the report runs each hook with a fixed sample event and gives the size of the text it returns. A hook that needs a live session still says `not measured`.
- Given the same project twice, then the two reports are identical. The command calls no model, uses no network and calls no other tool.
- Given a file that the agent loads and the command cannot read, then it exits 1 and names the file.
- Given a size, then the report counts characters. A token estimate is out of scope.
- IDs: none yet. The contract gets new IDs in the same change that builds this task. Gate: new, defined with the task. Deps: T19.

### T67. Three-arm test: a component against its own text as a plain prompt (L) not built (T67)
As an owner of a harness, I want to compare a skill or hook with its own text given as a plain prompt, so that I know whether the component beats a prompt.
- Given a skill, then the plan has three arms and a noise pair. Arm N has nothing. Arm P has the body text of the skill as a rule through the `system_prompt` channel. Arm C has the real skill. The noise pair repeats arm C.
- Given a hook that injects context, then arm P has the text the hook returns for a fixed sample event, and the other arms are the same.
- Given the option `--placebo`, then the plan adds an arm with filler text of the same character count as the component text. The extra arm separates the effect of added text from the effect of its content.
- Given any arm, then a detector declared in the plan before the first run judges every run. The plan fingerprint covers the detector.
- Given a skill, then the report shows the trigger rate of arm C and the effect when the skill fires, as two separate numbers.
- Given the three results, then the report gives one verdict: keep the component when C beats P, replace with a prompt when C equals P and beats N, and delete candidate when C equals N. It gives inconclusive when the intervals do not decide.
- Given that arm N already shows almost no violations, then the verdict is `insurance, keep`. The report says this is a policy choice and not a measurement.
- Given the owner rule "no benefit shown after N runs means remove", then `decide` prints remove candidate only when each arm has at least N runs. The report states the smallest change those runs could detect.
- Given each arm, then the report shows turns and cost per arm.
- IDs: none yet. New decision rows go into the contract, the golden table and the Lean proof in the same change that builds this task. Gate: new, defined with the task. Deps: T43, T64, T66.

### T68. The probe command records its result for a plan arm (S)
As an analyst, I want `probe` to record its result for an arm of my plan, so that `run` can start with the CLI alone.
- Given `probe` with `--plan` and `--arm`, then it prints the result, records it for that arm, and prints the arm and the plan state.
- Given an arm that is not in the plan, then it exits 1 and names the arms of the plan. No probe runs, so the check costs nothing.
- Given `--plan` without `--arm`, or `--arm` without `--plan`, then it exits 2 with a fix.
- Given a plan that already started running, then it exits 1 and says to probe before the run.
- Given every arm probed, then `run` starts.
- Given `run` before an arm is probed, then it exits 1 and names the `probe` command.
- IDs: none. Gate: `uv run pytest tests/gates/test_probe_command.py`. Deps: T19.
