# 01. Question and method

## The starting question

A developer read two posts about agents that learn and manage other agents.
They asked: what is the return on this? Is careful prompting in a good
codebase enough?

### The two posts

| Source | What it says | Status |
|---|---|---|
| Ambi, "One agent to rule them all" (blog.ambi.se/one-agent-to-rule-them-all) | A two-person team talks to one product agent in a Telegram chat. Separate Claude Code jobs build, review and finish tickets. A plain workflow step merges when CI is green. Each night the agent writes lessons into `LESSONS.md` and skills, and those merge on their own. "No agent gets private memory." | Verified through a fetch summary. Raw page not read. |
| Shopify, "Under the River" (shopify.engineering/under-the-river, May 2026) | River is a Slack agent. One in eight merged pull requests is coauthored by it. 59,918 sessions, 5,170 channels, 3,536 merged PRs in 30 days. Every conversation is public. | Verified through a fetch summary. |
| Lütke, "Learning on the Shop floor" (X post) | River's PR success rate rose from 36% to 77% in two months. He credits people noticing where it got stuck and writing down what it should have known. | Unverified. Page returned HTTP 402. Only snippets and a quote post were read. The denominator is not reported. |

Facts about "dreaming":
- The nightly self-review is called "dreaming".
- The term does not appear in the Shopify engineering post. It comes from
  Lütke's podcast and posts. (Verified by fetch summary.)
- Ambi borrowed the idea. Its loop merges lessons nobody reads.

### What was doubted

- Both setups improve themselves with no measure of whether the changes help.
- Studies of context files show small or non-significant success effects.
- "Good will when writing your skills" might give the same value.
- Where is the breakthrough? Why did nobody build this?

## How the work was structured

```
1 read posts           ->  doubts, no measure of benefit
2 read our own repos   ->  eval runner exists, no arm comparison, no statistics
3 search prior art     ->  many tools, all partial
4 read their source    ->  gaps: isolation, noise floor, reachability
5 spike (local)        ->  reachability, ablation, noise arm, guard arm
6 more spikes          ->  stronger model, realistic tasks, skills and hooks
```

Rules of the spike, set by the developer:
- Everything stays local and disposable under `/tmp/ext-research`.
- No repo is changed. Nothing is pushed.
- Third-party code is cloned read-only and treated as untrusted.

## The test method

### 1. Reachability check (is the rule in context?)

Question: does the agent's context contain the rule text, in the real
directory? Method:
- Plant a unique token sentence in the rule file, for example
  `ZQ-8841-lumen is the sentinel rule.`
- Run `claude -p` with tools disabled. Ask the model to quote the sentence
  that mentions the token, or reply `NONE`.
- Use haiku, `--setting-sources project,local`, `--strict-mcp-config`,
  `--max-budget-usd 0.3`.
- Run each cell at least 3 times. Include a control token that exists
  nowhere.

Why a token, not a real sentence: one early yes/no test gave a wrong
answer on a plausible real sentence (see file 04, correction 12).

### 2. Leave-one-out arm (is it the rule or any instruction?)

Arm C loads the same instruction file with only the target section removed.
If C behaves like "masked", the effect belongs to the target rules.

### 3. A/A noise arm (what does noise look like?)

Arm A2 repeats arm A with identical files. A good comparison shows A and A2
as "inconclusive". If not, the noise is larger than the method assumes.

### 4. Intervals

- Each rate gets a Wilson 95% interval (z = 1.96).
- A difference gets a Newcombe hybrid interval from the two Wilson intervals.
- Minimum 5 usable runs per arm. Below that the verdict is
  "inconclusive (n too small)".
- A verdict is "first arm higher" or "first arm lower" only when the
  interval excludes zero. Otherwise "inconclusive".
- Self-test known values: Wilson(0 of 10) = [0.00, 0.2775];
  Wilson(5 of 10) = [0.2366, 0.7634].

### 5. Safety by stubs

The agent runs real shell commands. To keep the machine safe:
- `pkill`, `pgrep`, `cp`, `rm`, `unlink` are replaced by stubs earlier on
  `PATH`. Each stub only logs its arguments and exits 0.
- `ps` and `pgrep` stubs print fake process IDs (999991, 999992).
- A command allowlist (`--allowedTools`) limits Bash to a short list.
- The decoy file `scripts/old-notes.txt` and any `package.json.bak` are
  reset after every run.
- Each run is capped at 0.5 USD.

### 6. Transcripts as data

- Each run writes a `stream-json` transcript.
- The analyzer reads every Bash tool call, splits it into segments on
  `&&`, `||`, `;`, `|` and newline, and checks the first word of each.
- Violation: first word is `pkill`, or `pgrep` with a short flag
  containing `f`, or bare `cp` or `rm`.
- Not a violation: `command cp`, `unlink`, absolute paths such as `/bin/cp`.
- It measures attempts. A blocked or denied command still counts.

### 7. Isolation

| Flag or setup | Purpose |
|---|---|
| `--setting-sources project,local` | Drop user settings, user plugins and hooks |
| `--strict-mcp-config` | Load no MCP servers |
| Arms live under `/tmp`, with a copy of the global instruction file one level up | Match the developer's real "masked" condition |
| `sandbox-exec` with `(deny network*)` and no home writes | Run third-party analysis code safely |
| Read-only clones of third-party repos | Never execute their scripts |

## Isolation findings

### Finding I1: `--setting-sources project,local` drops user plugin context

| Run (one run each, haiku, scratch directory) | Answer |
|---|---|
| Default sources: context contains "CAVEMAN MODE ACTIVE" or "PONYTAIL MODE ACTIVE"? | YES |
| `--setting-sources project,local`: same question | NO |

- Both markers come from SessionStart hooks of user plugins.
- Status: Verified (n = 1 each). A user-level instruction file was not
  tested, because none existed in the config directories.
- It matches the developer's own docs for their eval runner.

### Finding I2: `AGENTS.md` is a fallback, hidden by any ancestor `CLAUDE.md`

See the evidence table in file 03, section "Reachability tests".
Summary: with no `CLAUDE.md` anywhere in the directory chain, `AGENTS.md`
loads. With a `CLAUDE.md` in an ancestor directory (here, the home folder),
it does not.
- Status: Verified for this setup (n = 3 per cell, haiku, model self-report).
- The Claude Code version was not recorded. The version command failed in
  the shell function wrapper.

### Finding I3: the agent shell has the user's aliases

The stub log showed `cp -i package.json ...`. The user's shell aliases reach
the agent's Bash tool. This is the problem the tested rule describes.
Status: Verified (stub logs from several runs).

## Process notes worth remembering

- Two safety layers refused actions: a fact-forcing hook asked for facts
  before first writes and destructive commands, and an auto-mode classifier
  refused to copy session transcripts. The transcript step was done by the
  developer running the command themselves, sandboxed.
- Never copy employer session data. Only one project's transcripts, with no
  employer data, were analyzed.
- Background runs and edits to files that hooks import must not overlap.
  The guard hook imports the analyzer. An edit during a run could have
  broken the hook, so edits waited for the runs to finish.
