# 01. Scope of v0

v0 answers one user question: "Does this rule in my harness file work, and what
should I do with it?" It answers with the four questions of the contract
(Q1 reachability, Q2 effect, Q3 guard, Q4 side effects) and the decision table.
Contract: v0.5.

## What v0 includes
| # | Capability | Why (spike evidence) | Contract IDs |
|---|---|---|---|
| 1 | Reachability probe for instruction files, with a control token and a check of the leave-one-out arm | F1: `AGENTS.md` is a fallback that an ancestor `CLAUDE.md` hides. F2: a masked rule had no effect. | P1 to P4, L7 |
| 2 | Isolated runner with a validated stub world, outcomes counted per task cell, usable per outcome | F19: a bad stub world invalidated runs. F16: allowlist denials hid work. | W1 to W5, L1, L6 |
| 3 | Effect test: LOO arm, noise pair (a repeat of the LOO arm), three-valued noise status, interval verdicts | F3, F6, F17: effects were large and the noise arm showed no false difference at n = 20. | V1 to V6, DI-1, DI-2, E1, L8 |
| 4 | Guard test measured by completion, with block coverage and bypass | F4: a guard needs a usable block message. F5: a guard blocks the command, not the attempt. F15: agents route around a Bash guard. | G1 |
| 5 | Decision table | The point of the tool: keep, fix loading, replace with a script, or delete candidate. | D1 to D12 |
| 6 | Side-effect report | F18: loading a file changed other behavior (`git -C` 22 of 60). | S1, S2 |
| 7 | Budget with reservations, retry policy, abort, idempotent resume | F7: runs are cheap. Spike B still overspent its cap. | L2 to L5, L9, T1, T2, T2a |
| 8 | Warnings: W-LOWN, W-DENIAL, saturated, pooled | F6 (n = 5 wobbles), F13 (saturation), F16 (denials) | report only |

## What v0 leaves out
| Item | Why it is out | When to revisit |
|---|---|---|
| Facts store (dated, sourced facts) | No experiment has touched it. Planning code for an untested idea would repeat the early mistake of the spike. | After a spike that tests it |
| Skill-trigger tests | Spike C covered one skill on haiku. The signal is a `Skill` tool call, which needs a different probe and different outcomes. | v0.2, with spike C data as the starting point |
| Hook tests | Context-injecting hooks passed a sentinel probe. A blocking hook is already covered by the guard test (Q3). More hook types add little for v0. | v0.2 |
| Multi-model matrix | Sonnet costs about 14 times haiku per run. Model drift also breaks comparisons over time (open question U11). v0 runs one model per plan. The user picks it. | After v0 proves its value |
| Web UI | A report in Markdown and JSON is enough to test the idea. | Only if users ask |
| Other agents (Codex, OpenCode) | Isolation flags and stream parsing are agent specific. v0 targets Claude Code behind one adapter so a second one can follow. | v0.3 |
| Mining tasks from real sessions | Access to session transcripts was denied during the spike, and transcripts hold private data. | Only with an explicit, local, opt-in design |
| Auto-written rule edits | Auto-generated context files cost more and did not help in the cited study (F9). | Not planned |

## Definition of v0 done
1. All milestones M0 to M7 pass their gates (see file 03).
2. The live reproduction gates (G4.4 and G5.5) reproduce the direction of the pilot
   results at a total spend of at most $2.00.
3. The Lean project builds with no `sorry`. The TLC runs agree with their expected
   verdicts (contract section 10).
4. The report for the pilot rules prints a decision for each rule, shows the
   warnings, and lists its limits.

## Assumptions to check early
| ID | Assumption | Check | If false |
|---|---|---|---|
| A1 | The `claude` CLI accepts the isolation flags the pilot used (`--setting-sources project,local`, `--strict-mcp-config`). | Task T20 and gate G3.1 | Change the command builder. Re-run the isolation check (T31). |
| A2 | Stream-json output keeps the fields the pilot parsed (`result`, `total_cost_usd`, `num_turns`, `permission_denials`). | Task T21 and gate G3.2 on a fresh transcript | Update the parser. Version-pin the CLI in the report. |
| A3 | A fake agent can model the real agent well enough to test the statistics. | Gate G4.3 against the pilot rates | Keep the fake agent for logic tests only. Do not use it for power claims. |
| A4 | A rule maps to one section of one file. | Task T32 on the pilot repo | Add a rule locator that takes a line range. |
| A5 | Python 3.11 with the standard library is enough for the core. | Check at M1 | Add a dependency only with a written reason. |
| A-CAP | The runner can enforce RUN_CAP so one run never costs more (contract assumption). | Task T27 and gate G3.10, with a fake clock; the live gates check spend | If the agent's own budget flag does not stop a run, rely on the wall-clock limit alone and lower RUN_CAP. |

## Honest limits of this scope
- The evidence is two rules, toy and natural tasks written by us, mostly haiku.
- Decisions are advice. `DeleteCandidate` means "not measurable at this n". It does
  not mean "no effect".
- A guard test says nothing about real-world bypass beyond the channels it counts
  (see CI-16 for the open definition).
- The TLA+ model is bounded and uses smaller constants than the product.
