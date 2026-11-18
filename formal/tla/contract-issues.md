# Contract issues found while writing the TLA+ model

Source: `docs/contract.md` (v0.4). Part 3 gives the status of the nine gaps in Part 2 against v0.3.
Part 1 gives the status of the 12 issues raised against v0.1. Part 2 lists the new gaps
found while updating the model to v0.2.

## Part 1. Earlier issues against v0.1

| # | Issue (short) | Status in v0.2 | How the model now treats it |
|---|---|---|---|
| 1 | Spend accounting with parallel runs | Resolved: L2 has the reservation rule | `BudgetAllows == Spent + Reserved + RunCap <= Budget`. L2 is `Spent + Reserved <= Budget`. |
| 2 | L2 holds only if `RUN_CAP` is a true cap | Resolved as assumption A-CAP. Not provable in the model | A `Timeout` step ends a run and charges `RunCap`. The runner must enforce A-CAP. The model cannot check that it does. |
| 3 | Abort with runs in flight | Resolved in section 7 | Abort records in-flight runs unusable and charges `RunCap` each. |
| 4 | T2 is false when abort is allowed | Resolved: T2 and T2a | TLC still violates T2 when abort is allowed. The suite expects that. T2a holds. |
| 5 | Pending is not a stored state | Resolved: derived | Pending is derived from the counters. |
| 6 | L3 is per run, model uses counters | Resolved: contract says counters in the model | L3 checks that usable, unusable and cost counters never decrease. Per-run immutability is left to implementation tests. |
| 7 | "Every arm" in L1 | Resolved: "every arm of the plan" | L1 uses the plan's arms. |
| 8 | Aborted plan and verdicts | Resolved in L5 | See N4 below for how the model reads it. |
| 9 | L8 against V6 | Resolved: merged | L8 needs a noise arm and `NoiseOk`. V6 repeats the second half. |
| 10 | Retry policy | Resolved: retry rule and L9 | Unusable runs do not use up a rep. Attempts are capped at `Reps + MaxRetries`. |
| 11 | Fairness undefined | Resolved: assumption F | Weak fairness on runner steps only. None on Abort, Timeout or WorldChanged. |
| 12 | `MIN_RUNS` constant | Resolved: section 9 note | The model uses 1 or 2. |

## Part 2. New gaps found in v0.2

| # | Where | Gap | What the model assumes | Suggested fix |
|---|---|---|---|---|
| N1 | Section 7, "Pending" | "Pending work" is defined as fewer than `reps` usable runs and attempts below the cap. That ignores runs in flight. With parallel runs, starting while others are in flight can push usable runs above `reps`. The L4 mutant shows TLC reaching exactly that. | A start needs `usable + in flight < reps` and `attempts < reps + MAX_RETRIES`. | Count in-flight runs in the definition of pending work. |
| N2 | T2, W3 | T2 needs the world to change only finitely often. If it can change forever, the plan can loop between changed and re-validated, and Start never stays enabled. Weak fairness does not help. | `MaxWorldChanges` bounds the number of changes. | Add an assumption: the world changes finitely often. |
| N3 | W3 | "Moves the plan out of WorldValidated" is not defined for the later states. | From WorldValidated or ReachabilityChecked the plan goes back to Drafted. In Running it stays Running with starts blocked. Reachability results are kept. | State this in section 7. |
| N4 | L5 | A plan can be Aborted after Analyzed, when verdicts may exist. "An Aborted plan gets no verdict" does not say what happens to them. | Abort discards the noise status and every effect result. | Say "discarded", or forbid Abort after Analyzed. |
| N5 | V6 | A plan with no noise pair has no NoiseStatus. | NoiseUnmeasured. | Say that a missing pair is NoiseUnmeasured. |
| N6 | Section 7 | When every retry is used and a cell still has fewer than `reps` usable runs, is the plan Complete? | Complete. The small count then gives NotEnoughRuns. BudgetStopped only when the budget blocks a start. | State it. |
| N7 | A-CAP | A timeout may cost less than `RUN_CAP`. The contract does not say what to charge. | The full `RUN_CAP`, and the run counts as an attempt. This is the safe choice. | State the charge. |
| N8 | P4 | P4 says the plan cannot report an effect if the LOO arm is not Loaded. That is not one of L1 to L9. | Not modelled. | Add it as a property, or fold it into L7 for the LOO arm. |
| N9 | Section 4 | "Usable per outcome" has two meanings (`attempted_violation`, `completed`). The model has one usable counter. | One abstract outcome. L6 checks only that one. | Model two usable counters if per-outcome mistakes matter. W-DENIAL is not modelled either. |

## Part 3. Status of N1 to N9 in contract v0.3

| # | Status | Where the model checks it |
|---|---|---|
| N1 | Resolved. Section 7 counts runs in flight in "Pending". | `CanStart`. Mutant L4 removes the in-flight count and must violate L4. |
| N2 | Resolved. Section 7 assumes the world changes finitely often. | `MaxWorldChanges` bounds `WorldChanged`. |
| N3 | Resolved. Section 7 says what a world change does in each state. | Property `W3`. Mutant W3 erases reachability results and must violate it. The probe `NeverStartBlockedByWorld` shows a Running plan with starts blocked. |
| N4 | Resolved by forbidding abort after Analyzed. | `Abort` excludes Analyzed and Reported. Invariant `AbortBeforeAnalyzed` uses the history flag `analyzed`. Mutant abort allows abort after Analyzed and must violate it. The probe `NeverAnalyzed` shows the state is reachable. `Abort` no longer resets noise status or effects, because an Aborted plan cannot hold them (L5). |
| N5 | Resolved. V6 says a missing pair is NoiseUnmeasured. | `NoiseMeasurable` needs the noise arm. L8 and the probe `NeverNoPairReported` cover the no-pair path. |
| N6 | Resolved. Section 7 says exhausted retries still end Complete. | The probe `NeverCompleteWithShortCell` shows a Complete plan with a cell short of `Reps`. |
| N7 | Resolved. Section 7 says a timeout charges the full `RUN_CAP`. | Property `TimeoutCharges`. Mutant T charges nothing and must violate it. |
| N8 | Open in the model. v0.3 gives a failed P4 the EffectResult Invalid and folds the check into L7 for the rule arm only. | Not modelled. The Lean and Python parts cover it. |
| N9 | Open. Per-outcome usable counts are still one abstract counter. | Not modelled. |

Unclear in the contract: section 7 says Abort is reachable from "any state before
Analyzed". The model reads that as Drafted to Complete or BudgetStopped. The history flag
`analyzed` is a model variable, not a contract term. The finite-world-changes assumption is
stated in prose, not as a numbered item.

## Part 4. Resume in contract v0.4

| # | Status | Where the model checks it |
|---|---|---|
| R1 | Resolved. Section 7 defines resume: BudgetStopped to Running only, strictly higher budget, world validated, `endedBy` reset. | Action `Resume`, constants `MaxResumes` and `MaxBudget`. Property `L10`. Mutants RA (resume from Complete) and RD (resume without a valid world) must violate it. |
| R2 | Resolved. L11: the budget never decreases. | Property `L11`. Mutant RB (any budget from 0) must violate it. |
| R3 | Resolved. L12: a Running plan is never marked as ended. | Invariant `L12`. Mutant RC (`endedBy` kept) must violate it. |
| R4 | Open by design. A-FP (the plan is identical except `budget_usd`) has no plan content in the model. | Not modelled. The implementation fingerprint covers it (backlog T61). |
| R5 | Open. Run records carry no world hash. | Not modelled. Backlog T62. |
