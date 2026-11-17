# 06. Risks, prior art and stop conditions

Evidence comes from the spike notes in `/tmp/ext-research/article/`. Claims about
other tools come from subagent reads of their source, not from running them.

## Prior-art overlap
| Tool | What overlaps with v0 | What it lacks (as read) | v0 response |
|---|---|---|---|
| deadrules | Leave-one-out ablation of instruction-file sections, Wilson and Newcombe intervals, a minimum-n guard | No identical-config noise run, final text only (no transcript), no reachability check, permissive agent mode | Closest overlap for Q2. v0 adds the noise pair and Invalid result (V6), Q1 and Q3. Contributing upstream is an option (stop condition STOP-1) |
| agent-skill-eval | With and without comparison for skills, Wilson and bootstrap, budgets, three agents | Arm is a skill flag, no noise run, user config can leak into both arms, its own roadmap plans configuration variants | v0 targets instruction-file rules and isolation by design |
| ruleproof | Deterministic checks over diff and transcript, the strongest isolation flags seen | Checks after the fact, no ablation runner for your own rules, only 3.2% of 1,960 real directives compiled to checks | v0 borrows the idea of isolation flags |
| rulebench (ralfyishere) | Trap tests of rule bundles | LLM judge from the same model family, median of 3 runs, no intervals, no isolation | v0 uses deterministic checks and intervals |
| rulebench (treestar84) | One-rule ablation with a filler control | Saturated 97% baseline, pseudo-replication, no tests, no isolation | v0 uses a leave-one-out arm and reports saturation (warning `saturated`) |
| ruleprobe (Jake Selby) | Hit counts and "unobserved" over past transcripts | Does not run agents, zero hits is ambiguous | Complementary. v0 does not read private transcripts |

What v0 adds that the read tools did not show: the reachability probe (Q1), the
noise pair with an invalid verdict (V6), the guard-message completion test (Q3),
world validation, a side-effect report and a formal contract. Search was not
exhaustive. Treat "not found" as "not found in what we read".

## Validity risks found in the spike
| Risk | Evidence | Mitigation in v0 | Gate or scenario |
|---|---|---|---|
| A bad stub world invalidates runs | F19: the `ps` stub listed processes outside the checkout | World validation W1 to W3 | G3.3, world-validation.feature |
| Permission allowlist denies chained commands and hides completed work | F16: sonnet guard run 3 | Per-outcome usability, denial counts, W-DENIAL warning | runner-isolation.feature |
| Attempts are not executed commands | F5 | Label outcomes, show blocked counts separately | guard-test.feature, report.feature |
| Agents route around a Bash guard through another tool | F15: `Write` in 4 of 10 sonnet runs | Bypass rate lowers the guard result | G5.3 |
| Reachability is the model's own report | Spike token tests, n = 3 | Control token, P1 to P4, repeated probes | G2.2, G2.3 |
| Isolation is partly tested | U6: no user-level instruction file existed, so the test could not show leakage; Claude Code version was not recorded | Record the CLI version in every report; optional marker check | G3.8 |
| Tasks written by the plan author | F17 held on natural tasks, but we wrote them | Say so in the report limits | report.feature |
| One model per plan, and drift over time | U11, sonnet costs 14 times more | Report the model; no cross-model claims | report.feature |
| Pooled intervals ignore task clustering | Spike B caveat | Per-task verdicts first; a pooled verdict is labeled `pooled` with a warning (contract section 4) | effect-with-noise.feature, warnings.feature |
| Shell parsing has gaps | Known gaps list | A documented corpus of known gaps | G5.1 |
| `/bin/cp` meets the intent but not the letter | Pilot guard results | Listed as an alternative channel, not a violation and not counted as bypass (plan assumption, open CI-16) | runner-isolation.feature, guard-test.feature |
| The contract defines bypass in a way that could count the guard's own advice | CI-16 (open) | Bypass counts only channels the block message did not offer | G5.3 |
| NoiseStatus is defined for one outcome; the guard compares `completed` | CI-17 (open) | The report shows the `completed` noise status as a line; G1 stays as written | effect-with-noise.feature |
| P4 failure has no row in the E1 table, and P1 does not say whether unusable probe runs count | CI-18 (open) | A failed P4 gives `Invalid`; only usable probe runs count | reachability.feature |
| RUN_CAP is a runner assumption (A-CAP), not a proven property | Contract section 9 | Wall-clock limit plus the agent's budget flag; tests with a fake clock; live gates print spend | G3.10 |

## Engineering risks
| Risk | Mitigation |
|---|---|
| Spec and code drift apart | Conformance gate G1.5 for the decision table; a later trace-validation step (not in v0) |
| TLC is heavy (an overwatch spec needed about 9 minutes and a 10 GB heap) | Small bounds, one spec for the lifecycle, a time cap in the gate |
| Lean toolchain is large | Install under `/tmp` or a pinned `ELAN_HOME`; core library only; no Mathlib |
| Scope creep (facts store, TCR, skills, multi-model) | File 01 lists what is out and why. A new item needs a written reason and a cost cap |
| Cost overrun | Budget module with reservations (rule L2), milestone caps, haiku in gates |
| The `claude` CLI output changes | Parser corpus (G3.2), version recorded, adapter interface |
| Name collisions | `willitharness` was free on PyPI, npm and GitHub search at check time. Trademarks and domains are not checked |

## Honest limits
- v0 says "this rule changed this behavior on these tasks with this model". It does
  not say "this rule is good".
- `DeleteCandidate` means "no measurable effect at this n". It is advice.
- Formal methods cover the pure logic and the lifecycle. They do not cover agent
  behavior, shell parsing, or the CLI (contract section 8).
- The evidence behind the design is two rules and mostly haiku.

## What would make us stop
| ID | Condition | Action |
|---|---|---|
| STOP-1 | A prior-art tool adds a reachability probe and a noise pair with an invalid verdict | Stop building. Contribute upstream |
| STOP-2 | G4.4 does not reproduce the pilot direction at a cost of $1.00 or less after one fix | Pause. Review the design |
| STOP-3 | On a harness that is not ours, over half of the tested rules end as `CannotDecide` or `NeedsMoreRuns` at 20 runs per cell | Cut to a reachability-only tool |
| STOP-4 | A normal rule check costs over $2 at 20 runs per cell on haiku | Reduce arms or reps. Re-plan |
| STOP-5 | The reachability result flips for the same fixture across two Claude Code versions | Pin versions. If that fails, drop the Q1 claim |
| STOP-6 | Formal gates take more than a third of the M7 time | Cut formal scope to the verdict and decision logic |
| STOP-7 | Three outside rule checks on real harnesses find nothing a user acts on | Stop or pivot |
