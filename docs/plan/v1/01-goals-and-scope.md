# 01. Goals and scope of v1

## The four goals
These are the owner's words.

| ID | Goal |
|---|---|
| G1 | For each thing audited (rule, hook, skill, plugin component), is it helping, or the same as just prompting? Unused and worthless components must be findable. |
| G2 | How to reduce the prose of what is audited. |
| G3 | Plug and play: "scan this repo, test every rule, give me a report". The front end is a Claude Code plugin with a skill. The free scan and report come first. Paid tests are a second, opt-in step that the user of the plugin pays for. The tool never writes to the audited repo. Changes appear only as proposals in the report. |
| G4 | README, GitHub Pages and all docs are always up to date. A bad doc is worse than none. Every doc claim is checked by a script against code or gate output. Delete what no script can check. Fix first the stale headers: the TLA+ README and the Lean README name old contract versions, and `check_lean.py` pins an old one. The contract is v0.7. |

## The known gap
The free audit reads instruction files only. A repo that ships a plugin, hooks or skills shows no rules.
Verified on 2026-11-25 with `uv run willitharness load-report ~/Develop/overwatch` and the same command on `~/Develop/zanity`.
Both reports list one file only: `~/CLAUDE.md`, marked "above the project". Neither repo has an instruction file.
Verified on the same day: the report for `~/Develop/gated-delivery` lists no skill, and that repo holds a plugin folder with skills.
The source says why. `src/willitharness/load_report.py` sets `NOT_COUNTED` to "plugin skills and user-level skills".
It reads skills from `.claude/skills` only. It reads hooks from `.claude/settings.json` only.
Git hooks in `.githooks` are never read (Verified: no `.githooks` string in `load_report.py`).

A second finding. `~/CLAUDE.md` is the only loaded file of both repos. It would count as the repo's own prose.
Task T90 must separate repo files from user-level files in every number.

## What v1 does
| Goal | v1 does | Task group |
|---|---|---|
| G1 | Lists every component with its size. Counts its use in Claude Code session transcripts. Finds unobserved and duplicate components. Runs the paid three-arm test only when the user opts in | T90 to T93, T99 |
| G2 | Reports prose cost per component. Proposes only deterministic cuts: delete a duplicate, point to a script | T92, T93 |
| G3 | One audit command, one plugin skill, a free report, a paid step with a required cap | T98 to T100 |
| G4 | Gates for headers, counts, file lists, command names, the Pages trigger | T85 to T89 |

## What v1 skips
| Item | Why | When to revisit |
|---|---|---|
| A model that rewrites prose | No script can check a rewrite. It breaks the G4 rule | Never in v1 |
| Applying a proposal | The tool never writes to the audited repo | Never. The user applies a diff by hand |
| Running a hook or a skill in the free scan | Repo hooks are code. The free scan runs no code of the repo | Only the existing flag `--run-hooks`, which stays off |
| Other agents than Claude Code | Transcript format and isolation flags are agent specific | After v1 |
| A usage signal for git hooks | No transcript event names a git hook (Inferred: the event list below has none) | If a log of git hook runs appears |
| Many models in one plan | Sonnet costs much more than haiku per run (`../06-risks.md`) | After v1 |
| A web UI | A Markdown report is enough | If users ask |

## The transcript format
Verified on 2026-11-25 by reading real sessions under `~/.claude/projects`. Every line is one JSON object.
Each session is one `.jsonl` file under a folder named after the working directory.
There are two roots on this machine: `~/.claude/projects` and `~/.claude-thoughtworks/projects`.
Together they hold thousands of session files and gigabytes of text. The reader must stream them.

| Event | Where it is | What it gives |
|---|---|---|
| Skill call | `type` assistant, `message.content[]` block `tool_use` with `name` Skill | `input.skill`, for example `gated-delivery:primer` |
| Agent call | Same, `name` Agent | `input.subagent_type` |
| Hook run | `type` attachment, `attachment.type` hook_success | `hookEvent`, `command`, `exitCode`, `durationMs` |
| Skills offered | `attachment.type` skill_listing | The list of skills the session could call |
| Slash command | `type` user, text holding `<command-name>/name</command-name>` | The command name |
| Working directory | `cwd` on user lines | Which repo the session ran in |

Inferred: a skill that appears in the listing and never in a call is "offered, not used".
Inferred: the event names can change with the Claude Code version. The reader must record the `version` field of each session.

## Success criteria
Each criterion is a statement that a script can check.

| Key | Statement | Checked by |
|---|---|---|
| K1 | On a fixture plugin repo, the inventory lists each hook, skill, agent and command. Each size equals the size from an independent count | Gate T90 |
| K2 | On fixture transcripts, each usage count equals the count of an independent reader | Gate T91 |
| K3 | The hash of every file and the file list of the audited folder stay equal through the audit | Gate T98 |
| K4 | The free audit spawns no process and opens no network connection. A test that spawns a process fails the audit | Gate T98 |
| K5 | The paid step refuses to start with no cap, and refuses a cap below its worst case. Both refusals happen before any spend | Gate T99 |
| K6 | A proposed change is a diff in the report. No command of the tool applies a diff | Gate T93 |
| K7 | Each stale header, count and file list that this plan names makes a docs gate fail on a seeded copy | Gates T85 to T89 |
| K8 | No gate is weakened and `zanity.toml` is untouched | Review of each diff |

## Scope in one sentence
The acceptance test of v1 is one command: given a repository folder, print a report of its components with size, use, duplicates and proposals, and change nothing.
