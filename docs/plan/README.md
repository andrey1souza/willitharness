# willitharness: plan for v0

`willitharness` checks whether the rules you write for a coding agent work.
This folder holds the plan to build v0.

Source of truth: `../contract.md` (v0.6). Version v0.1 is kept as
`../contract-v0.1.md`. Every ID in this plan comes from the contract.
Do not edit the contract from here. Gaps are listed in `contract-issues.md`.

## Size of the plan
| Item | Count |
|---|---|
| Milestones | 8 (M0 to M7) |
| Total live cost cap | $2.00 |
| Contract issues | CI-01 to CI-18, all resolved (see `contract-issues.md`) |

## Reading order
| Order | File | What it answers |
|---|---|---|
| 1 | `01-scope-v0.md` | What v0 does, what it skips, and why |
| 2 | `02-architecture.md` | Constants, modules, data model, CLI, golden tables, pilot reuse |
| 3 | `features/*.feature` | The behavior, as BDD scenarios tagged with contract IDs |
| 4 | `03-milestones-and-checkpoints.md` | M0 to M7, with executable gates |
| 5 | `04-test-strategy.md` | Property tests, corpus, mutants, conformance, spend control |
| 6 | `05-traceability.md` | Every contract ID mapped to features, tests, TLA+, Lean |
| 7 | `06-risks.md` | Prior art, validity risks, limits, stop conditions |
| 8 | `07-task-backlog.md` | The ordered task list (BDD stories) |
| 9 | `contract-issues.md` | Status of every contract issue |

## Conventions
- IDs come from the contract. Stop conditions are named STOP-1 to STOP-7 so they
  never collide with contract IDs (S1 and S2 are side-effect rules).
- Tags: each scenario carries its IDs, for example `@V2 @D4`. Tag `@live` marks a
  scenario that spends money. Informational tags `@Q1`, `@Q3`, `@Q4` name the
  question.
- Gates: a gate is a command with an expected output. Names look like `G3.3`
  (milestone 3, gate 3).
- Gate pair: every gate has a good input that must pass and a bad input that must be
  rejected. A gate with no bad input does not count.
- Sizes: S under half a day, M about a day, L two or three days.
- Costs: caps use the measured haiku cost of $0.003 to $0.006 per small run
  (finding F7). Sonnet costs about 14 times more per run.

## Who owns what
| Area | Owner | Location |
|---|---|---|
| Plan, features, backlog | plan fork (this folder) | `plan/` |
| TLA+ specs and TLC runs | TLA+ fork | `../formal/tla/` |
| Lean proofs and golden tables (`decision_table.json`, `effect_table.json`, `probe_table.json`, `guard_table.json`) | Lean fork | `../formal/lean/` |
| Implementation | this repo | `src/willitharness/` |

## Honest limits
- The spike evidence is toy and natural tasks written by us, mostly haiku, two rules,
  stubbed commands.
- Formal methods cover the verdict logic, the effect and probe mappings, the guard
  result, the decision table and the run lifecycle. They do not cover agent
  behavior, shell parsing or the CLI (contract section 9). The TLA+ model uses
  smaller constants than the product.
- Three contract questions are open (bypass definition, noise status per outcome,
  the P4 failure row). The plan states its assumption for each.
