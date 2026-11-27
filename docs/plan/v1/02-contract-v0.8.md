# 02. Contract version 0.8: proposed definitions

This file proposes the new definitions. The contract stays at v0.7 until a task adds an ID.

## The choice: keep the proposal here
Option A is a section marked "Proposed" in `../../contract.md`. Option B keeps the proposal in this folder.
Each implementing task then adds its IDs to the contract. This plan chooses option B.

Verified reasons, from `scripts/gates/trace_check.py` and `scripts/gates/docs_freshness.py`:
1. `trace_check.py` reads only the table in section 8 of the contract. An ID outside the table has no gate. It is an unchecked claim.
2. An ID inside the table needs a BDD tag, a test, and a Lean or TLA+ item. Missing items fail the gate.
3. The file `scripts/gates/trace_pending.json` can waive a missing item. Today it holds two entries, both renames. A waiver for every new ID is a standing exception. It weakens the gate.
4. `docs_freshness.py` compares each stated contract version with the title of the contract. A bump to 0.8 before the code exists makes the plan docs wrong.
5. Option B keeps every gate green: this folder holds no table row that the trace gate reads.

The cost of option B: the definitions sit in two places until each task lands. The plan gate of task T89 fails when an ID is in both places with different text.
Each implementing task moves its IDs from this file to the contract and deletes them here.

Contract version 0.8 is the version where all IDs below are in the contract. The bump is the last task of the contract work (T96).

## Terms
| Term | Meaning |
|---|---|
| Component | One file-backed thing that a session loads or runs. Kinds: rule, instruction file, hook, skill, agent, command |
| Plugin | A folder that holds components and a manifest. It is a container, not a component |
| Audited folder | The folder that the user names. The tool treats it as read-only |
| Free report | The report that needs no agent run and no money |
| Paid step | A run of the real agent that the user opts in to, with a cap |
| Proposal | A change shown as a diff or as text in the report. It is never applied |

## Proposed IDs
| ID | Statement |
|---|---|
| IN1 | The inventory lists every component under the audited folder from a fixed list of paths. It skips `.git`, `node_modules`, `.venv` and `.claude/worktrees` |
| IN2 | The size of a component is the number of characters of its file text. A hook counts its command text plus the text of each script it names inside the folder |
| IN3 | A hooks file that does not hold the Claude Code layout is listed as "unsupported format" with its size. It is never skipped without a line |
| IN4 | The inventory runs no code of the audited folder. It reads text only |
| US1 | The usage of a component is a count of events in session transcripts. Only sessions that ran inside the audited folder count. The count has a first time, a last time and a session count |
| US2 | A component with zero events is "unobserved". It is "unused" only when the sessions read reach MIN_USAGE_SESSIONS. The report prints the session count beside the word |
| US3 | The usage reader keeps names, counts and times. It keeps no message text |
| US4 | A line that cannot be read counts as an unreadable line in the report. It does not stop the audit |
| RD1 | Static redundancy has two classes. A duplicate is a sentence that is equal, after trimming and lower-casing, in two components. A script-backed rule names a script that exists in the folder |
| RD2 | "The same as prompting" is a measured claim. Only a paid three-arm run (TA1 to TA8) may state it. The free report never states it |
| PC1 | The prose cost of a component is its size in characters. The report splits always-loaded from on-demand |
| PC2 | The report shows the share of each source in the total prose cost, with user-level files in a separate line |
| PC3 | A prose proposal is one of two edits: delete a duplicate, or replace a script-backed rule with a pointer to its script. No other rewrite is proposed |
| RC1 | The recommendation is a total, deterministic function of usage, backing, duplicate and measured evidence. Table in `03-formal-model.md` |
| RC2 | A measured DeleteCandidate gives Remove |
| RC3 | A measured ReplaceWithPrompt gives Shrink |
| RC4 | A measured KeepComponent or InsuranceKeep gives Keep. A free signal never overrides a measurement |
| RC5 | A duplicate gives Shrink, when no measurement decides |
| RC6 | A script-backed rule gives ReplaceByScript, when no measurement decides and it is not a duplicate |
| RC7 | Unobserved usage with enough sessions gives Remove. Too few sessions or an unobservable kind gives Undecided |
| RC8 | Used, unique and not script-backed gives Keep. The report marks it "free signal, not measured" |
| RO1 | After the audit, the hash of every file and the file list of the audited folder equal their values before |
| RO2 | The free audit starts no process, opens no network connection and runs no code of the audited folder |
| RO3 | The tool offers no command that applies a proposal |
| RO4 | All state of the tool lives in an output folder outside the audited folder. The tool refuses an output folder inside it |
| SC1 | A paid step starts only with a cap that the user gave in the same command. There is no default cap and no cap in a config file |
| SC2 | The cap must be at least the worst case: arms x reps x tasks x run cap, plus probes. Otherwise the step refuses before any spend |
| SC3 | The recorded spend of all paid steps of one audit is at most the cap |
| SC4 | The free report is the same with or without a paid step. A paid result adds a section and changes no earlier line |
| SC5 | A run that is denied or times out is recorded as unusable. The audit still prints its report |
| SC6 | An opt-in covers one paid step. It does not carry to the next step or the next session |

Verified: the contract uses none of these prefixes today. A `grep -nE` over `../../contract.md` finds no IN, US, RD, PC, RC, RO or SC followed by a digit.

## Where each ID must appear when it enters the contract
| ID group | Where it must appear |
|---|---|
| IN1 to IN4, US1 to US4 | BDD features, tests |
| RD1, PC1 to PC3 | BDD features, tests |
| RD2 | BDD features |
| RC1 to RC8 | BDD features, tests, Lean theorems |
| RO1 to RO4 | BDD features, tests, TLA+ invariants |
| SC1 to SC6 | BDD features, tests, TLA+ invariants |

## Open assumptions
- MIN_USAGE_SESSIONS has no value. Experiment EX2 in `05-experiments.md` sets it from data. Until then US2 prints "unobserved" only.
- The size threshold for a Shrink of a used component has no value. Experiment EX3 sets it. Until then size ranks the report and does not enter the table.
- The cap rule SC2 uses the same formula as `scripts/gates/three_arm_live.sh`. Verified: that script prints "arms x reps x tasks x cap" and refuses a cap below the total.
