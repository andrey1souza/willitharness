# willitharness: plan for v1

`willitharness` v0 checks whether one rule that you write for a coding agent works.
v1 audits a whole harness: rules, hooks, skills, agents, commands and plugins.
This folder holds the plan to build v1. It is a proposal. No v1 code exists yet.

Source of truth: `../../contract.md` (v0.7). This plan proposes version 0.8 of the contract.
The proposal lives in `02-contract-v0.8.md`. It does not edit the contract.

## Base
The free audit command is built on the local branch `feat/audit-command` (backlog task T84).
Main has no audit command. Verified: `ls src/willitharness/audit.py` finds no file on this branch of main.
This plan builds on that branch. Task T84 must merge before task T85 starts.

## Size
This README keeps no count. A hand-kept count goes stale (rule of task T79).
The size is in the backlog: each task has a size S, M or L.
The paid spend is the sum of the worst cases in `05-experiments.md`. No paid run starts before the owner approves it.

## Reading order
| Order | File | What it answers |
|---|---|---|
| 1 | `01-goals-and-scope.md` | The four goals, what v1 does and skips, success criteria |
| 2 | `02-contract-v0.8.md` | The new definitions with proposed IDs |
| 3 | `03-formal-model.md` | The TLA+ model of the audit pipeline and the Lean tables |
| 4 | `04-simulation-spike.md` | A time-boxed spike on deterministic simulation, with go and no-go |
| 5 | `05-experiments.md` | Experiments on four real repositories, free first, paid last |
| 6 | `06-docs-always-true.md` | The rule that no doc claim goes stale, and the gates |
| 7 | `07-backlog.md` | The ordered task list |
| 8 | `08-risks-and-limits.md` | Validity risks, each with a mitigation or a stated limit |

## Conventions
- Each non-obvious claim carries a tag. Verified names the file or the command. Inferred means not checked.
- A proposed ID is not in the contract yet. The implementing task adds it to the contract in the same change.
- A path of a file that does not exist yet is written without code marks and ends with "(new)".
- Task IDs continue the backlog of `../07-task-backlog.md`. The last ID on main is T83. The audit story is T84 on its branch. v1 starts at T85.
- A gate has a good input that must pass and a bad input that must be rejected. A gate with no bad input does not count.
- Sizes: S under half a day, M about a day, L two or three days.
- Costs: a paid worst case is arms x reps x tasks x run cap, plus probes. The formula is the one of `scripts/gates/three_arm_live.sh`.

## Who decides
| Area | Decides |
|---|---|
| Goals G1 to G4 and the scope | The owner |
| Spike go or no-go | The numbers in `04-simulation-spike.md`, then the owner |
| Any paid run | The owner, one run at a time |
| Any push or remote write | The owner. This plan never plans one |

## Honest limits
- Every number about the owner repositories is a dated snapshot. It carries its command.
- The dossiers in the commonsense repository are evidence. A spike decides, not a dossier.
- The paid steps are not run. Their costs are worst cases from a formula, not measurements.
