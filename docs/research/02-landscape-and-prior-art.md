# 02. Landscape and prior art

Source of facts: our own reads, plus subagent reads of source code.
We ran no third-party tool except `ruleprobe` (Jake Selby), see file 03.
Dates are last-commit or changelog dates as reported by the readers.

## Capability table

Legend: yes = present, part = partial, no = absent, n/a = not relevant.

| Project | Tests a harness edit | Paired stats and interval | Noise floor and "inconclusive" | Proves checks can fail | Isolates user config | Facts store | Formal model | Gates auto-edits |
|---|---|---|---|---|---|---|---|---|
| gated-delivery | part | no | no | yes | yes | no | no | part |
| zanity | no | no | no | part | n/a | no | no | part |
| overwatch | no | part | no | yes | n/a | no | yes | part |
| agent-skill-eval (ASE) | part (skills only) | part | no | no | no | no | no | no |
| claude-benchmark | part (one file) | part | no | part | no | no | no | no |
| skill-eval (D0NO1) | no | no | no | no | no | no | no | no |
| dreaming loops (Ambi, agent-swarm, danwilsonai) | no | no | no | no | n/a | no | no | part |

Two columns are empty for everyone: noise floor with "inconclusive", and a
facts store. Status: Inferred from source reads. "No" means not found, not
proven absent.

## Our own repos

### gated-delivery (the developer's public repo)

- Plugin with skills for delivery flow, plus an eval runner and a large
  consistency guard. Status of reads: Verified (docs read by us, scripts
  read by a subagent).
- `docs/mistakes-to-rules.md`: 77 rows. Each row names a mistake, a rule
  and a test that can fail.
- Eval runner (`scripts/eval/run-scenarios.ts`, 732 lines): spawns
  `claude -p` per scenario, arm and repeat. The baseline arm is a separate
  invocation with no plugin. No script compares arms. The "skill wins 6 of 7"
  threshold is prose. Default repeat is 2. No variance, interval or
  significance test. Records cost and seconds, not turns or tokens. Judge
  cost is not counted.
- Strengths: `--setting-sources project,local` isolation, a corpus that
  proves checks can fail (good and bad outputs per check), format-variant
  replay, a rule inventory, a token budget, shrink-only baselines, a
  saturation table (scenarios that the no-skill baseline passes are retired,
  dated 2026-10-19).
- Coupling: `ROOT = process.cwd()`, the arm is "whole `plugin/`", and the
  path `plugin/skills/<skill>/evals.md` is fixed. It cannot take an arbitrary
  harness diff.
- Own admissions (docs): "A live stamp is a sample", "No property tests and
  no simulation", "The Bash guard is an accident guard. Indirection defeats
  it."
- Cost note: its docs say a smoke session costs about 0.1 to 0.7 USD. Our
  small tasks cost 0.003 to 0.006 USD. See file 05.

### zanity (Zig linter for agents)

- Tree-sitter, 9 languages. `--agent` output is about 1% of the terminal
  bytes: fix text once per rule, a cap of 10 findings, the exact next command.
- The text "never suppress the finding, disable its rule or exclude its path"
  is pinned by a golden test (`src/report_agent.zig`).
- Baseline ids are SHA-256 over path, rule, trimmed anchor line and ordinal.
  Line numbers are excluded. `bench/parity/ratchet.py` fails on a loss and
  also on an unrecorded gain.
- `relaxed-check` flags `eslint-disable`, `|| true`, `continue-on-error` and
  similar. It could serve as an outcome oracle.
- No A/B runner, no task capture, no TLA+. Status: Verified (subagent read).

### overwatch (watchers and formal models for agents)

- Runs test watchers beside coding agents and returns only regressions.
- TLA+ specs: `FailurePolicy`, `Overwatch` (274 lines), `IntegrationContract`
  (345 lines), `IntegrationLifecycle`. Not a refinement proof of the code
  (`spec/README.md`).
- Trace validation: the real engine runs under seeded random environments.
  TLC checks that the log is a behavior of the model.
- Vacuity lesson (commit f059d17): a permissive model let an engine that
  timed out every check pass all 40 traces. The fix allowed timeouts only
  where the harness made a check hang.
- Probes (13) prove that a property's scenario is reachable. Mutants are
  mentioned once in prose. We said "mutant discipline" earlier. That was
  too strong.
- TCR (test, commit or revert) lives on unmerged branches. Limits are
  listed in the repo (single writer, base64 secrets unseen).
- `scripts/timing.py` fits a lognormal to edit gaps and simulates. It is the
  only variance-aware code, and it sizes the product, not harness changes.
- Full model run takes about 9 minutes and 10 GB, so CI skips it.

### An earlier private team plugin (lineage of gated-delivery)

- Shape of its per-ticket `learnings.md`: bold claim, then evidence (paths,
  commit hashes, dashboard ids). About 9 of 47 bullets carry an ISO date.
  No structured date, scope or status. No entry is marked stale. Nothing
  reads these files in code. Status: Verified by a subagent. Employer
  details are not kept in these notes.
- Its `learn-flow` routes lessons by scope. gated-delivery's version puts a
  deterministic check first and demands a failing example.

## Evaluation tools (read by subagents, not run)

### agent-skill-eval (ASE, tardigrde)

- Python, MIT, v0.14.0, changelog dated 2026-11-16, 23 test files, very
  active. `cli.py` is 3,886 lines.
- Fresh git workspace per case, agent, arm and run. Agents: Claude Code,
  OpenCode, Codex, fake.
- An arm is a boolean `with_skill`. Only skills can be installed. Its roadmap
  item 5, "agent configuration variants as the comparison unit", is the
  largest planned change.
- Statistics: pass@k, pass^k, Wilson interval, a bootstrap of per-case
  deltas against a stored baseline (not with versus without). The
  with/without delta has no interval. No A/A. No "inconclusive". No minimum n.
- Claude path runs on the host with `--dangerously-skip-permissions`. We
  found no `HOME` isolation, so user config can leak into both arms.
- Claude output gives no turn count and no tool-call list.
- Our search snippet claimed a bootstrap on the comparison. The source
  shows otherwise (correction 4 in file 04).

### skill-eval (D0NO1)

- About 1,000 lines. No arm concept. The "baseline" is the previous stored
  run of the same suite. One run per case. Letter grades. Treat as a toy.

### claude-benchmark (jchilcher-godaddy)

- Python, Apache-2.0. A profile is one markdown file copied to the run's
  `CLAUDE.md` and also appended to the system prompt.
- Most of its 21 experiments use `--direct-api`: no `CLAUDE.md`, no tools,
  no agent loop. They measure prompt text, not the harness.
- 48 synthetic single-file tasks. Composite score is half LLM-judged by a
  same-family judge. No A/A. Changelog has one entry, 2025-02-28.
- The headline "1,188 runs, 10 profiles, none beat empty" does not appear
  in the repo. The repo corpus is about 212K to 233K runs.
- Its own corrections teach pitfalls: baseline ceilings, cross-language
  prompt contamination, in-family judges, unpaired tests on nested data.

## Rule-testing tools (read by subagents, not run, except where noted)

| Tool | What it does | Notable facts | Security note |
|---|---|---|---|
| deadrules (lazizpapi, TS) | Leave-one-out ablation of `CLAUDE.md` sections through `claude -p`. Verdicts: load-bearing, dead, harmful, unclear. | Wilson plus Newcombe intervals, minimum n guard. About 2.4k lines, one commit (2026-08-17). Records cost and final text only, no tool calls. Demo: 60 runs for 1.51 USD. No A/A. | `bypassPermissions`. Likely partial isolation. |
| ruleproof (h-a-forster, Python) | Deterministic checks over a git diff and a session transcript. A separate bench. | Strongest isolation flags: `claudeMdExcludes`, settings sources, ancestor-file assertion. Own results: nothing significant (p = 0.125, p = 0.08). Only 3.2% of 1,960 real directives compiled to checks. About 14k lines, one commit (2026-11-13). | No network code found. Bench uses bypass permissions. |
| ruleprobe (JakeSelby, Python) | Runs deterministic detectors over past transcripts. Counts hits and "unobserved" detectors. | Standard library only. Alpha. One commit (2026-10-12). Authors warn zero hits is not proof of no effect. | No network or subprocess in the package (grep). We ran it sandboxed. |
| ruleprobe (moonrunnerkc, TS) | Turns instruction files into ESLint config, checks drift. | Not related to behavior change. | Executes the project's own ESLint config code. Avoid on untrusted material. |
| rulebench (ralfyishere, Python) | Hand-written trap tests under rule bundles. LLM judge. | n = 3, same-family judge, no isolation. Its own 54-cell study did not replicate its headline. | `bypassPermissions`, real `~/.claude`. |
| rulebench (treestar84, TS) | Single-rule ablation against 30 tasks, filler control, hidden tests. | n = 150 per condition. Baseline 97.3% (146 of 150). Four "effective" rules were 4 failures against 0, including rules unrelated to the task. Pseudo-replication. No tests. 6,150 runs took 24 to 30 hours. | `--dangerously-skip-permissions`, no isolation. |
| build-project-review (devill, MIT) | Builds a repo-local code-review skill from review history. | Quote-provenance verifier is reusable. Pass 1 (no principles) versus pass 2 is a single sample. No A/B, no reachability. | `gh` calls, indirect prompt-injection surface. |

Our own run of `ruleprobe` (Jake Selby): file 03.

## Papers and talks

| Source | Key facts | Status |
|---|---|---|
| Newcombe et al., "How Amazon Web Services Uses Formal Methods" (CACM, April 2015) | TLA+ used on 10 large systems. Found bugs no other technique found, such as a 35-step DynamoDB failure trace. "How do we know that the executable code correctly implements the verified design? The answer is we do not know." Models can miss performance degradation. | Verified (PDF read). |
| Gloaguen et al., "Evaluating AGENTS.md" (arXiv 2602.11988) | SWE-bench Lite (300 tasks) and AGENTbench/CTXbench (138 instances). One sample per condition. LLM-written files: resolution -0.5% (p = 0.87) and -2% (p = 0.37), steps +2.45 and +3.92, cost +20% and +23% (p < 0.001%). Developer-written: +2.4% (p = 0.21), LLM versus developer p = 0.038, cost up to +19%. Removing all other docs made LLM files help by +2.7%. Python only. | Verified (paper fetched, 3,165 of 103,165 characters not read). |
| Lulla et al. (arXiv 2601.20404) | 10 repos, 124 PRs, paired runs. Median runtime -28.64%, output tokens -16.58%, comparable completion. | Unverified (snippet). |
| Khatri (arXiv 2607.27250) | 17 tasks, 3 repos, 288 runs. Injection strategy did not change correctness. | Unverified (snippet). |
| DeltaSelect; "What Does a Harness Buy? Tokens, Mostly" | A small fixed task set overfits. Rerunning the same configuration changes as many outcomes as swapping a harness. | Unverified (snippets). |
| Lauren Tan, "All Code Is Slop (Except Mine)" (ai.engineer talk page) | "your codebase is kind of like a garden." Corrections belong in the codebase and executable checks, not in `AGENTS.md`. A recap names a "gardener" role. Her team shipped about 3,000 of 11,000 PRs, about 0.5% reverted, with no baseline. | Partly verified: the talk page and recaps by subagent. The video had no readable transcript. The numbers are self-reported. |
| Shopify River, Ambi, Lütke | See file 01. | Mixed. |
| danwilsonai/dreaming | Scheduled review of agent sessions that proposes the smallest fix, often a deletion. Approval gates. Ships a spec, not code. No outcome test. One setup. 0 stars. | Verified (README read). |
| agent-swarm.dev, "How we got to 60% deterministic dreaming" | 415 changes in 28 nights, per-lane caps, about 65% of proposals rejected, 26 of 41 workflow nodes use no model. Instruction tokens fell from about 61.9k to 32.0k. Its own simulations credit dreaming with 25 to 40% of the gains. | Verified (page fetched). Self-reported, one system. |

## Gap summary

Not found anywhere in what we read:
1. A reachability check ("is the rule in context, in the real directory?").
2. An A/A noise arm with an "inconclusive" verdict.
3. A test of the block message of a guard.
4. A facts store with dates, sources and staleness checks.
5. A/B for hooks, not only skills and instruction files.

Status: Inferred from reads and searches. Search was not exhaustive.
We were wrong about novelty twice before (file 04, corrections 1 and 14).
