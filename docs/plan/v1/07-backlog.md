# 07. Task backlog for v1

Tasks in dependency order. The format follows `../07-task-backlog.md`: a BDD story with Given and Then lines, the IDs it covers, a gate and its dependencies.
Sizes: S under half a day, M about a day, L two or three days. A task is done when its gate passes with its bad input rejected.
Numbering: the last ID on main is T83. The audit story T84 is on the branch `feat/audit-command` and is the base of v1. v1 starts at T85.
Order, decided by the owner: merge T84 first, then T85 to T89, then the features.
A path marked "(new)" does not exist yet. The IDs named here are proposed. Each task adds its own IDs to the contract (see `02-contract-v0.8.md`).
No task pushes to a remote. A paid run is never part of `make check`.

## Part A. Stale docs first (goal G4)

### T85. Fail the build when a formal doc names an old contract version (S)
As a maintainer, I want each formal doc to state its contract version, so that no header lags.
- Given the repo today, then the new check fails. The two formal READMEs and `check_lean.py` name older contract versions. The contract is v0.7.
- Given the check, then it is written and seen failing before any fix.
- Given a copy with a different contract title, then the check exits 1 and names each file that differs.
- Given the headers fixed, then the check passes.
- Given the fix, then `make formal` ran first. Its result is in the change text.
- Given a Lean or TLA+ table that differs from the contract, then the task lists the difference. It does not bump the version.
- IDs: none. Gate: test file tests/gates/test_formal_headers.py (new), plus a check in `scripts/gates/repo_checks.py`. Deps: none.
- Creates: tests/gates/test_formal_headers.py (new).

### T86. Check numbers and file lists of the formal docs (M)
As a maintainer, I want each count and file name in the formal READMEs checked, so that none goes stale.
- Given a README with a wrong theorem count, then the check exits 1.
- Given a README row for a missing file, such as `last_run.txt` today, then the check exits 1.
- Given such a row that says the file is generated and ignored by git, then the check passes.
- Given a stated row count of a golden table that differs from its JSON file, then the check exits 1.
- Given a stated probe count or mutant count that differs from the TLA+ files, then the check exits 1.
- Given `checked_documents`, then it includes the Markdown files under `formal/`.
- Given a claim that no script can check, then the task deletes the claim.
- IDs: none. Gate: test file tests/gates/test_formal_numbers.py (new). Deps: T85.
- Creates: tests/gates/test_formal_numbers.py (new).

### T87. Keep hyphenated command names and check both ways (S)
As a maintainer, I want a documented command checked by its full name, so that a typo cannot pass.
- Given a doc that names the command build-plna, then the docs gate fails. Today it passes. The name is cut at the hyphen.
- Given a `USAGE` command with no row in the README table "What works today", then the docs gate fails.
- Given the README and `USAGE` in step, then the gate passes.
- IDs: none. Gate: the existing test file tests/gates/test_docs_freshness.py gains two failing-first cases. Deps: none.

### T88. Rebuild the Pages site on every merge to main (S)
As a maintainer, I want the site rebuilt on each merge, so that it never shows an old README.
Decided by the owner: the `paths` filter of the Pages workflow is removed. The plan change that records this decision also removes it.
- Given the workflow, then it has no `paths` filter on push, so each merge rebuilds the site.
- Given a copy of the workflow with a filter that omits README.md, then the check exits 1.
- Given the change, then the task reports the seconds of one build. The cost is one Linux job per merge. The gain is a site that is never stale.
- IDs: none. Gate: a check in `scripts/gates/repo_checks.py` and one test. Deps: none.

### T89. Gate the v1 plan folder (S)
As a maintainer, I want the v1 plan folder checked, so that the plan cannot go stale as tasks land.
- Given a "(new)" path that exists while its task entry stands, then the gate exits 1.
- Given an ID with different text in this plan and in the contract, then the gate exits 1.
- Given a task entry with no gate line, then the gate exits 1.
- Given a number in a v1 plan file, then it needs a tag. IDs, versions, dates, list markers and file names need none. Exit codes and the numbers 0 and 1 need none. [param] marks a plan decision. [check:name] marks a number that the gate computes from a file or a command output.
- Given an untagged number, then the gate exits 1 and names the line. The gate extends `docs_freshness.py`, or is a new gate with a failing-first test.
- Given a [check:name] tag with no registered check, then the gate exits 1.
- IDs: none. Gate: test file tests/gates/test_plan_v1.py (new). Deps: T85.
- Creates: tests/gates/test_plan_v1.py (new).

## Part B. Component inventory, usage and prose (goals G1 and G2)

### T90. List every component of a folder with its size (M)
As an owner of a harness, I want each hook, skill, agent and command listed with its size. A plugin repo then shows its parts.
- Given a fixture plugin repo, then the audit lists each component with kind, path and characters (IN1, IN2).
- Given the fixture, then it holds a hooks file, two skills, an agent, a command and a git hook.
- Given each size, then it equals the size from an independent count in the test (K1).
- Given a hooks file in another layout, then it is listed as "unsupported format" with its size (IN3).
- Given the overwatch registry as the fixture, then the unsupported-format case is covered.
- Given a hook command that names a script inside the folder, then the size includes that script text (IN2).
- Given any hook, then its code is never run (IN4).
- Given a folder `.claude/worktrees` with copies, then they are skipped (IN1).
- Given a user-level file such as `~/CLAUDE.md`, then its size is on a separate line and in no repo total.
- Given a symlink to a file outside the folder, then the file is not read.
- IDs: IN1, IN2, IN3, IN4. Gate: test file tests/gates/test_inventory.py (new). Deps: T84.
- Creates: tests/gates/test_inventory.py (new).

### T91. Count component usage from session transcripts (M)
As an owner of a harness, I want each component's calls counted in my sessions. Unused components are then findable.
- Given fixture transcripts, then the report counts each Skill call, Agent call, hook run and slash command by name (US1).
- Given each count, then the report adds the first time, the last time and the number of sessions (US1).
- Given each count, then it equals the count of an independent reader in the test (K2).
- Given a line that is not JSON, then it counts as one unreadable line and the audit goes on (US4).
- Given a message that holds a planted secret string, then the report never holds the string (US3).
- Given a session whose folder is outside the audited folder, then it is not counted.
- Given every folder that holds transcripts, then the report reads each one and lists each folder it read and each it did not read, with the reason (US1). The Cursor folder `~/.cursor/projects` is listed as not read.
- Given a call id that appears more than once, then the report counts it once (US1).
- Given a skill run by a slash command and by a Skill call, then the report counts the two kinds apart (US1).
- Given the oldest and the newest session time that were read, then the report shows both. "Unobserved" then names its window (US2).
- Given a component with zero calls, then the report says "unobserved in N sessions" (US2).
- Given no value for MIN_USAGE_SESSIONS yet, then the report never says "unused". EX2 sets the value.
- Given each session, then the Claude Code `version` field is recorded, so a format change shows.
- Given a git hook, then its usage is "not observable".
- IDs: US1, US2, US3, US4. Gate: test file tests/gates/test_usage.py (new). Deps: T90.
- Creates: tests/gates/test_usage.py (new).

### T92. Report prose cost and static redundancy (M)
As an owner of a harness, I want the characters and duplicates of each component. I then see the prose.
- Given a folder, then the report lists characters per component (PC1).
- Given the same folder, then the list splits always-loaded from on-demand, with the share of each source (PC2).
- Given a sentence that is equal after trimming and lower-casing in two components, then both are listed as duplicates (RD1).
- Given a rule that names a script that exists, then it is listed as script-backed (RD1).
- Given a script that does not exist, then the rule gets no such class.
- Given the free report, then it never says a component is "the same as prompting" (RD2).
- IDs: PC1, PC2, RD1, RD2. Gate: test file tests/gates/test_prose_cost.py (new). Deps: T90.
- Creates: tests/gates/test_prose_cost.py (new).

### T93. Give a recommendation and proposals for each component (M)
As an owner of a harness, I want one recommendation per component: keep, remove, replace or shrink.
- Given usage, backing, duplicate and evidence, then `recommend` follows the table of `03-formal-model.md`. It is total (RC1 to RC8).
- Given a measured DeleteCandidate and a script-backed rule, then the value is Remove (RC2, RC4).
- Given a duplicate, then the proposal is a diff that deletes the duplicate line (PC3).
- Given a script-backed rule, then the proposal replaces it with a pointer to the script (PC3).
- Given any other prose, then the report proposes no rewrite.
- Given a recommendation from free signals only, then the report marks it "free signal, not measured".
- Given the CLI, then no command applies a proposal (RO3, K6).
- Given a fixture repo, then a copy hashed before and after shows no change.
- IDs: RC1 to RC8, PC3, RO3. Gate: test file tests/gates/test_recommend.py (new). Deps: T91, T92.
- Creates: tests/gates/test_recommend.py (new).

## Part C. Formal models (goal G3, the promises)

### T94. Model the audit pipeline in TLA+ (L)
As a maintainer, I want the pipeline promises checked in a model: no write, no spend without a cap, no applied proposal.
- Given the pipeline code, then it has explicit stages. Each refused action raises with a rule and a fix.
- Given the model, then TLC checks the nine invariants of `03-formal-model.md` (RO1, RO3, SC1 to SC6).
- Given each mutant of `03-formal-model.md`, then TLC reports the matching invariant.
- Given each probe, then TLC violates it.
- Given the replay, then walks run through the stage code. A seeded divergence exits 1.
- IDs: RO1, RO3, SC1, SC2, SC3, SC4, SC5, SC6. Gate: `uv run python formal/tla/check_models.py` and `uv run python formal/tla/replay_traces.py`. Deps: T93.

### T95. Add the recommendation table in Lean (M)
As a maintainer, I want the recommendation table proven total and deterministic, so that the code cannot drift.
- Given the Lean definition, then it builds with no `sorry`. The axiom audit shows only standard axioms.
- Given the exhaustive check, then it covers every input of the domain.
- Given each wrong variant of `03-formal-model.md`, then the build fails.
- Given the Python `recommend`, then it equals the table on every row.
- IDs: RC1 to RC8. Gate: `python3 formal/lean/check_lean.py` and `uv run pytest tests/golden`. Deps: T93.

### T96. Move the IDs into the contract and bump it to v0.8 (S)
As a maintainer, I want each proposed ID in the contract once its code exists. The trace gate then covers it.
- Given each ID of `02-contract-v0.8.md`, then it is in the section 8 table and the trace gate finds its places.
- Given the contract title, then it reads v0.8.
- Given section 11, then it names each change and its cause.
- Given a doc that still states v0.7, then the docs gate fails until it is corrected.
- Given the moved definitions, then they are deleted from `02-contract-v0.8.md`.
- IDs: all of Part B and Part C. Gate: `uv run python scripts/gates/trace_check.py` and `uv run python scripts/gates/repo_checks.py`. Deps: T93, T94, T95.

## Part D. Simulation spike (not a commitment)

### T97. Spike: a deterministic simulator of the audit pipeline (M, time-boxed)
As an owner, I want to know if a simulator finds defects that the gates miss. I add it only if it pays.
Decided by the owner: the spike runs, with the 8-hour box and the numeric criteria of `04-simulation-spike.md`. [param]
- Given the method of `04-simulation-spike.md`, then the spike stops at 8 hours. [param]
- Given 5 planted defects, then the result lists which the gates catch and which the simulator catches. [param]
- Given the go criteria, then the result states go or no-go with the numbers.
- Given no-go, then the simulator code is deleted and a dated note stays.
- Given go, then the simulator joins `make check` as one target.
- IDs: none. Gate: the numbers of the spike. Deps: T94.

## Part E. Free end to end, paid step, plugin (goal G3)

### T98. Gate the free audit end to end (M)
As an owner of a harness, I want one gate for "scan this repo". The free promise is then tested whole.
- Given a copy of each fixture repo, then the file hashes and the file list stay equal (RO1, K3).
- Given a helper that writes one file, then the same check fails.
- Given the free audit, then a trap on any spawned process or network call never fires (RO2, K4).
- Given an output folder inside the audited folder, then the audit refuses and names the rule (RO4).
- Given the report, then it holds the sections of the audit story. It adds components, usage, prose cost and proposals.
- Given a plugin repo, then the report no longer shows zero rules.
- IDs: RO1, RO2, RO4. Gate: test file tests/gates/test_audit_free_end_to_end.py (new). Deps: T93, T94.
- Creates: tests/gates/test_audit_free_end_to_end.py (new).

### T99. Add the paid step with opt-in and a required cap (M)
As an owner of a harness, I want a second command that spends only with my cap. The free scan can never spend.
- Given the paid step, then it is its own command and not a flag of the free audit (SC1). The free audit has no path to it. The task sets the name.
- Given no `--cap-usd` in the command, then it exits 2 before any run (SC1).
- Given a config file with a cap, then it is ignored. There is no default cap (SC1).
- Given a cap below the worst case, then it refuses and prints the worst case (SC2).
- Given the worst case, then it is arms x reps x tasks x run cap, plus probes.
- Given a finished step, then the recorded spend is at most the cap (SC3).
- Given a denied or timed-out run, then it is recorded as unusable and the report still prints (SC5).
- Given a second plan in the same audit, then it needs its own opt-in (SC6).
- Given the paid result, then the free report text is byte-equal to before. The paid section is appended (SC4).
- Given the run state, then it is written outside the audited folder (RO4).
- IDs: SC1 to SC6, RO4. Gate: test file tests/gates/test_audit_paid_step.py (new), with the fake agent. Deps: T98.
- Creates: tests/gates/test_audit_paid_step.py (new).

### T100. Harden the plugin skill (M)
As a user of the plugin, I want the skill to scan free first and ask before any paid step.
- Given the skill text, then it tells the agent to run the free audit first and show the whole report.
- Given the skill text, then it names no command that writes to the audited folder.
- Given a paid step, then the skill asks for a cap and shows the worst case before it runs anything.
- Given each sentence of the skill, then it has 20 words or fewer. The check exists in `plugin_checks.py` on the audit branch. [param]
- Given the plugin manifest, then it holds name, version and description.
- Given the tools the skill may use, then the check lists them. The task reads the Claude Code documentation first.
- Given a frontmatter field for tool limits, then the gate checks it. Inferred: such a field exists. Verify before use.
- IDs: none. Gate: the plugin check extended, with its test file tests/gates/test_plugin_checks.py. Deps: T99.

## Part F. Experiments (goals G1 to G3)

### T101. Run the free experiments on the four repos (M)
As an owner, I want EX1 to EX6 run and stored, so that the thresholds of v1 come from data.
- Given EX1 to EX6 of `05-experiments.md`, then each result is a stored file with its command and its date.
- Given EX2, then MIN_USAGE_SESSIONS gets a value and US2 uses it.
- Given EX3, then the Shrink threshold gets a value, or the task states that there is none.
- Given EX4, then the three mask results are stored as fixtures.
- Given a failed pass criterion, then the plan changes as `05-experiments.md` says.
- IDs: none. Gate: the stored files and a test that reads them (new). Deps: T98.

### T102. Paid experiments PX1 to PX4, last (S each)
As an owner, I want each paid run approved one at a time, so that no spend surprises me.
- Given PX1 to PX4, then each is listed with its command and its worst case before it runs.
- Given an approval, then the run stays at or below its worst case.
- Given a finished run, then the result is stored with its cost.
- Given a change that follows from a result in gated-delivery, then it stays local. Nothing is pushed.
- IDs: none. Gate: the live gate of each run, defined with its approval. Deps: T101, T99.
