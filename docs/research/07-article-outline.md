# 07. Article outline

Audience: developers who write `CLAUDE.md`, `AGENTS.md`, skills and hooks
for coding agents.
Length target: 1,800 to 2,500 words, 4 tables, 2 diagrams.
Tone: plain, short sentences, honest about limits.

## Candidate titles

1. "Your AGENTS.md might not be loading: how to test whether an agent rule works"
2. "Before you test a rule, test that it loads"
3. "Prose rules, guard scripts, and the message that makes a block recoverable"

Recommendation: title 2 for the main article, because the first finding is
the most surprising and the cheapest to try. Titles 1 and 3 can be sections
or follow-up posts.

## Structure

1. The hook (150 words)
   - You wrote a rule. The agent broke it anyway. Was the rule ever read?
   - One-line result: in our setup, a rule in `AGENTS.md` never reached the
     agent, because a `CLAUDE.md` higher in the folder tree hides it.
2. How to check what loads (300 words)
   - The sentinel-token trick. The command line. The prompt text.
   - Why a token and not a real sentence (yes/no answers from a small model
     gave a wrong "YES").
   - Evidence table (file 03, section 3.1, rows 5 to 11).
   - Diagram: directory chain with and without a parent `CLAUDE.md`.
3. Does a loaded rule change anything? (400 words)
   - Arms A, A2, B, C. What each answers.
   - Bar chart of attempt rates, per task (file 03).
   - The leave-one-out arm and the noise arm in one paragraph each.
   - Honest note: attempts, toy tasks, haiku.
4. Can a script replace the prose? (400 words)
   - Guard design. The hook. The two messages, side by side.
   - Table: attempts, blocked, done, turns (file 05, section 3).
   - The 5 of 20 against 20 of 20 story. Message design rules:
     name the rule, say why, give a path that works for the agent's
     situation.
5. What it costs (200 words)
   - 0.003 to 0.006 USD per small run. 280 runs for 1.07 USD.
   - Corrected power table (file 05). What you can and cannot detect.
6. What we did not test (250 words)
   - The honest-limits section below.
7. Try it yourself (200 words)
   - A five-step recipe: plant token, check load, pick one rule, write a
     tempting task, run with a noise arm.
   - Safety: stubs, allowlist, scratch directory, budget cap.
8. Takeaways (100 words)

## Key figures and tables to include
- Directory-chain diagram (loads / hidden).
- Reachability evidence table.
- Attempt-rate bar chart for pkill and cp/rm across A, A2, C, B.
- Guard table: old and new message, attempts, blocked, done.
- Corrected power and cost table.

## Main takeaways
1. A rule can silently not load. Check what loads before you test what it does.
2. A rule in context changed behavior a lot in our toy tasks. A rule
   that is masked changed nothing.
3. Run an identical-config noise arm. If it shows a difference, trust nothing.
4. Remove one section at a time to see whether the rule or "any
   instruction" causes the change.
5. A guard script blocks commands. A guard message decides whether the agent
   recovers. Test the message.
6. Small tasks are cheap to test. Effects on overall success are not.

## Honest-limits section (must stay in the article)
- It is a spike. Tasks are toy tasks written to tempt a violation.
- Haiku for the main runs. One stronger-model run is described
  separately (add its result or remove the claim).
- Commands were stubbed. Process IDs were fake.
- Two rules only. Twenty runs per cell.
- "Violation" means an attempt, including attempts the guard or allowlist
  blocked.
- Claude Code version not recorded. The load behavior may change.
- The studies cited show small success effects for context files.
  Our result is about targeted behavior, not overall success.
- We were wrong several times along the way. Say so (file 04, part 2).

## Claims to hold back unless checked
- Anything about Shopify River numbers beyond the engineering post.
- The 36% to 77% figure (primary page not read).
- Lulla and Khatri numbers (snippets only).
- "Nobody has built this": at least five small repos built parts.

## Open items before writing
- Add sonnet, spike B and spike C results if they change the picture.
- Record the Claude Code version and rerun the reachability table.
- Decide whether to publish the scripts. They are scratch code in `/tmp`.
- Remove local paths and any employer-linked names from all examples.
