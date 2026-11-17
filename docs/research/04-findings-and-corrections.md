# 04. Findings and corrections

## Part 1. Findings ranked by evidence strength

Strength scale: A = measured by us with controls and enough runs.
B = measured by us, small n or one setup. C = read in a source by us.
D = reported by a subagent or a snippet. E = inferred.

| # | Finding | Strength | Basis |
|---|---|---|---|
| F1 | A rule file can silently not load. In our setup, `AGENTS.md` is a fallback that any ancestor `CLAUDE.md` hides. | B | File 03, 3.1. n = 3 per cell, haiku, model self-report, version not recorded. |
| F2 | Masked rules had no effect on behavior: arms A, A2 and C were alike. | A | File 03, 3.4. n = 20 per cell. |
| F3 | Loaded target rules changed behavior in toy tasks. pkill attempts fell from 83% (pooled controls) to 0 of 20. cp/rm attempts fell from 100% to 60%. | A for this toy setup | The leave-one-out arm C separates "the rule" from "any instruction". |
| F4 | A guard that blocks needs a block message with a working alternative. Old message: 5 of 20 tasks completed. New message: 20 of 20. | A for this setup | D against D2, n = 20. Five failing runs read by hand. |
| F5 | A guard changes what runs, not what the agent tries. | A | Arm D tried as often as arm A. |
| F6 | An identical-config noise arm showed no false difference at n = 20. At n = 5 it wobbled. | A | A against A2. |
| F7 | Small tasks cost 0.003 to 0.006 USD per run on haiku. | A | 280 runs, 1.07 USD. |
| F8 | Zero hits in a transcript is ambiguous. | C | ruleprobe: `no-verify` 0 of 1,314 sessions, and the authors say so. |
| F9 | Context-file effects on success are small and often not significant. Cost effects are larger and not consistent across studies. | C for Gloaguen, D for others | See file 05. |
| F10 | Prior art for rule testing is broad. Pieces we thought unique exist in small repos. | D | Subagent reads of source. |
| F11 | The reachability check, the noise arm with an "inconclusive" verdict, and a guard-message test were not found in any tool we read. | E | Absence in reads. Search not exhaustive. |
| F12 | The real-session violation rates after 2026-11-10 are higher, which fits a masked rule. | E | Different populations, attempts only. Do not rely on it. |
| F13 | Models may follow many rules without being told (saturation). Not true for our two rules on sonnet 5.5: masked, it violated in 10 of 10 runs on both tasks. | A for this toy setup (own run); D for the other repos' saturation data (baseline 97.3%, 15 of 15 rules followed by Sonnet 5.5 with both file sizes) | File 03, 3.5. Saturation is rule-specific and task-specific. Do not generalize either way. |
| F14 | Loaded rules work better on sonnet 5.5 than on haiku: cp/rm attempts 2 of 10 (20%) against 12 of 20 (60%). | B | Different n and models, no cross-model interval. |
| F15 | A Bash guard can push a capable agent to another tool. In 4 of 10 sonnet guard-only runs the agent tried `Write` to create the backup file after `cp` was blocked (0 of 10 in the other sonnet arms). | B | Attempts only. The harness allowlist denied the `Write` calls. Whether the other channel meets the rule's intent depends on the rule. |
| F17 | The pilot effects hold on natural tasks. Masked: 98% (39/40) violating attempts on four rule-relevant tasks, 0/20 on neutral tasks. Loaded: 22% (9/40). | B | File 03, 3.6. Haiku, our own tasks, attempts only, pooled intervals ignore clustering. |
| F18 | Loading the rule file changes other behavior too. Arm B ran `git -C` in 22 of 60 runs, against 1 for A and 0 for D2. | B | Spike B note. A rule test should report side effects, not only the target behavior. |
| F19 | The harness can invalidate runs. The `ps` stub listed processes outside the checkout, so agents correctly refused to kill them. Three runs moved aside. | A (method caveat) | Found by reading runs. Check the stub world before trusting a task. |
| F16 | The "done" metric is a rough proxy. The permission allowlist denies chained commands, which hid completed work in every arm. Example: sonnet D2 run 3, where the guard logged `allow` and the allowlist then denied. | A (method caveat) | Read by hand. |

## Part 2. Corrections log

Each row is an error or overstatement by the assistant during the session,
what was true, how it was found, and the fix.

| # | What was said | What is true | Found by | Fix |
|---|---|---|---|---|
| 1 | "No tool covers the A/B gap." | ASE, claude-benchmark, skill-eval and several rule-testing repos cover parts of it. | Broader search, then source reads | Landscape rewritten (file 02). |
| 2 | "About 60% of the replay eval already exists in gated-delivery." | Runs and grading exist. No arm comparison and no statistics. The "wins 6 of 7" line is prose. | Subagent read of the runner source | Decision changed from "extend in place" to a separate small project. |
| 3 | Gloaguen: "context files lowered success; human files gave +4%." | Success changes were not significant: -0.5% (p = 0.87), -2% (p = 0.37), +2.4% (p = 0.21). Cost rose about 20% and was significant. | Paper fetched | Numbers corrected in files 02 and 05. |
| 4 | ASE puts a bootstrap interval on the with/without comparison. | The bootstrap compares baseline against current run. The with/without delta has no interval. | Source read | Corrected. |
| 5 | claude-benchmark: "1,188 runs, none beat an empty file." | The text is not in the repo. Its corpus is about 212K to 233K runs. | Repo search | Claim dropped. |
| 6 | Overwatch uses mutant testing. | It uses reachability probes. Mutants appear once in prose. | First-hand check by a subagent | Wording lowered. |
| 7 | The anti-suppression text lives in `src/report.zig`. | It lives in `src/report_agent.zig`. | First-hand check | Path corrected. |
| 8 | TLA+ can "test how the project behaves". | TLA+ checks a model of a design. Overwatch ties code to a model with trace validation. The AWS paper itself says code conformance is unknown. | Paper and overwatch read | Scope of TLA+ narrowed. Deferred for a first tool. |
| 9 | Build the new work inside gated-delivery. | gated-delivery's runner is tied to `plugin/skills/`. A separate small project is cleaner. | Coupling read | Separate project. |
| 10 | Use TypeScript. | Python fits the eval ecosystem and TLC tooling. | Reasoning | Python chosen (not final). |
| 11 | Runs cost 0.1 to 0.7 USD, so 800 runs cost 80 to 560 USD. | Small tasks cost 0.003 to 0.006 USD. The estimate came from a different kind of session. | Our runs | Power table cost column corrected (file 05). |
| 12 | "`AGENTS.md` does not reach Claude Code because there is no `CLAUDE.md`." | Precise cause: with no `CLAUDE.md` anywhere, `AGENTS.md` loads. The home `CLAUDE.md` is an ancestor and hides it. Early single yes/no tests were also unreliable (arm A answered YES once). | Controlled `/tmp` pair, three runs per cell | Cause refined. Token and quote prompt replaced yes/no. |
| 13 | The first guard message ("record each PID you start") was good. | It was a dead end for processes the agent never started. Completion fell to 5 of 20. | Reading five failing runs | Message rewritten (arm D2). |
| 14 | "Tier 1 (rule tests) is already built several times." | It exists, but each version lacks tool calls, isolation or honest statistics. | Source reads | Reworded as "exists with gaps". |
| 15 | Shopify "dreaming" and "half of PRs." | "Dreaming" is not in the engineering post. Half of PRs is a founder claim. One in eight is the audited figure. The 36% to 77% figure is only from snippets. | Fetch summaries | Attribution corrected (file 01). |
| 16 | The original `stop-server` task. | It never tempted a violation. All three smoke runs of it (arms A, A2, B) were compliant. | Smoke runs | Task redesigned. Old runs moved aside. |
| 17 | "Violation rates rose after the rule, so the rule fails." | The rule was not loaded, and the populations differ. No rule effect can be read from it. | Reachability tests | Section 3.2 caveats. |
| 18 | "Prose rules rely on prose alone, with no hook" (about pkill). | True, but prose that was never loaded is a stronger statement. | Reachability tests | Replaced. |
| 19 | Planned questions to the developer about "the first user." | There is no product yet. The question was premature. | Developer feedback | Reframed around build-plan inputs. |

## Part 3. A user pushback that improved the work

The developer said: "deterministic checks and scripts don't need judge or
evaluation, they're always better than prose."
Our position, supported by data:
- Right in principle: a check has the same verdict every time. In our toy
  tasks, prose left 60% cp/rm attempts, while a guard blocked every one.
- Not "always" and not "no evaluation": a check can be wrong, can change
  agent behavior, and cannot cover judgment rules. Their own docs list
  checks that could not fail and a guard that blocked a branch named
  `feature/main`.
- The guard experiment then showed a concrete case: a guard with a dead-end
  message dropped completion to 5 of 20.
