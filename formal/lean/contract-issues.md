# Contract issues: status against contract v0.3

Contract v0.3 settles N1, N2, N3, N4, N5, N6 and N10 below. Lean now models them: coverage is a three-value input (Full, Partial, NoneSeen), a guard arm with too few runs or NoneSeen coverage gives GuardUntested, and `reported_table.json` gives the implementation a golden table for `Reported`. N7 to N9, N11 and N12 stay as listed.

## Earlier issues (from the v0.1 proofs)
| # | Issue | Status in v0.2 |
|---|---|---|
| 1 | V3 needs an ordered interval (low <= high) | RESOLVED. DI-1 is stated. Lean class field `diff_ordered`. |
| 2 | V4 needs identical pairs to contain 0; redundant with swap | RESOLVED. DI-2 (swap) is stated. The extra field is gone. `diffSelf_derived` proves it. |
| 3 | V5 unused by the verdict proofs; Newcombe-over-Wilson link not formalized | RESOLVED as a label: V5 is "property-tested, not proven; Lean assumes it". The Newcombe-over-Wilson link is still not formalized. That part stays OPEN by design (see N11). |
| 4 | Noise arm size unspecified; small noise arm gave `noiseOk` | RESOLVED. NoiseUnmeasured exists. `V6_unmeasured_iff`, `E1_unmeasured_invalid` prove it. |
| 5 | GuardMatchesRule mixed a statistical test with an operational claim | RESOLVED. G1 takes three inputs. `guardOf` and the G1 theorems follow it. Measurement of two of the inputs is still undefined (N2). |
| 6 | `decide` clashes with Lean's `decide` | RESOLVED. The contract names `decideRule`. |
| 7 | D6 may be over-read | RESOLVED in the contract text (D6 report text, `saturated` flag). Lean does not model report text. OPEN for the BDD plan. |
| 8 | `effectOf` mapping not in the contract | RESOLVED. E1 table. One Lean theorem per row. |

## New gaps found while updating to v0.2
N1. G1 and a guard arm with too few runs. If the guard arm ran but its `completed`
    verdict is InconclusiveSmallN, G1 returns GuardWorse. GuardUntested means "no
    guard arm was run". A user sees "worse" for an unmeasured guard. Suggest
    GuardUntested or a NeedsMoreRuns-style value for that case.
N2. `blockCoverage` and `bypassRate` have no definition. What is the denominator
    (violating commands seen, or runs)? What is the value when the guard saw no
    violating command (0 of 0)? Lean takes both as rationals and the golden table
    as booleans (coverage = 1, bypass = 0). A vacuous coverage of 1 would let a guard
    that never fired pass G1.
N3. Probe inputs have no validity rule. The contract does not require
    targetHits <= runs and controlHits <= runs. Lean's `probeResult` is total, and
    returns Unknown for targetHits > runs (not equal, not 0). The golden table covers
    only valid inputs.
N4. P4 reuses P1 to P3. Lean probes the LOO arm with `probeResult`, so a LOO probe
    with fewer than MIN_PROBE_RUNS runs, or with a control hit, is invalid. The
    contract says only "must be Loaded". Please confirm that P1 and P2 apply.
N5. L7 is applied to the rule arm only (`ruleReach`). The LOO arm is covered by P4.
    The contract says "an arm with reach = Unknown gets no effect verdict". Please
    confirm no other arm needs the check.
N6. `Reported` is a pure predicate over `PlanFacts`. TLA+ models L8 inside the
    lifecycle. Nothing machine-checks that the two agree. Suggest a golden
    conformance table for the gate, like the other four.
N7. Warnings (W-LOWN, W-DENIAL, `saturated`, `pooled`) are "report only, never change
    a verdict". Lean models only S2, by type. A future change could let a warning
    feed a decision without breaking any theorem. Needs an implementation test.
N8. S2 is a type-level argument. The Lean theorem is true by construction (`rfl`).
    It is documentation, not detection.
N9. Per-outcome usable runs (`attempted_violation` against `completed`) and the
    `pooled` label are not modeled. Counts are inputs to `verdictOf`.
N10. D6 together with `saturated`. The contract says the D6 report shows the flag,
     but the decision value stays DeleteCandidate. Please confirm that a saturated
     LOO arm (k = 0) should not change D6 to a softer value such as CannotDecide.
     A LOO arm at 0 violations leaves nothing for the rule to lower.
N11. Nothing links the numeric Newcombe code to DI-1 and DI-2. A property test must
     check ordering and swap symmetry on random counts. Suggest naming that test in
     the BDD plan.
N12. `zeroOracle` shows DI-1 and DI-2 are consistent. No witness exists for the
     V5 assumption, so V5 could in principle be inconsistent with the other two.
     Low risk, because the real Wilson interval satisfies V5.
