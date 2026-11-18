# willitharness: TLA+ model of the run lifecycle (contract v0.4)

Status: spike. The model checks the lifecycle of section 7 of
`docs/contract.md` (v0.4). It does not check the
verdict numbers or agent behavior.

## Files

| File | What it is |
|---|---|
| `WillItHarness.tla` | The model. Operators `L1` to `L12`, `T1`, `T2`, `T2a` are the contract IDs. `V6` is the noise rule lifted to the lifecycle. |
| `Probes.tla` | 23 probes. Each says "this never happens". TLC must violate each one. |
| `nominal.cfg` `budget_tight.cfg` `unusable.cfg` `unknown_reach.cfg` `abort.cfg` `world_change.cfg` `two_tasks.cfg` `resume.cfg` `resume_big.cfg` `resume_world.cfg` `resume_abort.cfg` | One scenario each. |
| `check_models.py` | Runs every scenario, probe and mutant. Compares each result with what it must say. |
| `generated/` | Files the runner writes: the 17 mutant specs and every probe and mutant `.cfg`. Safe to delete. Not tracked by git; `repo_checks.py` fails if a file there is tracked. |
| `contract-issues.md` | Status of the 12 earlier issues, 9 new gaps and the resume items. |
| `last_run.txt` | Output of the last full run. |

## What is modelled

- Plan states: Drafted, WorldValidated, ReachabilityChecked, Running, Complete,
  BudgetStopped, Aborted, Analyzed, Reported.
- Three arms: `LOO` (leave-one-out), `Rule`, and `Repeat` (the noise repeat of `LOO`). A
  plan may or may not include `Repeat`. That is what makes L8 testable.
- Per cell (arm, task): counters for attempts (started), usable runs, unusable runs, and
  recorded cost.
- Retry: an unusable run does not use up a rep. A start needs
  `usable + in flight < Reps` and `attempts < Reps + MaxRetries`. L4 caps usable runs
  at `Reps`. L9 caps attempts at `Reps + MaxRetries`.
- Run ends: `Record` ends a run as usable or unusable (harness failure, cost 0 to
  `RunCap`). `Timeout` ends a run as unusable and charges `RunCap` (A-CAP).
- Budget: a start needs `Spent + Reserved + RunCap <= budget`. `Reserved` is `RunCap`
  times the runs in flight.
- World: `WorldChanged` (a hash change) sets the world to not validated. From
  WorldValidated or ReachabilityChecked the plan goes back to Drafted. In Running it
  stays Running and no new run can start until `ValidateWorld` runs again. A counter
  bounds the number of changes (`MaxWorldChanges`).
- A reachability result per plan arm: Loaded, Masked or Unknown.
- Noise: `NoiseStatus` is derived from the counters. Fewer than `MinRuns` usable runs
  on `LOO` or `Repeat`, or no `Repeat` arm, gives NoiseUnmeasured. Otherwise TLC
  chooses NoiseOk or NoiseFloorTooHigh freely, because the numbers are not modelled.
- Verdict step: assess noise, emit an effect result per rule arm, then report. An
  effect result is Reported only with a noise arm and NoiseOk. An arm with Unknown
  reachability is Withheld.
- Resume: `Resume(b)` moves BudgetStopped to Running with a new budget `b` strictly above
  the current one and at most `MaxBudget`. It needs the world validated, resets `endedBy`
  and keeps the reachability results. `MaxResumes` bounds the number of resumes. The
  budget is now a variable that starts at `Budget`. A world change is allowed in
  BudgetStopped and leaves the plan BudgetStopped. Assumption A-FP (same plan except the
  budget) is not modelled.
- Abort: allowed only before Analyzed. It records runs in flight as unusable at `RunCap`
  each. An Analyzed or Reported plan cannot be aborted, so an Aborted plan never holds a
  noise status or an effect result. The history flag `analyzed` exists only to check this.

## Properties

| ID | Meaning | Kind |
|---|---|---|
| L1 | A run starts only in Running, with the world validated and every plan arm checked | action property |
| L2 | `Spent + Reserved <= budget` (the current budget) | invariant |
| L3 | Recorded counters and cost never decrease | action property |
| L4 | Usable runs per cell never exceed `Reps` | invariant |
| L5 | No verdict before Complete or BudgetStopped. An Aborted plan has none | invariant |
| L6 | Counts in the report equal the usable runs | invariant |
| L7 | An arm with reachability Unknown gets no effect result | invariant |
| L8 | An effect result needs a noise arm and NoiseOk | invariant |
| L9 | Attempts per cell never exceed `Reps + MaxRetries` | invariant |
| L10 | A resume happens only from BudgetStopped, with the world validated, a strictly higher budget, ending in Running with `endedBy` reset | action property |
| L11 | The budget never decreases | action property |
| L12 | A Running plan has `endedBy` = none | invariant |
| AbortBeforeAnalyzed | A plan that was Analyzed is never Aborted (contract v0.3, section 7) | invariant |
| W3 | A world change keeps reachability results, sends WorldValidated and ReachabilityChecked back to Drafted, and keeps Running in Running | action property |
| TimeoutCharges | A timeout charges exactly `RunCap` and starts no run | action property |
| V6 | An effect result needs NoiseOk | invariant |
| T1 | Runs in flight eventually reach zero | liveness |
| T2 | Running leads to Complete or BudgetStopped (no abort) | liveness |
| T2a | Running leads to Complete, BudgetStopped or Aborted | liveness |
| TypeOK | Types and ranges | invariant |

Assumption F (fairness): weak fairness on every runner step, including `ValidateWorld`.
None on Abort, Timeout and WorldChanged. WorldChanged is also bounded. Without that bound
the world could change forever and `Start` would never stay enabled.

## Results (measured, 2 TLC workers, TLC 2.19, one machine)

The whole suite: **52 of 52 runs matched what they must say, in 318 s (the sum of the per-run times).** This is a local run on one machine. CI has not run it.

Scenarios. Every one passed.

| Scenario | Bounds | States generated | Distinct | Seconds |
|---|---|---|---|---|
| nominal | 1 task, reps 2, retries 1, `RunCap` 2, budget 12, `MinRuns` 2 | 107,014 | 31,286 | 6.2 |
| budget_tight | same, budget 5 | 40,526 | 22,590 | 2.9 |
| unusable (retry and timeout) | reps 1, retries 1, `RunCap` 1, budget 9, `MinRuns` 1 | 310,714 | 129,898 | 14.1 |
| unknown_reach | nominal plus reachability Unknown | 357,904 | 104,095 | 18.6 |
| abort | unusable bounds plus abort, checks T2a | 421,026 | 171,360 | 17.2 |
| world_change | reps 1, retries 1, one world change, `MinRuns` 1 | 16,636 | 9,158 | 1.6 |
| two_tasks | 2 tasks, reps 1, retries 0, `MinRuns` 1 | 1,040,634 | 175,826 | 140.7 |
| resume | reps 1, retries 0, `RunCap` 2, budget 3, `MaxBudget` 6, one resume | 17,106 | 9,390 | 1.4 |
| resume_big | nominal with budget 5, `MaxBudget` 12, two resumes | 425,570 | 211,406 | 21.5 |
| resume_world | resume plus one world change | 55,184 | 28,154 | 2.5 |
| resume_abort | unusable bounds with budget 3, `MaxBudget` 9, one resume, abort allowed, checks T2a | 1,430,650 | 709,684 | 55.8 |

With abort allowed, TLC violates T2 as written (116,136 states, 3.6 s). The run
`abort: T2 fails when abort is allowed` expects exactly that.

Probes. All 23 were violated, so each state is reachable: BudgetStopped, Reported, an
unusable run, a timeout, an extra attempt beyond `Reps`, the attempt cap reached,
NoiseOk, NoiseFloorTooHigh, NoiseUnmeasured, a Reported plan with no noise arm, an
effect Reported, an effect Withheld for an Unknown arm, Aborted, an abort after a
verdict, a plan that was Analyzed, a Complete plan with a cell short of `Reps`, a Masked arm, a
world change, a Running plan blocked by a changed world, a resume, a plan stopped by the
budget again after a resume, a Complete plan after a resume, and a BudgetStopped plan
whose world changed.
The longest probe run took 1.5 s.

Mutants. Each mutant is the spec with one tagged line replaced. The runner checks that
exactly one line changes. Each mutant is checked against only the property it breaks,
and TLC named exactly that property:

| Mutant | One-line change | Result (states generated) |
|---|---|---|
| L1 | Start allowed before reachability is checked | violation of L1 (16) |
| L1w | Start allowed while the world is not validated | violation of L1 (276) |
| L2 | Budget check replaced by TRUE | violation of L2 (168) |
| L3 | Recording a usable run can erase an unusable one | violation of L3 (578) |
| L4 | In-flight runs no longer count toward `Reps` | violation of L4 (3,938) |
| L5 | Noise assessed while still Running | violation of L5 (100) |
| L6 | Report counts usable plus unusable runs | violation of L6 (31,400) |
| L7 | Unknown arms no longer withheld | violation of L7 (339,159) |
| L8 | Effect Reported without a noise check | violation of L8 (86,276) |
| L9 | Attempt cap removed | violation of L9 (2,683) |
| abort | Abort allowed after Analyzed | violation of AbortBeforeAnalyzed (16,368) |
| W3 | A world change erases the reachability results | violation of W3 (20) |
| RA | Resume allowed from Complete too | violation of L10 (25,338) |
| RB | Resume accepts any budget, also a lower one | violation of L11 (263) |
| RC | Resume keeps `endedBy` | violation of L12 (323) |
| RD | Resume needs no validated world | violation of L10 (1,450) |
| T | A timeout charges nothing | violation of TimeoutCharges (114) |

State counts for violating runs vary a little from run to run, because TLC stops at the
first violation with 2 workers. Counts for passing runs do not vary.

Two things the suite caught while moving to v0.2:
- The first L3 mutant did not fail. With `Reps = 1`, no run can be in flight while a
  usable run is recorded, so the mutated line could never lower the usable count. The
  runner reported the mismatch. The mutation now lowers the unusable counter, and it
  fails as it should.
- The first retry scenario (reps 1, retries 2, `RunCap` 2) ran past 3 minutes and was
  stopped by hand. It was trimmed to retries 1 and `RunCap` 1. It now takes 13 s and
  still reaches the attempt cap.

## How to rerun

```
cd formal/tla
python3 check_models.py                 # all 52 runs, about 5.3 minutes
python3 check_models.py --only mutant   # one family
python3 check_models.py --list
```

It needs a JDK and the TLC jar. Defaults: Java at `/opt/homebrew/opt/openjdk/bin/java`
and the jar at `~/.cache/tlalings/tla2tools.jar`. Override with `--java` and `--jar`. The runner refuses a jar whose sha256 is not the pinned one (tlaplus release v1.7.4, digest in `check_models.py`).
The runner exits with 1 on any mismatch. `two_tasks` takes 140.7 s of the 318 s because of
its liveness check.

## What is NOT proven

- The model is bounded: 3 arms, 1 or 2 tasks, 1 or 2 reps, 0 or 1 retries, small costs,
  at most one world change, at most two resumes. A pass is not a proof for other sizes. `MinRuns` is 1 or 2,
  not 5.
- Agent behavior is not modelled. Neither are the Wilson and Newcombe numbers, the effect
  mapping E1, the guard rule G1, the probe rules P1 to P4, or the decision table. The
  Lean part and property tests cover those.
- Runs are counters, not records. Per-run identity and per-run immutability are not
  checked. L3 says the counters never decrease.
- One abstract outcome stands for "usable". The two outcomes of the contract
  (`attempted_violation`, `completed`) are not tracked separately, so L6 checks only one.
- P4 (the LOO arm must be Loaded) and the denial warning W-DENIAL are not modelled.
- A-CAP (one run never costs more than `RunCap`) is an assumption. The model charges
  `RunCap` on a timeout and does not check that the real runner does.
- A-FP (a resume keeps the plan identical except the budget) has no plan content in the model. The implementation fingerprint covers it. Run records carry no world hash, and the model does not show it.
- The number of world changes is bounded by assumption. T2 needs that bound.
- The mutants prove that these checks can fail on these seventeen bugs. They do not prove
  the spec has no other bug.
- A probe proves a state is reachable in its scenario. It does not prove a real run
  reaches it.
