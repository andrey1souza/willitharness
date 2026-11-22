# willitharness

Check whether the rules you write for a coding agent work.

You write rules in `CLAUDE.md`, `AGENTS.md`, skills and hooks. Do they load? Do they
change what the agent does? Would a script do better? `willitharness` answers four
questions for each rule and gives a decision: fix the loading, keep, replace with a
script, or delete candidate.

## Status
**Early. This is a spike turning into a v0.** Nothing here is released.
The plan, the formal models and the research notes are in this repo. The tool is
being built milestone by milestone (see `docs/plan/03-milestones-and-checkpoints.md`).
A planned feature shows the id of its task in `docs/plan/07-task-backlog.md`.

## What works today
| Command | What it does | Status |
|---|---|---|
| `willitharness plan check <plan.json>` | Checks that a plan file is valid. | works |
| `willitharness world check <world-dir>` | Checks a world folder and prints its hash. | works |
| `willitharness probe` | Runs an agent and records whether the rule text reached it. With `--plan` and `--arm`, it records the result for one arm of a plan. | works |
| `willitharness run <plan.json>` | Runs every arm of a plan within its budget. | works |
| `willitharness abort <plan.json>` | Marks a plan as aborted. | works |
| `willitharness analyze <plan.json>` | Gives a verdict for a plan that has a `leave_one_out` arm and a `rule` arm. | works |
| `willitharness decide` | Turns the verdicts into a decision. | not built (T43) |
| The report | Shows the decision and its evidence. | not built (T45) |
| Comparing a skill or hook with the same text as a plain prompt | Tests whether the form matters, not only the text. | not built (T67) |

The `claude` agent runs real sessions and costs money. The `fake` agent runs offline and costs nothing.

## Try it offline
The fake agent proves the plumbing. It measures nothing about a real agent.
The example folder `examples/offline-demo/` holds a plan, a world and a `work` folder with a rule file.

Install the tool and copy the example. Run the commands in the copy.
```sh
uv sync
source .venv/bin/activate
cp -R examples/offline-demo /tmp/offline-demo
cd /tmp/offline-demo
```

Check the plan and the world.
```sh
willitharness plan check plan.json
willitharness world check world
```
Output:
```
plan ok: demo (2 arms, 2 reps)
world: valid (hash ac7541d4)
```

Probe each arm. A probe records that the rule text reached the agent.
```sh
willitharness probe --agent fake --directory work --boundary work --runs 3 --seed 3 --target-token ZQ-8841-lumen --control-token purple-giraffe-91 --plan plan.json --arm A
willitharness probe --agent fake --directory work --boundary work --runs 3 --seed 3 --target-token ZQ-8841-lumen --control-token purple-giraffe-91 --plan plan.json --arm B
```
Output for arm A:
```
reachability: Loaded
the target token appeared in 3 of 3 runs
cost: $0.0000
recorded: arm A is Loaded in plan demo; plan state WorldValidated
```

Run the plan.
```sh
willitharness run plan.json --agent fake
```
Output:
```
plan Complete: 8 runs, spent $0.04
```

The command `willitharness analyze plan.json` refuses on this demo plan. The plan has no `leave_one_out` arm and its two arms have the role `rule`. A real plan needs one arm of each role.
The test `tests/gates/test_readme_quick_start.py` runs these commands and fails when they go stale.

## The four questions
1. **Reachability.** Is the rule text in the agent's context, in the real directory?
2. **Effect.** Does the rule change the target behavior? Rule arm against a
   leave-one-out arm, with a noise arm and interval verdicts.
3. **Guard.** Would a script that blocks the command do as well?
4. **Side effects.** What else changed?

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

## For contributors
Every section from here to the license is for contributors.

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

## Working on it
```sh
uv sync
make check
git config core.hooksPath .githooks
```

### Tools wired in
- **zanity** checks the code (`zanity.toml`). It runs in the pre-commit hook and in CI.
- **overwatch** runs the tests beside the agent and hands back regressions
  (`.overwatch.json`). It needs the overwatch plugin installed in Claude Code.

## License
MIT. See `LICENSE`.
