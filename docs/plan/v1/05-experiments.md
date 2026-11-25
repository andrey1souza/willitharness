# 05. Experiments on the owner repositories

Four repositories: gated-delivery, commonsense, overwatch and zanity. They sit under `~/Develop`.
Free experiments come first. Every paid run comes last, and the owner approves each one.

## Rules for all experiments
- The tool never writes to a repository under test (RO1). A paid step runs on a copy in a scratch folder outside the repository (RO4).
- Any change to gated-delivery stays local. This plan never plans a push to gated-delivery.
- A paid run costs at most its worst case: arms x reps x tasks x run cap, plus probes x probe cap. The formula comes from `scripts/gates/three_arm_live.sh`.
- Every experiment names what its result decides. An experiment that decides nothing is not run.

## Already measured
| Result | Where | What it says |
|---|---|---|
| Rule `pkill`, model haiku, live run G4.4 | `fixtures/results/g4_4.json` (row stop-server) | The file holds runs, hits and cost for the rule-removed arm and the rule-loaded arm. A test checks the README quote |
| gated-delivery `AGENTS.md`: the probe found it Masked. With `CLAUDE.md` holding `@AGENTS.md`, the probe found it Loaded | Unstored observation. The coordinator ran `willitharness probe` by hand. `probe` stores nothing without `--plan`. No result file exists | Inferred: the probe ran. Experiment EX4 stores it |
| commonsense `AGENTS.md`: the probe found it Masked | Same: unstored observation | Same |
| The free report for both repos | Verified on 2026-11-25 with `uv run willitharness load-report ~/Develop/gated-delivery` and the same for commonsense | Each prints "AGENTS.md: not loaded: masked by" the user-level `CLAUDE.md`. The static prediction agrees with the probes |

## Free experiments
| ID | Hypothesis | Cost | Pass criterion | What the result decides |
|---|---|---|---|---|
| EX1 | The inventory finds components in all four repos that the v0 audit misses | Free | For each repo, the inventory equals a hand list that the owner writes first. The hand list is committed before the run | Whether the fixed list of paths in IN1 is complete. Which hook formats exist (IN3) |
| EX2 | At least one gated-delivery skill has zero calls in the local sessions | Free | The count of each skill equals the count of an independent reader on 3 sampled sessions. The distribution of sessions per skill is printed | The value of MIN_USAGE_SESSIONS (US2) [param] |
| EX3 | Prose cost is dominated by a few components | Free | The report lists characters per component and the share of each source. The two user-level lines are apart | The size threshold for Shrink. Whether user-level files need their own section |
| EX4 | The static mask prediction equals the probe result | Free, if the three results are stored | Prediction equals result in every case: gated-delivery masked, gated-delivery with `@AGENTS.md`, commonsense masked | Whether the free scan may print "masked" with the word "predicted" only. It must keep the label |
| EX5 | The detectors for duplicate and script-backed rules are right | Free | The owner reads 10 flagged items of each class. Proposed bar: at least 9 of 10 are right in each class | Whether a class stays in the report or leaves it (risk R1 in `08-risks-and-limits.md`) [param] |
| EX6 | The audit of all four repos writes nothing and ends | Free | The hash of each repo tree is equal before and after. The seconds of each audit are printed | The time limit of the free audit. No limit is set before the first measure |

Notes on the free experiments:
- Verified on 2026-11-25 by a file walk: gated-delivery holds skills, agent files, command files and one hooks file in its plugin folder. EX1 lists them.
- Verified: its `hooks.json` runs `usage-log.mjs` after Skill, Bash, Task and Agent calls. EX2 can compare the transcript count with that log. Inferred: the log exists on disk. Check first.
- Verified: the hooks file of overwatch holds the key modules with one TypeScript path. It is not the Claude Code layout. EX1 tests IN3 on it.
- Verified: zanity has a pre-commit git hook and no instruction file. It has no usage signal in transcripts (Inferred: no transcript event names a git hook).
- Verified: overwatch has many folders under `.claude/worktrees`. Each holds a copy of its plugin files. IN1 skips that folder so the copies do not count many times.

## Paid experiments, last
None of these runs before the end of the plan. Each needs its own approval of the command and the worst case.
The model is haiku. A sonnet run costs much more (`../06-risks.md`). No sonnet run is planned.

| ID | Hypothesis | Command | Worst case |
|---|---|---|---|
| PX1 | Does the skill of the `pkill` case beat the same text as a plain prompt? This is task T71 of the v0 backlog | `bash scripts/gates/three_arm_live.sh --live --reps 20 --cap-usd 0.92 --model haiku --artifacts NAME` | 4 arms x 20 reps x 1 task x $0.01 = $0.80. Probes: 4 arms x 3 runs x $0.01 = $0.12. Total $0.92. [check:pkill-worst-case] The gate computes it from `fixtures/three-arm-pkill/plan/plan.json` |
| PX2 | Block messages differ in effect (task T75 of the v0 backlog) | The paid step of task T99 on the T75 plan | 3 arms x 20 reps x 1 task x $0.01 = $0.60. Probes: 3 arms x 3 runs x $0.01 = $0.09. Total $0.69. The parameters are proposed. T75 sets its own. [param] |
| PX3 | One command rule of gated-delivery, chosen from EX1 and EX5, is worth its prose. Arms N, N2, rule, guard | The paid step of task T99, on a copy of gated-delivery in a scratch folder | 4 arms x 20 reps x 1 task x $0.01 = $0.80. Probes: 4 arms x 3 runs x $0.01 = $0.12. Total $0.92. The parameters are proposed. [param] |
| PX4 | One command rule of commonsense, loaded through `@AGENTS.md` in a copy, lowers violations | Same, on a copy of commonsense | $0.92 with the same parameters. [param] |

The sum of the four worst cases is a ceiling. The paid step prints it before each approval, from the same formula.

Pass criteria and decisions of the paid runs:
| ID | Pass criterion | What the result decides |
|---|---|---|
| PX1 | `decide` prints one verdict for the case, with no refusal | Whether the three-arm path works end to end on a real skill |
| PX2 | The script prints completion counts per message, or `no difference` | Whether the block message text matters |
| PX3 | `decide` prints a decision. Noise status is NoiseOk | Whether the report may call the rule Keep, Remove or ReplaceByScript for that repo |
| PX4 | Same as PX3 | Whether the `@AGENTS.md` proposal helps the user of commonsense |

Not planned:
- Overwatch hooks. They are TypeScript modules in a registry, not command hooks. The paid hook test does not apply (Inferred). EX1 confirms the format first.
- Zanity git hooks. A git hook runs when the agent runs `git`. No v1 paid test measures it.

## What would change the plan
- EX4 fails in any case: the free scan drops the word "masked" and prints "unknown, probe needed".
- EX5 fails for a class: that class leaves the report until a better detector exists.
- EX2 shows every skill used: the unobserved class stays in the report but proposes nothing.
