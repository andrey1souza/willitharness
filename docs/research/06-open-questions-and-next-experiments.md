# 06. Open questions, next experiments, build-plan implications

## 1. What is still unknown

| # | Question | Why it matters | Where it is tracked |
|---|---|---|---|
| U1 | Do stronger models obey masked rules anyway (saturation)? ANSWERED for two rules: no. Sonnet 5.5 violated in 10 of 10 masked runs on both tasks. Still open for other rules and other models. | If yes, "this rule is dead" becomes the main result. | File 03 section 3.5 |
| U2 | How often do violations happen in natural, untempting tasks? ANSWERED for two rules on haiku: masked 98% when the task involves the commands, 0 of 60 when it does not. Toy tasks did not overstate the effect. Open: how often such tasks occur in real work. | Toy tasks may overstate the effect. | File 03 section 3.6, spike-b-realistic-tasks.md |
| U3 | Does the method work for skills and hooks, not only instruction files? PARTLY ANSWERED (haiku, one skill): noise arm and intervals transfer; skills need an invocation signal and the `Skill` tool on; context-injecting hooks pass a sentinel probe. Open: where a skill description's trigger rate flips, and user-level skills. | Most harness text is not in one file. | File 03 section 3.7, spike-c-skills-hooks.md |
| U4 | Do the same effects hold for the other three candidate rules (`git -C`, preflight first, two-full-runs limit)? | Two rules are a thin sample. The two-runs limit, and the "no process of yours still runs" rule, cannot be seen in a transcript. | Not started |
| U5 | Does the `AGENTS.md` fallback hold in other Claude Code versions and in other agents? | The finding may be version-bound. | Not started. Version was not recorded. |
| U6 | Does a user-level instruction file leak into runs under `--setting-sources project,local`? | Isolation claim is partial. | Not tested. No user-level file existed. |
| U7 | What did the `/bin/cp`-style commands do when allowed? | The allowlist hid bypass effects. | Not started |
| U8 | What do prose rules cost in tokens per session, against guard retries? | Needed for a real return estimate. | Not measured |
| U9 | Does paired analysis by task narrow the intervals? | Could cut run counts. | Not started |
| U10 | How well do results transfer across languages and project types? | Our repo is one TypeScript and Markdown project. | Not started |
| U11 | Are the A/A results stable across days and model updates? | Model drift can break comparisons. | Not started |
| U12 | Does anyone want this? | A spike cannot answer it. | Out of scope for now |

## 2. Candidate next experiments (ordered by decision value)

1. Read the sonnet results. Decide how much of the "masked rule" effect
   survives for a stronger model.
2. Read spike B and spike C. Decide whether realistic tasks and skills
   change the picture.
3. Repeat the guard test with the exact block message variants (bare "no",
   rule plus reason, rule plus fix) on one task. Question: which message
   parts matter?
4. Add a no-allowlist variant in a throwaway container, so bypass paths
   run for real. Question: what do bypasses do?
5. Add the other rules, using scenarios built from the repo's own mistake
   log. Question: do results hold across rules?
6. Add a filler-control arm of equal length, not only leave-one-out.
   Question: does length alone matter?
7. Record the Claude Code version and test two versions.
8. Measure per-session token cost of the prose section.

## 3. Build-plan implications

### What a first version could contain

| Part | Why |
|---|---|
| Reachability check for a rule file, in the real directory | Strongest and cheapest result. No other tool found with it. |
| Leave-one-out arm per rule | Separates the rule from "any instruction". |
| A/A noise arm and an "inconclusive" verdict with a minimum n | Prevents false claims. |
| Per-run completion metric and cost report, from stream-json | Needed to see side effects of guards. |
| Safety pattern: stubs, allowlist, per-run cap, scratch directories | Makes runs safe on a developer machine. |
| Guard-message test: block message variants compared on completion | The one result no other tool tests. |
| Deterministic checks only for grading | No judge, no judge noise. |
| Python, standard library only, with self-tests | Matches the ecosystem. Not final. |

### What a first version should leave out

| Part | Why |
|---|---|
| A general benchmark or leaderboard | Crowded, and effects are small at general level. |
| An LLM judge | Adds noise and cost before the noise of the checks is known. |
| Auto-written lessons that merge themselves | Evidence says LLM-written context can cost more with no gain. |
| A facts store with staleness checks | Unproven. Revisit after real-task results. |
| A TLA+ model | Valuable for the verdict logic, but only after the runner exists. |
| Support for many agents | One adapter first. A second to prove the interface. |

### Design rules carried over from the session
- Every check must be shown to fail on a bad case (the "check that cannot
  fail proves nothing" rule).
- Counts and intervals, not single runs.
- Report attempts and executions separately.
- Treat third-party code as untrusted: clone read-only, sandbox, no network.
- Keep arms as overlay directories. The tool does not need to understand
  the files in them.

### Decision gates
1. If the sonnet run shows saturation for strong models: reposition the work
   as a pruning tool, not an enforcement tool.
2. If realistic tasks show near-zero natural violation: a tempting-task
   mode needs a clear label, or scenarios must come from real mistake logs.
3. If skills and hooks need a different method: split the scope.
4. If the reachability finding does not hold across versions: it still
   stands as a documented behavior, but the check must pin versions.

### Smallest publishable unit
The reachability finding plus its test could stand alone as a short note
or a small script. It needs version pinning (U5) first.
