# willitharness

Check whether the rules you write for a coding agent work.

You write rules in `CLAUDE.md`, `AGENTS.md`, skills and hooks. Do they load? Do they
change what the agent does? Would a script do better? `willitharness` answers four
questions for each rule and gives a decision: fix the loading, keep, replace with a
script, or delete candidate.

**Status: early. This is a spike turning into a v0.** Nothing here is released.
The plan, the formal models and the research notes are in this repo. The tool is
being built milestone by milestone (see `docs/plan/03-milestones-and-checkpoints.md`).

## The four questions
1. **Reachability.** Is the rule text in the agent's context, in the real directory?
2. **Effect.** Does the rule change the target behavior? Rule arm against a
   leave-one-out arm, with a noise arm and interval verdicts.
3. **Guard.** Would a script that blocks the command do as well?
4. **Side effects.** What else changed?

## How work lands (trunk-based development)
`main` is the trunk. Nobody commits on it. Work happens on a short-lived branch named
`type/slug` (`feat`, `fix`, `chore`, `docs`, `test`), at most 10 commits and 24 hours
old. `python3 scripts/guards/integrate.py` rebases the branch on `origin/main` and runs
`make check`. It keeps the branch and never moves local `main`. The hooks enforce this:
`scripts/guards/trunk.py`.

## Contributing flow
Remote `main` is protected. After `integrate.py` passes, run `git push origin <branch>`
and open a pull request. Write its body with `scripts/guards/pr_text.py --base origin/main
--facts <json>` and check it with `--check <body-file>`. The owner squash-merges on GitHub.
Then run `integrate.py --sync`. `--land-local` is not for publishing.

## Security
Report vulnerabilities privately; see `SECURITY.md`. `make security` audits the GitHub settings (needs network and an admin `gh` token; not part of `make check`).

## Data
`.willitharness/` stores run records, transcripts, calls logs, reachability, state and approvals.
Transcripts can hold your task text. Secret environment values are redacted from stored artifacts.
Git ignores the folder.
Delete everything with `rm -r .willitharness`. Delete one plan with `rm -r .willitharness/<plan>`.

## Checks
`make check` runs the tests, zanity, every mutation module, the trace gate, the repo checks, the simulation and the trace replay of the TLA+ model against the code. `make formal` runs the Lean and TLA+ gates. `make live` runs the real agent on the reachability fixtures (about a cent) and fails above $0.10.

## What is here
| Path | What |
|---|---|
| `docs/contract.md` | The domain contract. Every property has an ID. |
| `docs/plan/` | Scope, architecture, milestones, test strategy, task backlog. |
| `features/` | BDD scenarios, tagged with contract IDs. |
| `formal/tla/` | TLA+ model of the run lifecycle, with probes and mutants. |
| `formal/lean/` | Lean 4 proofs of the verdict and decision logic, and golden tables. |
| `docs/research/` | Findings and corrections from the spike. Read `04-findings-and-corrections.md`. |
| `docs/mistakes-to-rules.md` | Each mistake and the check that now rules out its category. |
| `src/willitharness/` | The Python package. |

## Limits of isolation
Effect runs use Claude's own sandbox and have no network. Guard runs use macOS `sandbox-exec` and their network is open. The Linux sandbox path is untested.
Run only plans you have read. Isolation is not a security boundary against a hostile plan.
The `claude` process itself is not confined.

## Honest limits
- Effect runs (Bash only) use Claude's own sandbox: Bash can write only in the run's workspace, scratch folder and calls log, cannot read `~/.ssh` and the other secret folders, and has no network. Guard runs (Bash, Write, Edit) use macOS `sandbox-exec`: writes and secret reads are denied and the network is open. The `claude` process itself is not confined in either kind. On Linux the Claude sandbox needs bubblewrap and socat; that path is untested.
- The spike used toy tasks, mostly one small model, stubbed commands and two rules.
- The formal part covers the verdict logic, the decision table and the run lifecycle
  (bounded). It does not cover agent behavior, shell parsing, the numeric interval
  code or the `claude` CLI.
- Other tools test parts of this (agent-skill-eval, deadrules, ruleproof, rulebench).
  See `docs/research/02-landscape-and-prior-art.md`.

## Working on it
```sh
uv sync
make check
git config core.hooksPath .githooks
```

### Push window rule
Pushes are allowed only from 18:00 to 08:59 local time. `.githooks/pre-push` refuses
a push outside that window, and a Claude Code hook in `.claude/settings.json` refuses
`git push` and `--no-verify` from an agent. Both call `scripts/guards/push_window.py`.
A git hook can be bypassed by someone who removes it, so treat the rule as a guard
for accidents, not as access control.

### Tools wired in
- **zanity** checks the code (`zanity.toml`). It runs in the pre-commit hook and in CI.
- **overwatch** runs the tests beside the agent and hands back regressions
  (`.overwatch.json`). It needs the overwatch plugin installed in Claude Code.

## License
MIT. See `LICENSE`.
