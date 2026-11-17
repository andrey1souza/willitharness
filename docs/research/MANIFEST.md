# MANIFEST

Everything lives under `/tmp/ext-research` (about 173 MB when written).
It is disposable. Delete it all with `rm -rf /tmp/ext-research`.
No repo was changed and nothing was pushed.

## Notes (this folder)

| File | Status |
|---|---|
| 00-README.md | Written |
| 01-question-and-method.md | Written |
| 02-landscape-and-prior-art.md | Written |
| 03-experiments.md | Written. Sections 3.5 (sonnet), 3.6 (spike B), 3.7 (spike C) are placeholders. |
| 04-findings-and-corrections.md | Written |
| 05-roi-and-power.md | Written |
| 06-open-questions-and-next-experiments.md | Written |
| 07-article-outline.md | Written |
| MANIFEST.md | This file |
| spike-b-realistic-tasks.md | Owned by another worker. Not written by this set. |
| spike-c-skills-hooks.md | Owned by another worker. Not written by this set. |

## Scripts and fixtures (our own code)

| Path | Purpose |
|---|---|
| `scripts/run_pilot.sh` | Runs `claude -p` per label, task and repetition. Env: `MODEL` (default haiku), `RESULTS_DIR`. Resumable. Resets decoy files after each run. |
| `scripts/analyze_pilot.py` | Reads transcripts. Computes attempts, Wilson and Newcombe intervals, completion, costs. Has `--self-test`. Env: `RESULTS_ROOT`. The guard hook imports it. Do not edit it while runs are active. |
| `scripts/guard_hook.py` | `PreToolUse` hook for the Bash tool. Blocks violating commands (exit 2). Writes `guard.log`. Holds the block messages. |
| `scripts/make_synthetic_sessions.py` | Writes 11 invented transcripts for detector validation. |
| `detectors/agent-rules.yaml` | Five custom detectors for ruleprobe (pkill, git-without-C, bare-cp-rm, no-preflight, force-push-phrase). |

## Pilot (`pilot/`)

| Path | Purpose |
|---|---|
| `pilot/arms/A` | Clone of the repo at HEAD `b6f551c`, no repo `CLAUDE.md`. Rules masked by the ancestor file. |
| `pilot/arms/B` | A plus `CLAUDE.md` with `@AGENTS.md`. |
| `pilot/arms/C` | B with the "Working here as an agent" section removed. |
| `pilot/arms/D` | A plus project hook settings (`.claude/settings.json`). |
| `pilot/arms/E` | B plus the same hook settings. |
| `pilot/CLAUDE.md` | Copy of the developer's global instruction file. It sits above the arms to reproduce the masking. |
| `pilot/bin/` | Stubs: `pkill`, `pgrep`, `cp`, `rm`, `unlink`, `ps`, `lsof`. Log and exit 0. |
| `pilot/tasks/` | Task text: `stop-server.txt` (final design), `backup-delete.txt`. |
| `pilot/results/` | 280 transcripts: labels A, A2, B, C, D, D2, E. Per run: `transcript.jsonl`, `stub.log`, `guard.log`, `fs.log`, `stderr.txt`. |
| `pilot/results-smoke/` | 3 transcripts from the dropped first design of stop-server. |
| `pilot/results-sonnet/` | Sonnet runs (arms A, B, D2). 60 transcripts at the time of writing. In progress. |
| `pilot/*.log` | Batch logs (`smoke`, `batch`, `batch2-*`, `batch3-*`, `batch4-D2`, `sonnet-*`). |

Notes:
- The arms contain a tracked hookify rule file under `.claude/`. It applies
  only if a hookify plugin is active. Isolation drops user plugins, so it
  should have no effect (Inferred, not tested).
- Each arm's `AGENTS.md` carries one planted sentence for reachability tests.

## Small test folders

| Path | Purpose |
|---|---|
| `htest/` | Controlled pair that shows an ancestor `CLAUDE.md` hides a child `AGENTS.md` (`parent/child` and `solo`). |
| `loadtest/` | First scratch test: `CLAUDE.md` and `AGENTS.md` in one folder. |
| `sentinel/` | Working folder for the plugin-isolation test. |
| `guardtest/` | Guard hook self-test log (`guard.log`, `err.txt`). |
| `synth/` | The 11 invented transcripts. |
| `run/` | Empty working folder used as cwd for the ruleprobe runs. |
| `transcripts-copy/` | Empty. The copy of real transcripts was refused, and not retried. |

## Third-party clones (UNTRUSTED, read-only, shallow, never run except one)

| Path | Repo |
|---|---|
| `ase/repo` | tardigrde/agent-skill-eval |
| `dsk/repo` | D0NO1/skill-eval |
| `cb/repo` | jchilcher-godaddy/claude-benchmark |
| `dr/repo` | lazizpapi/deadrules |
| `rp/repo` | h-a-forster/ruleproof |
| `pr1/repo` | JakeSelby/ruleprobe (the only one executed: sandboxed, no network, no home writes) |
| `pr2/repo` | moonrunnerkc/ruleprobe |
| `rb1/repo` | ralfyishere/rulebench |
| `rb2/repo` | treestar84/rulebench |
| `ivetts/repo` | devill/ivetts-skills |

Stray empty folders with spaces in their names (`dr lazizpapi`, `pr1 JakeSelby`,
`pr2 moonrunnerkc`, `rb1 ralfyishere`, `rb2 treestar84`, `rp h-a-forster`)
came from a failed first clone loop. They are harmless and can be deleted.

## How to rerun the analysis

```
python3 -B /tmp/ext-research/scripts/analyze_pilot.py --self-test
python3 -B /tmp/ext-research/scripts/analyze_pilot.py
RESULTS_ROOT=/tmp/ext-research/pilot/results-sonnet python3 -B /tmp/ext-research/scripts/analyze_pilot.py
```

The comparison lists inside the analyzer name fixed pairs of labels. For the
sonnet folder only the labels A, B and D2 exist, so only those pairs print.
