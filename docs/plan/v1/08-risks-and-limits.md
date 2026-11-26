# 08. Risks and limits of v1

Each risk has a mitigation or a stated limit. A limit is a risk that v1 accepts and says so in the report.
The v0 risks stay valid. They are in `../06-risks.md`.

## Validity risks
| ID | Risk | Evidence | Mitigation | Limit |
|---|---|---|---|---|
| R1 | A detector is wrong: duplicate, script-backed, masked or class | The audit story needed a fix to classify command bullets (Verified: the history of main holds a fix commit whose message says "classify command bullets") | Experiment EX5: the owner reads a sample of each class. A class below the bar leaves the report. Each report line carries its reason | The text of a rule is read by patterns. Only a behaviour test shows what an agent does |
| R2 | Auto-written worlds, tasks and detectors give a wrong paid result | v0 finding F19: a bad stub world invalidated runs (`../06-risks.md`) | The paid step runs world validation W1 to W5 first. It shows the world to the user before the opt-in. v1 writes no rule text | An auto-written task is a guess of the tool. The report says it was auto-written |
| R3 | A user-level file leaks into the result | Verified on 2026-11-25: `~/CLAUDE.md` is the only file loaded for overwatch and zanity. It also masks `AGENTS.md` in gated-delivery and commonsense | IN2 puts user-level files on a separate line. A prose total never includes them. A paid arm uses the pinned built-in skills of task T82 | A user-level file still decides what loads. The report says "masked by a user-level file" |
| R4 | A repo is untrusted. Its hooks are code and its skills are prompts | The v0 README says to run only plans you have read | The free scan reads text only and runs nothing (IN4, RO2). The report cuts quoted rule text to a short limit, as the audit command does. The plugin skill tells the agent to treat the report as data | A line of repo text could still steer the agent that reads the report. This is not fully closed |
| R5 | The paid step runs the agent on an untrusted repo | README, Limits of isolation. Effect runs use Claude's own sandbox. Guard runs use `sandbox-exec` on macOS. The Linux path is untested. The `claude` process itself is not confined | Proposed, not yet approved by the owner: the paid step refuses to start on a platform other than macOS. Inferred to be cheap to add | The `claude` process is not confined on any platform. Run only repos you have read |
| R6 | Usage is not value. A guard hook that works may never block, and a rare skill may matter | Inferred. A hook_success line shows a hook ran, not that it blocked | RC7 needs MIN_USAGE_SESSIONS sessions. The word is "unobserved". A guard hook never gets Remove from usage alone | The free report cannot say a component helps. Only the paid three-arm run does |
| R7 | The transcript format changes with Claude Code | Verified: each session line carries a `version` field | The reader records the version. Unknown event shapes are counted and shown. Fixtures hold one session per format | A format change can hide events until a fixture is added |
| R8 | Worktree copies count a component many times | Verified: overwatch has many folders under `.claude/worktrees`, each with a copy of its plugin files | IN1 skips `.claude/worktrees`. Sessions that ran in a worktree of the folder count for the folder | Inferred: how Claude Code names the folder of such a session is not checked yet. EX1 checks it |
| R9 | Transcripts hold private data | Verified: thousands of files on this machine. The v0 scope says transcripts hold private data (`../01-scope-v0.md`) | US3: the reader keeps names, counts and times. It copies no text. The report is local | Component names can reveal work. The report must not be posted without a read |
| R10 | The paid cap is an assumption | Contract A-CAP: the runner enforces RUN_CAP. v0 finding F7: spike B overspent its cap | SC2 and SC3. The TLA+ model checks the ledger. Each paid run prints its worst case first | A-CAP is not proven. The first paid runs print their real spend |
| R11 | The plan has dated numbers that go stale | An untagged count of files or sessions would go stale | A number stays only with a [param] or [check:name] tag. The plan gate (T89) fails on any other number | A [param] number is a decision, not a claim about the world |
| R12 | The spike is biased: the planted defects fit the simulator | Defects are written by the plan author | A real defect found counts above a planted one. A one-fault defect does not count (`04-simulation-spike.md`) | Five defects are a small sample |
| R13 | The loading model of Claude Code changes | The free report predicts loading from rules of a pinned version | The report prints the label "predicted, not verified; a paid probe confirms it". EX4 checks the prediction against stored probes | A new Claude Code version can break a prediction until EX4 runs again |
| R14 | One model per plan, and drift over time | v0 finding U11: sonnet costs much more than haiku | The report states the model. No cross-model claim | A result holds for that model and that date |

## What v1 does not claim
- It does not claim that a component helps from free signals. The free report predicts and counts.
- It does not claim that a rule is dead because an agent ignores it. The three-arm paid run measures that.
- It does not prove the code. TLA+ and Lean check logic only (contract section 9).
- It does not cover Codex or another agent.

## Stop conditions
| ID | Stop when | Then |
|---|---|---|
| STOP-V1 | EX1 shows the inventory misses a component kind in 2 or more of the 4 repos | Stop Part B. Revise the list of paths, then repeat EX1 [param] |
| STOP-V2 | EX5 fails for both classes | Stop T92 and T93. Keep the inventory and usage only |
| STOP-V3 | The spike (T97) is no-go | Delete the simulator. Continue with the gates |
| STOP-V4 | A paid run costs more than its worst case | Stop all paid work. Open a defect on the cap before any new run |

These names do not collide with STOP-1 to STOP-7 of v0 (`../06-risks.md`).
