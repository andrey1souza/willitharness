# Research notes: do agent rules work, and how do you test them?

Status: SPIKE. Draft notes, written 2026-11-17. Local and disposable.
Nothing here is a product, a package or a released result.

## Purpose

These notes keep the findings of one long research session in files.
They also feed a later article for agentic developers.
The session started with one question: what is the return on agents and
harness files that learn about a product? It ended with a narrower
question: does a rule in a harness file change what a coding agent does?

## How to read the labels

| Label | Meaning |
|---|---|
| Verified | Read in a file or paper, or measured in our own runs |
| Inferred | Reasoned from verified facts, not checked directly |
| Unverified | Seen only in a search snippet, a summary, or a subagent report |

Many "Verified" facts about other people's repos come from subagents
that read the source. We did not run those tools, except where noted.

## Files

| File | Content |
|---|---|
| 01-question-and-method.md | The question, the structure of the work, the test method, isolation findings |
| 02-landscape-and-prior-art.md | Every tool, repo, post and paper looked at, plus a capability table |
| 03-experiments.md | Exact design and results of every experiment, with placeholders for open runs |
| 04-findings-and-corrections.md | Findings ranked by evidence, and a log of our own errors |
| 05-roi-and-power.md | Return on investment, power and cost, prose versus guard |
| 06-open-questions-and-next-experiments.md | What is unknown, what to test next, what a first tool would contain |
| 07-article-outline.md | Candidate titles and an outline for the article |
| MANIFEST.md | Every script and artifact path, with its purpose |
| spike-b-realistic-tasks.md | Added by another worker: realistic tasks (may not exist yet) |
| spike-c-skills-hooks.md | Added by another worker: skills and hooks (may not exist yet) |

```
question --> landscape --> experiments --> findings
   01           02             03             04
                                |              |
                                v              v
                          roi/power (05) --> open questions (06) --> article (07)
```

## Honest limits of the whole effort

- It is a spike. Tasks are small and were written by us to tempt a violation.
- Most runs use the haiku model. A sonnet run is in progress (see 03).
- Commands are stubbed. Process IDs are fake. No real process was stopped.
- Only 2 of 5 candidate rules were tested.
- Run counts are small: 20 runs per cell at most.
- The "violation" metric counts attempts, not executions.
- Claude Code is the only agent tested. The version was not recorded.
- No real user, no real project task, no other model family.

## What is safe to say today

- A rule can silently not load. We measured this in one setup (file 03).
- Loaded rules changed behavior a lot in toy tasks (file 03).
- A script that blocks a command needs a block message with a working
  alternative (file 03, arms D and D2).
- Prior art is broad. The idea of testing rules is not new (file 02).

## What is not safe to say

- That rules help real work. We did not test real work.
- That a tool built from this would find value for other people.
- Any claim about stronger models, until the sonnet run is read.
