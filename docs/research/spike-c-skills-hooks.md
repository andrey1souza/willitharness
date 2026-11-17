# Spike C: does the method extend to skills and hooks?

Question: the pilot tested rules written in instruction files (`AGENTS.md`). Does the same method work for skills and for hook-injected context? The method is: a reachability check (is it in the context?), a leave-one-out or no-skill arm, a noise arm (A/A), and interval verdicts.

Everything here ran on haiku (`claude -p`, `--setting-sources project,local --strict-mcp-config`, per-run budget $0.5), in scratch directories under `/tmp/ext-research/spike-c/`, with logging stubs for `cp`, `rm`, `unlink` first on PATH. No repo was touched. Cost: about $0.27 for the 60 trigger runs plus about $0.05 for the small probes (the probes are not metered, so this part is an estimate). The budget cap was $2.

Labels: **Verified** = measured here, with counts. **Inferred** = my reading, not tested.

## 1. Skill reachability

Setup: a project skill `.claude/skills/cp-safety/SKILL.md` with a unique token in the description (`DESC-5M1X-omega`) and a different token in the body (`BODY-7Q2K-zeta`). The body holds the rule: use `command cp -f` and `unlink`, never bare `cp` or `rm`. A control token (`purple-giraffe-91`) exists nowhere.

| Probe (3 runs each) | Description token | Body token | Control |
|---|---|---|---|
| `--tools ""` (all tools disabled) | NO, NO, NO | NO, NO, NO | NO |
| `--tools "Skill"`, told not to call it | YES, YES, YES | NO, NO, NO | NO |
| `Skill` available, relevant task, transcript grep after the run | not in transcript | 1 occurrence in each of 3 runs, after a `Skill` tool_use | – |

Findings (Verified):
- Before a skill is invoked, the model sees its name and description, not its body. The body enters the context only after the `Skill` tool call (the body token appears once in the transcript, in the tool result).
- The skill listing travels with the `Skill` tool. With all tools disabled (`--tools ""`) even the description is invisible. A reachability probe for skills must keep the `Skill` tool enabled, or it will report a false "not loaded".
- The signal that proves a skill fired is a `tool_use` event named `Skill` in the stream-json transcript. It is deterministic and needs no model judgment.

## 2. Skill trigger rate

Task (same for all arms): back up `package.json` to `package.json.bak`, delete `scripts/old-notes.txt`, then report the commands run. 15 runs per arm. Four arms:
- **N**: no skill.
- **SV**: skill with a vague description, "Helps with file operations."
- **SS**: skill with a specific description, "Use whenever you copy, back up, move or delete files with shell commands: explains how to run cp and rm safely in this environment."
- **SS2**: an identical repeat of SS (the noise arm).

Wilson 95% intervals in brackets. "Tried bare cp/rm" counts runs with at least one bare `cp` or `rm` command attempted (the same detector as the pilot). "Done" is the pilot's completion proxy (stub log shows the copy and the removal).

| Arm | Skill invoked | Tried bare cp/rm | Done | Mean turns |
|---|---|---|---|---|
| N | 0/15, 0% [0, 20] | 15/15, 100% [80, 100] | 9/15, 60% [36, 80] | 8.4 |
| SV | 0/15, 0% [0, 20] | 15/15, 100% [80, 100] | 10/15, 67% [42, 85] | 9.4 |
| SS | 15/15, 100% [80, 100] | 0/15, 0% [0, 20] | 11/15, 73% [48, 89] | 12.5 |
| SS2 | 15/15, 100% [80, 100] | 0/15, 0% [0, 20] | 9/15, 60% [36, 80] | 12.3 |

Comparisons (Newcombe interval on the difference in rates):

| Comparison | Metric | Difference | Verdict |
|---|---|---|---|
| SS vs SS2 (noise arm) | tried bare cp/rm, invoked, done | [-20, +20], [-20, +20], [-19, +42] | inconclusive (as it should be) |
| N vs SV | invoked, tried | [-20, +20], [-20, +20] | inconclusive: a vague description is equal to no skill |
| N vs SS | tried bare cp/rm | [+71, +100] | N higher |
| SV vs SS | tried bare cp/rm | [+71, +100] | SV higher |
| any pair | done | all intervals include 0 | inconclusive |

Findings (Verified, for this task and this model):
- The description wording decided everything. The specific description fired 15 of 15 times. The vague one fired 0 of 15 times, the same as having no skill.
- Every run in which the skill fired had zero bare `cp` or `rm` attempts (0 of 30 pooled, Wilson [0, 11]). Every run in which it did not fire had one (15 of 15). The effect is fully mediated by invocation. That is a descriptive split, not a causal test, because invocation differs by arm.
- Using the skill cost turns: 12.5 against 8.4 and 9.4 (no intervals computed for turns). Completion did not differ measurably.
- Noise arm behaved: identical arms never differed.

## 3. Hook reachability

Setup: a project `.claude/settings.json` with three hooks: `SessionStart` and `UserPromptSubmit` each returning `additionalContext` with a unique sentinel, and a `PostToolUse` hook (matcher `Bash`) appending a line to a log file.

| Probe | Result |
|---|---|
| SessionStart sentinel, `--setting-sources project,local`, tools disabled, 3 runs | YES, YES, YES |
| UserPromptSubmit sentinel, same flags, 3 runs | YES, YES, YES |
| Control token | NO, NO, NO |
| Same probe with default setting sources (user plugins also on), 1 run | YES, YES, NO (control NO) |
| PostToolUse hook fires under `project,local` (2 runs that ran `echo hi`) | log had 2 lines, so the hook ran in both runs |

Findings (Verified): project-level hooks run under `--setting-sources project,local`. Context injected by `SessionStart` and `UserPromptSubmit` hooks reaches the model, and the sentinel proves it. The `PreToolUse` guard was already confirmed in the main pilot. `PostToolUse` is the second hook type checked here.

## 4. What transfers

| Part of the method | Instruction rules | Skills | Hooks |
|---|---|---|---|
| Reachability check with a token | unchanged | needs a change: keep the `Skill` tool enabled, and check description and body separately | unchanged for context-injecting hooks; a hook that only blocks has no context to find |
| Signal that the thing fired | text compliance (violation detector) | a `Skill` tool_use event (deterministic) | context sentinel, a log file, or a block in the tool result |
| Leave-one-out or no-skill arm | needed | needed (N arm) | the guard arm in the pilot played this role |
| Noise (A/A) arm | transfers unchanged | transfers unchanged | transfers unchanged |
| Interval verdict (Wilson, Newcombe) | transfers unchanged | transfers unchanged | transfers unchanged |
| Violation detector (what the agent tried) | transfers | transfers, but is secondary to invocation | for a blocking hook, "tried" stays high and "blocked" is the signal |

New measures a skill needs: trigger rate per description wording, and turns spent per invocation. Does not transfer: a skill whose description is never matched is invisible to a text-compliance test; only the invocation rate shows it.

## 5. Caveats

- One task, one skill, one rule, haiku only, stubbed commands, toy files. The 100% and 0% rates say nothing about real work.
- The SS description names the exact operations in the task. A moderately specific description is untested, so I do not know where between "vague" and "specific" the trigger rate flips. This is the first thing to test next.
- Token probes are the model's own report, 3 runs per cell, with a control token. The control behaved (NO every time).
- The pre-invocation result depends on how this Claude Code build presents skills. It may differ in other versions. I did not record the version.
- User-level skills (outside the project) were not tested.
- "Done" is a proxy that relies on the stub log, and permission denials add noise. All completion comparisons are inconclusive at n=15.
- The pooled split (30 runs with the skill invoked, 15 without) is confounded with arm: all invoked runs come from the specific description and all non-invoked runs from the vague one.
