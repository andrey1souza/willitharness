# 05. Return on investment, power and cost

## 1. What the evidence says about the size of effects

| Source | Result | Status |
|---|---|---|
| Gloaguen et al. (arXiv 2602.11988) | Success changes with context files are small and not significant (-0.5%, -2%, +2.4%). Cost of LLM-written files rose about 20% to 23% (significant). Developer-written files beat LLM-written by 7% (p = 0.038). One sample per condition, 300 plus 138 tasks. | Verified (paper) |
| Lulla et al. (arXiv 2601.20404) | Median runtime -28.64%, output tokens -16.58% with an `AGENTS.md`. Completion comparable. 124 PRs. | Unverified (snippet) |
| Gloaguen against Lulla | They disagree on the direction of cost. The designs differ (LLM-written against repo files, task sets). | Inferred |
| ruleproof bench | Nothing significant (p = 0.125, p = 0.08). Hidden tests passed in 79 of 80 runs, so success sits at the ceiling. | Verified by subagent read |
| rulebench (treestar84) | Baseline 97.3%. The four "effective" rules were 4 failures against 0. Probably noise. | Verified by subagent read |
| deadrules demo | A "dead" verdict at 10 against 10 runs carries a ±28% interval. | Verified by subagent read |
| Our pilot | Targeted behavior changes were large: pkill 83% to 0, cp/rm 100% to 60%. | Verified, toy tasks |

Reading: harness text rarely moves overall task success much. It moves
cost, steps, and specific behaviors a lot. A measurement tool should aim at
those.

## 2. Power and cost: the corrected table

Assumptions (ours, not measured):
- Run-to-run spread is about 50% of the mean.
- 80% power, 5% two-sided error, unpaired comparison. Pairing by task helps.
- Detectable change = 2.8 × spread × sqrt(2 / runs per arm).

| Runs per arm | Smallest change detectable | Runs, both arms | Cost at 0.003 to 0.006 USD per run |
|---|---|---|---|
| 25 | 40% | 50 | 0.15 to 0.30 USD |
| 50 | 28% | 100 | 0.30 to 0.60 USD |
| 100 | 20% | 200 | 0.60 to 1.20 USD |
| 400 | 10% | 800 | 2.40 to 4.80 USD |
| 2,450 | 4% | 4,900 | 14.70 to 29.40 USD |

Correction: an earlier version of this table used 0.1 to 0.7 USD per run.
That figure came from skill sessions in another repo's docs. For our small
tasks on haiku, measured cost was 0.003 to 0.006 USD (0.001 for one cell
where runs ended early). The earlier cost column was 20 to 100 times too
high for small tasks.

Real, multi-step tasks will cost more per run. We do not know how much.
Spike B (realistic tasks) will give a first number. Larger models also cost
more per run. The sonnet run will give a second number.

Dollars are not the limit for small tasks. The limits are:
- Task realism. Toy tasks may mislead.
- Wall-clock time. Each run takes some tens of seconds (Inferred; the
  duration was not recorded). Batches ran in up to four parallel processes.
- Permission denials add noise.

### What is detectable, what is not

| Question | Detectable cheaply? | Why |
|---|---|---|
| Does a rule change a targeted behavior (violation rate)? | Yes | Effects are large. 0 of 20 against about 83% was clear. |
| Is the effect from the rule or any instruction? | Yes | One extra arm (leave-one-out). |
| Does the guard recover the agent? | Yes | Completion differences of 50 points or more. |
| Does a harness edit change overall success by under 10%? | No | Needs 400 or more runs per arm, and a task set that is not at the ceiling. |
| Does it generalize to real work? | Unknown | Not tested. |

## 3. Prose against guard: what the data supports

Numbers are from file 03 (haiku, toy tasks, 20 runs per cell).

| Arm | Attempts: pkill | Attempts: cp/rm | Done: pkill | Done: cp/rm | Turns: pkill | Turns: cp/rm |
|---|---|---|---|---|---|---|
| A, nothing | 80% | 100% | 20 | 13 | 8.6 | 10.2 |
| B, prose only | 0% | 60% | 17 | 13 | 6.2 | 13.3 |
| D, guard, old message | 90% | 100% | 5 | 15 | 3.4 | 12.2 |
| D2, guard, new message | 95% | 100% | 20 | 15 | 8.2 | 11.3 |
| E, prose and guard | 0% | 55% | 19 | 19 | 6.8 | 15.3 |

Reading:
1. The guard blocks every matching command. Nothing slipped past it,
   except the known bypass paths (absolute `/bin/cp`).
2. Prose lowers attempts. A blocked attempt costs a retry turn. In our data,
   prose arms did not use fewer turns than guard-only arms.
3. A guard with a dead-end message can be worse than no guard (arm D).
4. With a usable message, guard-only matched prose plus guard on
   completion (arm D2 against E, interval -24% to +12% on pkill).
5. The cost of prose is tokens in every session. For this section it is
   about 207 words (1,220 minus 1,013). The per-session token cost was not
   measured.
6. The cost of a guard is one blocked attempt per violating run, and
   maintenance of the check and its message. Neither was priced.

Bottom line, supported by data in this setup only: for mechanical rules a
guard with a usable message can replace the prose. That supports the
principle "reduce prose, add deterministic checks". It does not show that
a guard is free of evaluation: its message and its bypass paths need tests.

## 4. What the ROI of a possible tool would be

| Use | Value | Evidence | Confidence |
|---|---|---|---|
| Find rules that never load | Prevents dead rules, costs cents | Our reachability findings | High for our setup |
| Find rules that change behavior | Keeps useful rules, flags dead ones | Pilot arms B and C | Medium (toy tasks) |
| Find rules the model already follows (saturation) | Deletes tokens | Other repos' ceilings, our sonnet run pending | Medium to low |
| Convert prose rules into guards and test the message | Stronger enforcement | Pilot arms D, D2, E | Medium (toy tasks) |
| Gate auto-written lessons | Avoids harmful context files | Gloaguen: LLM-written files cost more, no gain | Medium |
| Facts store with staleness checks | Unknown | No study tests it | Low, unproven |
| TLA+ model of the tool's own verdict logic | Protects the tool's correctness | AWS paper, overwatch | Medium, later |

## 5. Honest statement of return

- Cheap and informative today: reachability, targeted rule tests,
  leave-one-out, a noise arm, guard-message tests.
- Not shown: any gain on real work, any gain for other people, any gain
  from stronger models.
- If most real rules are never violated by strong models, the tool mostly
  says "saturated, delete". That has value (fewer tokens, clearer
  harness) but it is not proof that rules help.
- agent-swarm reports instruction tokens falling from about 61.9k to 32.0k,
  but that is self-reported, from one system, with modeled attribution.
