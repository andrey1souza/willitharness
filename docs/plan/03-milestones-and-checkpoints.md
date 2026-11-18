# 03. Milestones and checkpoints

Eight milestones in dependency order: M0 to M7. Every milestone has a goal, the
scenarios it turns green, executable gates, a cost cap and exit criteria.
Contract: v0.2 (43 IDs).

## How a gate works
- A gate is a command with an expected output.
- Every gate has a good input and a bad input. The runner
  `scripts/gates/run_gate.sh <gate>` runs both. It prints
  `GATE <id> OK (good passes, bad rejected)` only if the good input passes and the
  bad input fails. If the bad input passes it prints
  `GATE <id> BROKEN (bad input accepted)` and exits 1.
- Gates run offline unless marked `@live`. Live gates have a cost cap.
- Environment: `JAVA` defaults to `/opt/homebrew/opt/openjdk/bin/java`.
  `TLA2TOOLS_JAR` defaults to `~/.cache/tlalings/tla2tools.jar`. Lean comes from
  `elan` with `ELAN_HOME` set. Nothing is pushed.
- Golden tables from the Lean fork are referenced by name:
  `../formal/lean/decision_table.json`, `effect_table.json`, `probe_table.json`,
  `guard_table.json`. Their shape can change until the Lean fork marks them final.
  Conformance gates print the case count read from the file. The count is not
  hard-coded except for the decision table (3 x 5 x 3 = 45).

## Cost caps
| Milestone | Cap (USD) | Basis |
|---|---|---|
| M0, M1, M7 | 0.00 | No model runs |
| M2 | 0.10 | 2 fixtures x (3 rule-arm probe runs + 3 LOO-arm probe runs) = 12 runs at about $0.005 |
| M3 | 0.20 | One isolation check and a few smoke runs |
| M4 | 1.00 | 3 arms x 2 tasks x 10 reps = 60 runs at $0.003 to $0.006 (F7). Worst case with retries (12 attempts per cell) is 72 runs, about $0.43 |
| M5 | 0.50 | 2 guard arms x 10 reps = 20 runs. Worst case with retries is 24 runs, about $0.15 |
| M6 | 0.20 | Optional live smoke |
| Total | 2.00 | v0 definition of done (file 01) |
Caps are unchanged from the first plan. The v0.2 additions are offline logic. The
new default of 20 reps (DEFAULT_REPS) applies to users. The live gates set 10 reps
on purpose, so they show the W-LOWN warning. Sonnet costs about 14 times more per
run. Live gates use haiku.

## M0. Skeleton and gate runner
Goal: a package that imports, a hygiene gate, and the gate-pair runner.
Scenarios: none (infrastructure).

| Gate | Command | Expected output | Bad input (must be rejected) |
|---|---|---|---|
| G0.1 | `python -m willitharness --version` | `willitharness 0.0.0`, exit 0 | `python -m willitharness --versoin` exits 2 with `unknown option --versoin; use --version` |
| G0.2 | `scripts/gates/leak_check.sh src tests features docs fixtures` | `leak-check: clean`, exit 0 | `fixtures/bad/leak.txt` holds a home-directory path; the check exits 1 with `leak-check: found 1` |
| G0.3 | `scripts/gates/run_gate.sh G0.1` | `GATE G0.1 OK (good passes, bad rejected)` | a test gate whose bad input passes; the runner prints `BROKEN (bad input accepted)` and exits 1 |

Exit criteria: `make check` runs G0.1 to G0.3; the repo holds no user files or
session data.

## M1. Pure logic: verdict, effect, decision, constants, formal link
Goal: the pure functions, proven by tests and linked to the TLA+ and Lean artifacts.
Scenarios: `verdict-engine.feature`, `decision-table.feature`.

| Gate | Command | Expected output | Bad input |
|---|---|---|---|
| G1.1 | `python -m pytest tests/test_stats_properties.py -q` | `7 passed` or more (one property each for V1 to V5, DI-1, DI-2), 0 failed | the same tests run against `tests/mutants/stats_min_runs_1.py` fail |
| G1.2 | `python -m pytest tests/test_stats_known.py -q` | all pass; Wilson 0 of 10 is (0.0000, 0.2775), 5 of 10 is (0.2366, 0.7634); the pilot pairs give the pilot verdicts | a module with z = 1.64 fails |
| G1.3 | `python scripts/gates/mutants.py stats` | `mutants killed: 8/8` | with the tests directory emptied the script prints `mutants killed: 0/8` and exits 1 |
| G1.4 | `python -m pytest tests/test_decision.py -q` | all pass: 45 combinations, D1 to D12 | a table with D1 broken (Masked and RuleLowersViolations gives Keep) fails |
| G1.5 | `python -m willitharness.conformance decision ../formal/lean/decision_table.json` | `decision table conforms: 45 cases` | a JSON copy with one decision changed exits 1 with `mismatch for (Masked, Invalid, GuardWorse): lean=FixLoading python=Keep` |
| G1.6 | `python scripts/gates/trace_check.py ../00-domain-contract.md` | `trace-check: all 43 IDs covered` | a features copy with S2 removed exits 1 with `trace-check: missing S2 in features` |
| G1.7 | `python -m pytest tests/test_effect.py -q` | all pass: E1 over 3 noise statuses x 4 verdicts (12 cases); only NoiseOk gives an effect other than Invalid; NoiseStatus rules (V6) | a mutant that maps NoiseFloorTooHigh and FirstHigher to RuleLowersViolations fails |
| G1.8 | `python -m pytest tests/test_plan.py -q` and `willitharness plan check fixtures/plans/bad-noise-pair.json` | tests pass: DEFAULT_REPS 20, MAX_RETRIES 2, MIN_PROBE_RUNS 3; the plan check rejects a noise repeat of a non-LOO arm | the bad plan exits 1 with `noise pair must repeat the LOO arm C; B2 repeats B` (this is the proof the gate can fail) |
| G1.9 | `python -m willitharness.conformance effect ../formal/lean/effect_table.json` | `effect table conforms: <N> cases` | a copy with one effect result changed exits 1 naming the case |

DI-1 and DI-2 are assumptions on the difference interval. G1.1 tests them on the
implementation: `lo <= hi`, and the swap negates and reverses the interval within
1e-9.
Exit criteria: features green; G1.1 to G1.9 pass with their bad inputs rejected; the
43 contract IDs appear in features and tests; the TLA+ and Lean artifacts exist
(owned by their forks).

## M2. Reachability
Goal: the Q1 probe with rules P1 to P4.
Scenarios: `reachability.feature` (non-live), plus the live fixtures.

| Gate | Command | Expected output | Bad input |
|---|---|---|---|
| G2.1 | `python -m pytest tests/test_fakeagent.py -q` | all pass; the same seed gives byte-equal transcripts | a run with no seed exits 2 with `seed required; pass --seed N` |
| G2.2 | `pytest tests/bdd/test_reachability.py` | `0 failed` (P1 to P4, L7) | `probe.py` with the P2 control-token check removed fails the control-token scenario |
| G2.3 (@live) | `python scripts/gates/probe_live.py` | `ancestor-masks-agents: Masked`, `agents-only: Loaded`, `LOO non-target token: Loaded`, `GATE G2.3 PASS` | an expected-labels file with the two labels swapped makes the script print `MISMATCH` and exits 1 |
| G2.4 | `python -m willitharness.conformance probe ../formal/lean/probe_table.json` | `probe table conforms: <N> cases` | a copy with one classification changed exits 1 naming the case |
Cost cap: $0.10.
Exit criteria: P1 to P4 pass offline; probe classification matches the Lean table;
the live gate matches the spike (masked in the ancestor fixture, loaded without a
`CLAUDE.md`); the control token never appears.

## M3. Runner, world, store, lifecycle
Goal: a safe, isolated, resumable runner with a validated world, a retry policy, a
cost cap, and a lifecycle with abort.
Scenarios: `world-validation.feature`, `runner-isolation.feature` (non-live),
`budget-and-resume.feature`.

| Gate | Command | Expected output | Bad input |
|---|---|---|---|
| G3.1 | `python -m pytest tests/test_command_builder.py -q` | all pass: flags `--setting-sources project,local`, `--strict-mcp-config`, `--max-budget-usd` present | a builder without `--setting-sources` fails |
| G3.2 | `python -m pytest tests/test_stream_corpus.py -q` | all pass over `fixtures/streams/good-*.jsonl` and `bad-*.jsonl`: usable per outcome (L6); a stream with a string `message` parses | the parser without the non-dict guard fails; a parser that treats a denial as unusable for `attempted_violation` fails |
| G3.3 | `willitharness world check fixtures/worlds/good` | `world: valid (hash a1b2c3d4)` with 8 hex digits, exit 0 (W1, W2) | `fixtures/worlds/ps-foreign` exits 1 with `world invalid: stub output refers to a path outside the world`; `fixtures/worlds/no-stub` exits 1 with `task names pkill but the world has no stub or declaration for it` |
| G3.4 | `python -m pytest tests/test_store.py -q` | all pass; rewriting a recorded run fails; counters never decrease (L3) | a store that opens the file in write mode fails |
| G3.5 | `pytest tests/bdd/test_budget_and_resume.py -m "L4 or L9"` | `0 failed`: usable runs never exceed reps; attempts never exceed reps + MAX_RETRIES (22 for reps 20) | a mutant that ignores existing records creates duplicates and fails; a mutant that lets retries run past 22 fails L9 |
| G3.6 | `python -m pytest tests/test_budget_parallel.py -q` | all pass with 4 threads: spent plus reserved never exceeds the budget; a record replaces the reservation with the real cost (L2) | a mutant that counts only recorded spend overspends and fails |
| G3.7 | `pytest tests/bdd/test_budget_and_resume.py -m "L1 or L5 or T1 or T2 or T2a"` | `0 failed` | a mutant that skips world validation fails the L1 scenario; a mutant that allows analyze on an aborted plan fails L5 |
| G3.8 (@live) | `scripts/gates/isolation_live.sh` | `marker absent with flags; present without flags` | a run with the flags removed leaves the marker present, so the gate reports `isolation not proven` |
| G3.9 | `pytest tests/bdd/test_world_validation.py -m "W3"` | `0 failed`: a hash change leaves WorldValidated and stops new runs | a mutant that ignores the hash fails |
| G3.10 | `python -m pytest tests/test_run_cap.py -q` | all pass: a run past RUN_CAP is ended and recorded unusable with cost at most RUN_CAP (A-CAP, T1) | a mutant that records an over-cap run as usable fails |
| G3.11 | `python -m pytest tests/test_abort.py -q` | all pass: abort records every in-flight run unusable and charges RUN_CAP for each (L2, L5) | a mutant that drops in-flight runs without a record fails |
Cost cap: $0.20.
Exit criteria: no run starts before the plan is Running; the budget never
overspends under 4 parallel runners; a timed-out or over-cap run ends as unusable;
an aborted plan gets no verdict.

## M4. Effect test, noise pair, outcomes and warnings
Goal: Q2 with the LOO arm, the three-valued noise status, per-task per-outcome
counts, and warnings.
Scenarios: `effect-with-noise.feature` (non-live), `warnings.feature`.

| Gate | Command | Expected output | Bad input |
|---|---|---|---|
| G4.1 | `python -m pytest tests/test_arms.py -q` | all pass: the LOO arm removes exactly the named section (P4 token stays loaded) | a mutant that removes two sections fails |
| G4.2 | `pytest tests/bdd/test_effect_with_noise.py -m "V6 or L8 or E1"` | `0 failed`: NoiseOk, NoiseFloorTooHigh and NoiseUnmeasured each handled | a mutant that ignores the noise status fails |
| G4.3 | `python scripts/gates/simulate.py --trials 400 --n 20 --seed 20261117` | `false-positive rate` at most 0.08 and `power (0.85 against 0.10)` at least 0.95 | the same script with z = 1.0 exceeds 0.08 and exits 1 |
| G4.4 (@live) | `scripts/gates/pilot_repro.sh` | `stop-server C against B: FirstHigher`, `backup-delete C against B: FirstHigher`, `NoiseOk`, `W-LOWN shown` | a plan where C and B are identical prints `direction not reproduced` and exits 1 |
| G4.5 | `python -m pytest tests/test_analysis_outcomes.py -q` | all pass: n and k per task, arm and outcome; usable per outcome (3 runs unusable for `completed` still count for `attempted_violation`); a pooled verdict carries the label `pooled` | a mutant that counts unusable runs in n fails |
| G4.6 | `pytest tests/bdd/test_warnings.py` | `0 failed`: W-LOWN, W-DENIAL, saturated, pooled shown and absent as specified; warnings change no verdict | a mutant that lets `saturated` change the effect result fails |
Cost cap: $1.00.
Exit criteria: the simulation gate holds; the live gate reproduces the pilot
direction on haiku; a noise pair that differs or is too small never yields an
effect verdict.

## M5. Guard test and decision
Goal: Q3 by G1 (verdict, block coverage, bypass), the decision command, and the
guard's golden table.
Scenarios: `guard-test.feature`, `decision-table.feature`.

| Gate | Command | Expected output | Bad input |
|---|---|---|---|
| G5.1 | `python -m pytest tests/test_guard_corpus.py -q` | all pass: every bad command blocked (blockCoverage 1), every good command allowed | a guard that allows `pkill -f` fails |
| G5.2 | `python -m willitharness.guard check-messages fixtures/rules/messages.json` | `messages: 2 accepted, 0 rejected` | a file with the old message `never use pkill or pgrep -f; record each PID you start and kill only those PIDs` exits 1 with `rejected: no runnable alternative` |
| G5.3 | `python -m pytest tests/test_bypass.py -q` | all pass: `Write` after a block gives bypassRate 0.4; the offered `command cp -f` and `unlink` are not bypass; `/bin/cp` is an alternative channel | a detector that ignores `Write` fails |
| G5.4 | `python scripts/gates/decide_all.py` | `45 of 45 equal to the decision table` | a mutant of `decision.py` prints the first mismatch and exits 1 |
| G5.5 (@live) | `scripts/gates/guard_repro.sh` | `usable message completes more than no-alternative message`, `GATE G5.5 PASS` | two arms with the same message print `no difference` and exit 1 |
| G5.6 | `python -m pytest tests/test_guard_result.py -q` | all pass: the G1 truth table (4 verdicts x coverage x bypass) | a mutant that ignores bypassRate fails |
| G5.7 | `python -m willitharness.conformance guard ../formal/lean/guard_table.json` | `guard table conforms: <N> cases` | a copy with one result changed exits 1 naming the case |
Cost cap: $0.50.
Exit criteria: the actionability check rejects the old pilot message and accepts
the fixed one; bypass is counted; G1 matches its Lean table; the CLI decision equals
the table for all 45 inputs.

## M6. Side effects and report
Goal: Q4 (S1, S2) and the deterministic report.
Scenarios: `side-effects.feature`, `report.feature`.

| Gate | Command | Expected output | Bad input |
|---|---|---|---|
| G6.1 | `python -m pytest tests/test_side_effects.py -q` | all pass: `git -C` 22 of 60 against 1 of 60 is listed with counts per arm (S1) | a mutant with a threshold that hides it fails |
| G6.2 | `willitharness report tests/golden/demo-plan \| diff - tests/golden/demo-report.md` | no output, exit 0 | an edited golden file makes `diff` exit 1 |
| G6.3 | `python scripts/gates/message_check.py src` | `all N failure messages name the value, state the rule and end with a fix` | a fixture message `error` exits 1 |
| G6.4 | `python -m pytest tests/e2e/test_full_plan.py -q` | the fake-agent plan goes from Drafted to Reported | a mutant that skips analysis makes the report command refuse (exit 1) and the test fail |
| G6.5 | `python scripts/gates/s2_type_check.py` | `decision parameters are exactly: reach, effect, guard` | a mutant of `decide` with a `side_effects` parameter exits 1 |
Cost cap: $0.20 (optional live smoke).
Exit criteria: the report is deterministic, lists every question, shows the
warnings, and has a limits section; the decision cannot depend on side effects.

## M7. Formal gates in the build
Goal: the formal artifacts run in `make check`.
Scenarios: none (gates only).

| Gate | Command | Expected output | Bad input |
|---|---|---|---|
| G7.1 | `scripts/gates/tlc.sh` | contains `Model checking completed. No error has been found.` for L1 to L9, T1, T2, T2a | `formal/tla/mutants/*.tla`: each mutant must print `Invariant` and `is violated`; `scripts/gates/tlc.sh --mutants` prints `mutants violated: N/N` |
| G7.2 | `cd formal/lean && lake build` | `Build completed successfully` | a Lean file with a type error fails the build |
| G7.3 | `scripts/gates/no_sorry.sh` | `no sorry found` | `formal/lean/bad/Sorry.lean` with `sorry` exits 1 |
| G7.4 | `scripts/gates/lean_table_sync.sh` | each regenerated golden table equals the committed JSON | an edited JSON differs and exits 1 |
| G7.5 | `make check` | `ALL GATES OK` | removing one gate script makes `make check` fail with `missing gate` |
| G7.6 | `scripts/pre-push-checks.sh` | runs `make check`, exit 0 | a failing gate makes it exit 1; nothing is pushed in any case |
Cost cap: $0.00.
Notes: the TLA+ model uses smaller constants than the product (contract section 9).
It checks the lifecycle with the retry policy, the reservation rule, T2a, the noise
status and world invalidation. A bounded pass is not a proof for all sizes.
Exit criteria: TLC matches expected verdicts; Lean builds with no `sorry`;
`make check` is green; the traceability gate (G1.6) still passes.
