# Contract issues: status against contract v0.3

Contract v0.3 resolves CI-16, CI-17 and CI-18 and the TLA+ and Lean gaps listed in the contract's section 11. The text below keeps the v0.2 record. Items that change a Lean table, the guard code or the TLA+ model are still to be built.

Source: `../00-domain-contract.md` (v0.2, not edited). v0.1 is kept as
`../00-domain-contract.v0.1.md`. Section 11 of v0.2 lists every change.
The 15 issues found against v0.1 are all resolved. Three new issues were found
while applying v0.2. They are open.

## Issues from v0.1
| ID | Short description | Status | Resolved by (v0.2 item) |
|---|---|---|---|
| CI-01 | Noise pair did not say which arm it repeats | Resolved | Glossary "Noise arm" (repeat of the LOO arm); V6 |
| CI-02 | Q1 had no rule that produces Loaded, Masked, Unknown | Resolved | P1 to P4; constant MIN_PROBE_RUNS = 3 |
| CI-03 | Saturation was not modeled | Resolved | Warning `saturated` (section 4); D6 report text (section 6) |
| CI-04 | "Usable run" was run-level; denials hid completed work | Resolved | "Usable run, per outcome" (section 4); warning W-DENIAL |
| CI-05 | L2 ignored in-flight runs | Resolved | L2 reservation rule; assumption A-CAP (sections 2 and 7) |
| CI-06 | L4 conflicted with retries | Resolved | Retry policy (section 7); L4 counts usable runs; L9 caps attempts at reps + MAX_RETRIES |
| CI-07 | Guard result ignored bypass through another tool | Resolved | G1 (inputs blockCoverage and bypassRate). The definition of bypass is refined in CI-16 |
| CI-08 | No timeout transition | Resolved | Transitions in section 7 (timeout or cost above RUN_CAP gives RecordedUnusable) |
| CI-09 | Side effects had no ID | Resolved | S1 and S2 |
| CI-10 | `WorldValidated` had no checks | Resolved | W1 to W3; world hash change leaves WorldValidated (section 7) |
| CI-11 | Per task or pooled counts were not stated | Resolved | Section 4: per task first; pooled needs the label `pooled` and a warning |
| CI-12 | MIN_RUNS = 5 is too low to trust | Resolved | MIN_RUNS stays the hard floor; DEFAULT_REPS = 20; warning W-LOWN |
| CI-13 | Map from verdict to effect result was implicit | Resolved | E1 table. The P4 failure row is missing, see CI-18 |
| CI-14 | Target outcome was undefined | Resolved | Glossary: outcomes `attempted_violation`, `completed`, `blocked_count`. Noise per outcome is open, see CI-17 |
| CI-15 | Leave-one-out arm must still load the other rules | Resolved | P4 |

## New issues found against v0.2 (open)
| ID | Sev | Gap | Plan assumption until the contract decides | Where it shows |
|---|---|---|---|---|
| CI-16 | M | G1 defines bypass as "another tool or path produced the effect the blocked command would have produced". The guard's own block message offers `command cp -f` and `unlink`, and those also produce the effect. The definition would count the intended path as a bypass. | Bypass means the effect came through a channel the block message did not offer. A non-Bash tool such as `Write` or `Edit` that writes the blocked command's target path is a bypass. An absolute-path call of the same program (for example `/bin/cp`) is an alternative channel: reported, not counted in bypassRate. | Backlog T41; scenarios in `guard-test.feature` carry a plan-assumption comment |
| CI-17 | M | NoiseStatus is defined for the pair verdict on one outcome. E1 uses `attempted_violation`. G1 uses the `completed` verdict, but the contract does not say whether a noise check for `completed` is needed. | The report computes NoiseStatus per outcome and shows the `completed` noise status as a report line. G1 stays as written. | Backlog T33, T40; `effect-with-noise.feature` |
| CI-18 | L | P4 says an invalid LOO arm means "the plan cannot report an effect", but the E1 table has no row for it. P1 says "runs per arm" but does not say whether unusable probe runs count. | A failed P4 gives EffectResult `Invalid`. Only usable probe runs count toward MIN_PROBE_RUNS. | Backlog T16, T34; `reachability.feature` |

## Items checked and not issues
- W-LOWN compares against DEFAULT_REPS (20), not against the plan's own `reps`.
  This is by design. A plan that sets a lower `reps` always shows W-LOWN.
- A-CAP is an assumption about the runner. The plan enforces it with a wall-clock
  limit and the agent's own budget flag. It is not proven (contract section 9).
- The TLA+ model uses smaller constants than the product (contract section 9). The
  plan's gates for the product use the real constants.
