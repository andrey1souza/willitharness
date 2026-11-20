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
old. `python3 scripts/guards/integrate.py` rebases the branch on `main`, runs
`make check`, fast-forwards `main` and deletes the branch, so the history stays
linear and `main` stays green. The hooks enforce this: `scripts/guards/trunk.py`.

## Security
Report vulnerabilities privately; see `SECURITY.md`. `make security` audits the GitHub settings (needs network and an admin `gh` token; not part of `make check`).

## Checks
`make check` runs the tests, zanity, every mutation module, the trace gate, the repo checks and the simulation. `make formal` runs the Lean and TLA+ gates. `make live` runs the real agent on the reachability fixtures (about a cent) and fails above $0.10.

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
Isolation uses macOS `sandbox-exec`. The network is not blocked. There is no sandbox on Linux.
Run only plans you have read. Isolation is not a security boundary against a hostile plan.
The `claude` process itself is not confined.

## Honest limits
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
