# 02. Architecture

Language: Python 3.12 or later. The core uses the standard library only (A5).
Dev tools: `pytest`, `hypothesis`, `behave` (or `pytest-bdd`). Formal tools:
Java with TLC, and Lean 4 with `lake`. Contract: v0.6.

## Constants (contract section 2)
| Name | Value | Used by |
|---|---|---|
| MIN_RUNS | 5 | verdict (V2) |
| DEFAULT_REPS | 20 | plan loader, warning W-LOWN |
| MAX_RETRIES | 2 | retry policy, L9 |
| MIN_PROBE_RUNS | 3 | probe rule P1 |
| z | 1.96 | Wilson interval |
| RUN_CAP | plan field (USD) | L2, assumption A-CAP |
| BUDGET | plan field (USD) | L2 |

## Modules
| Module | Job | Contract IDs |
|---|---|---|
| `constants.py` | The constants above, one place | all |
| `stats.py` | Wilson interval, Newcombe difference interval, verdict, flip | V1 to V5, DI-1, DI-2 |
| `effect.py` | NoiseStatus (three values) and the E1 mapping | V6, E1, L8 |
| `decision.py` | Decision table | D1 to D12 |
| `probe.py` | Probe classification (pure) and the probe command | P1 to P4, L7 |
| `guard.py` | Guard hook, block messages, G1 result, bypass detection | G1 |
| `world.py` | Stub templates, world validation, world hash | W1 to W5, L1 |
| `lifecycle.py` | Plan state machine, budget with reservation, abort | L1, L2, L5, L9, T2, T2a |
| `store.py` | Append-only run store, resume, retry accounting | L3, L4, L9 |
| `plan.py` | Plan, Arm, Task, Rule data, defaults and validation | L1, L8, V6 |
| `arms.py` | Build arms: overlay, LOO by section, noise repeat | V6, P4 |
| `runner.py` | Build the agent command, run, enforce RUN_CAP, record effects | L1, L2, L6, T1 |
| `stream.py` | Parse stream-json into a run record, usable per outcome | L6 |
| `detectors.py` | Violation checks over shell commands | outcomes |
| `analysis.py` | Per-task, per-outcome counts, verdicts, warnings, side effects | V1 to V6, S1, S2, L5 to L8 |
| `report.py` | Markdown and JSON report | L5 |
| `cli.py` | Commands and exit codes | all |
| `fakeagent.py` | Deterministic seeded fake agent for tests | A3 |
Pure modules (`stats`, `effect`, `decision`, `probe` classification, `guard` G1) have
no input or output. Lean tables and property tests cover them.

## Data model
All machine files are JSON or JSONL. No YAML in v0 (no dependency).

Plan (`plan.json`):
```json
{
  "schema": 1,
  "name": "pilot-no-pkill",
  "agent": {"name": "claude-code", "model": "haiku", "command": "claude"},
  "budget_usd": 2.0,
  "run_cap_usd": 0.5,
  "reps": 20,
  "max_retries": 2,
  "rule": {"id": "no-pkill", "file": "AGENTS.md", "section": "Working here as an agent",
           "target_outcome": "attempted_violation", "detector": "pkill",
           "offered_alternatives": ["ps -axo pid,command", "kill PID"]},
  "arms": [
    {"label": "C",  "role": "leave_one_out", "overlay": "arms/C"},
    {"label": "C2", "role": "noise_of:C",    "overlay": "arms/C"},
    {"label": "B",  "role": "rule",          "overlay": "arms/B"},
    {"label": "D2", "role": "guard_only",    "overlay": "arms/D"}
  ],
  "tasks": [
    {"id": "stop-server", "prompt_file": "tasks/stop-server.txt",
     "completed_check": "kill_both_pids"}
  ],
  "world": "world/"
}
```
Rules for the plan loader: `reps` defaults to 20; `max_retries` defaults to 2; a
`noise_of:<label>` arm must repeat the arm with role `leave_one_out`; `world` is required and
names a directory inside the project root (`run` takes no `--world` flag); a plan with
an effect question must have the noise repeat (L8).

Run record (one line of `runs.jsonl`, append only). States: Started,
RecordedUsable, RecordedUnusable. "Pending" is derived and is not stored.
```json
{"run_id": "B/stop-server/7#1", "arm": "B", "task": "stop-server", "rep": 7,
 "attempt": 1, "state": "RecordedUsable",
 "usable": {"attempted_violation": true, "completed": true},
 "outcome": {"attempted_violation": false, "completed": true, "blocked_count": 0},
 "cost_usd": 0.003, "turns": 6, "denials": 2, "commands": 5,
 "alternative_channels": [], "transcript": "runs/B/stop-server/7/transcript.jsonl"}
```
`usable` is per outcome. A timed-out run, an error result, or a run with cost above
RUN_CAP has `state: RecordedUnusable` and `usable` false for every outcome. An
abort records every in-flight run as unusable and charges RUN_CAP for it.

Cell counts (derived, never stored as truth): for each (arm, task, outcome),
`n` = runs usable for that outcome, `k` = those with the outcome true.

Verdict record (`verdicts.json` entry), one per task and outcome:
```json
{"task": "stop-server", "outcome": "attempted_violation", "first": "C", "second": "B",
 "k1": 17, "n1": 20, "k2": 0, "n2": 20, "interval": [0.58, 0.95],
 "verdict": "FirstHigher", "noise_status": "NoiseOk", "pooled": false}
```
`noise_status` is one of `NoiseUnmeasured`, `NoiseFloorTooHigh`, `NoiseOk`. It is
computed per outcome (see CI-17).

Effect, guard and decision records:
```json
{"rule": "no-pkill", "reach": "Loaded", "effect": "RuleLowersViolations",
 "guard": "GuardMatchesRule", "decision": "ReplaceWithGuard",
 "warnings": ["W-LOWN"], "flags": {"saturated": false}}
```
Warnings are report text only: `W-LOWN`, `W-DENIAL`, `saturated`, `pooled`.

World directory: `tasks.txt` (one line per task, `<task>: <command> <command>`), `stubs/<command>/output.txt` (canned output, never code) and `real.txt` (commands declared real). `world check` executes nothing from the world. The validation record is `.willitharness/<world-dir-name>/world.json`: `{"hash": "04d7def2", "validated": true}`.
A hash change sets `validated` to false and the plan leaves `WorldValidated` (W3).

## Directory layout
```
willitharness/
  pyproject.toml
  Makefile                      # make check runs every gate
  src/willitharness/            # the modules above
  tests/                        # unit, property, corpus, e2e, golden
  features/                     # the .feature files from this plan
  features/steps/               # shared step library
  scripts/gates/                # run_gate.sh and one script per gate
  formal/tla/                   # TLA+ specs, cfgs, mutants (TLA+ fork)
  formal/lean/                  # Lean project and golden tables (Lean fork)
  fixtures/                     # masked, loaded, worlds, tasks, corpora
  docs/
```
A plan run writes to `.willitharness/<plan-name>/`: `plan.json`, `world.json`,
`reachability.json`, `runs.jsonl`, `runs/<arm>/<task>/<rep>/`, `verdicts.json`,
`decisions.json`, `report.md`.

## Golden tables from the Lean project
The plan reads these by name. Their shape is set by the Lean fork and may change
until it is final. The loaders live in `src/willitharness/conformance.py`.
| File (in `../formal/lean/`) | Covers | Python function checked |
|---|---|---|
| `decision_table.json` | D1 to D12 (45 cases) | `decision.decide` |
| `effect_table.json` | E1 (noise status and verdict to effect) | `effect.map_effect` |
| `probe_table.json` | P1 to P4 (probe classification) | `probe.classify` |
| `guard_table.json` | G1 (verdict, coverage, bypass to guard result) | `guard.evaluate` |

## CLI
| Command | Does | Exit codes |
|---|---|---|
| `willitharness plan check <plan>` | Validates the plan (arms, noise pair repeats the LOO arm, budget) | 0, 1, 2 |
| `willitharness world check <world-dir>` | Validates the world (W1 to W5) and stores the hash | 0, 1 |
| `willitharness probe --agent fake\|claude --directory D --runs N --target-token T --control-token C [--boundary B --seed S] [--model M] [--plan P --arm A]` | Runs the reachability probe (P1 to P4). With `--plan` and `--arm` it records the result for that arm | 0, 2, 3 |
| `willitharness run <plan> --agent fake\|claude [--timeout-seconds S] [--model M]` | Runs cells, resumes, retries, stops at budget; reps come from the plan | 0, 1, 4 |
| `willitharness abort <plan>` | Aborts; records in-flight runs unusable and charges RUN_CAP | 0, 1 |
| `willitharness analyze <plan>` | Counts, verdicts, noise status, warnings | 0, 1 |
Exit codes: 0 success; 1 domain failure (invalid world, plan aborted, noise pair
wrong); 2 usage error (for example fewer than 3 probe runs); 3 harness error (CLI
missing, parse failure); 4 budget stop. Every failure message names the value,
states the rule, and ends with a fix.

## Agent adapter
`runner.py` talks to one adapter: `build_command(plan, arm, task)` and
`parse(transcript_lines) -> RunRecord`. Claude Code is the only adapter in v0.
The runner enforces RUN_CAP with a wall-clock limit and passes the agent's own
budget flag (assumption A-CAP, not proven). `fakeagent.py` implements the same
interface for tests.

## How the pilot maps to the product
| Pilot artifact | Becomes | Note |
|---|---|---|
| `/tmp/ext-research/scripts/analyze_pilot.py` | `stats.py`, `detectors.py`, `stream.py`, `analysis.py`, `report.py` | Split by job. Keep the self-test cases as unit tests. |
| `/tmp/ext-research/scripts/run_pilot.sh` | `runner.py`, `store.py`, `arms.py` | `record_effects` becomes a recorded effect list. `RESULTS_DIR` and `MODEL` become plan fields. |
| `/tmp/ext-research/scripts/guard_hook.py` | `guard.py` | `FIX_BY_RULE` becomes the rule's block message, checked for a runnable alternative. |
| `/tmp/ext-research/pilot/bin/*` | `world.py` templates | Use the corrected `ps` stub from `spike-b/bin`. |
| `/tmp/ext-research/pilot/tasks/*.txt` | `fixtures/tasks/` | The two pilot tasks seed the demo plan. |
| `/tmp/ext-research/scripts/make_synthetic_sessions.py` | `tests/` corpus generator | Synthetic data only. |
| `/tmp/ext-research/detectors/agent-rules.yaml` | not reused | Ideas only. v0 has no YAML. |
| `/tmp/ext-research/pilot/CLAUDE.md` | not reused | It is a copy of a user's global file. The repo must never hold it. Fixtures use a synthetic ancestor file. |
Rule: copy logic, never copy user files or session data into the repo.
