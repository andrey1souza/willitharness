# 06. Docs that are always true

Goal G4: a bad doc is worse than none. This file states the rule, the checks that exist, the gaps and the tasks.

## The rule
A claim in a doc stays only if a script checks it against code or gate output. The script fails when the claim is false.
If no script can check a claim, delete the claim.
One exception exists. A line may carry the planned marker of the backlog, with the ID of an open task. Verified: `planned_errors` in `scripts/gates/docs_freshness.py` enforces it.
A dated snapshot may stay in a plan or research file only with its date and its command. It is history, not a claim about today.

## The deletion rule
1. A doc claim with no check and no open task is deleted in the next change that touches the doc.
2. A check that cannot fail does not count. Each new check ships with a seeded bad copy that makes it exit 1.
3. A task that lands deletes its own entry from the v1 backlog in the same change. The v1 plan gate (task T89) fails when a path listed as "(new)" exists while its task entry stands.
4. A number in a doc is computed by a script or is not in the doc.

## What each doc claim is checked against
| Doc | Claim kind | Checked against | Gate | State today |
|---|---|---|---|---|
| `README.md` | Documented commands and flags | `USAGE` in `src/willitharness/cli.py` | `command_errors` in `docs_freshness.py` | Partly. See finding F3 |
| `README.md` | `make` targets and the `make check` sentence | The Makefile | `make_errors` | Checked |
| `README.md` | Paths, the `.willitharness` folder, the Data terms, the isolation limits | The tree, `world.py`, `repo_checks.py` | `readme_path_errors`, `runtime_errors`, two repo checks | Checked |
| `README.md` | The offline quick start | The commands run in a copy | `tests/gates/test_readme_quick_start.py` | Checked |
| `README.md` | The before and after numbers | `fixtures/results/g4_4.json` | `tests/gates/test_readme_before_after.py` | Checked |
| `docs/contract.md` | The contract is the source | Section 8 against features, tests, Lean, TLA+ | `scripts/gates/trace_check.py` | Checked |
| `docs/plan/*.md` | Counts, IDs, versions, planned markers | Backlog, features, contract | `docs_freshness.py`, `repo_checks.py` | Checked. No hand counts (task T79) |
| `docs/plan/v1/*.md` | Same as `docs/plan/*.md` | Same | Same, plus the plan gate of task T89 | Checked after T89 |
| `formal/tla/README.md` | Contract version, file list, counts | The contract, the folder, the cfg files | None | Unchecked. See F1 and F2 |
| `formal/lean/README.md` | Contract version, theorem and row counts | The contract, `grep`, the JSON tables | None | Unchecked. See F1 |
| GitHub Pages | Every number and text on the site | `scripts/site/extract.py` reads README, contract, fixtures, gate output | `scripts/site/build.py --check` | Built, but see F5 |

## Findings, all Verified on 2026-11-25
| ID | Finding | Evidence |
|---|---|---|
| F1 | The formal docs state old contract versions. TLA+ README says v0.4. Lean README says v0.3. `check_lean.py` sets `CONTRACT_VERSION = "v0.3"`. The contract is v0.7 | `head -1 formal/tla/README.md`, `grep CONTRACT_VERSION formal/lean/check_lean.py`, line 1 of `docs/contract.md` |
| F1b | `checked_documents` in `docs_freshness.py` returns README.md and the files under `docs/` only. It skips `formal/` | Function body |
| F2 | The TLA+ README lists `last_run.txt`. The file does not exist. No code writes it | `ls formal/tla`; `grep -rn last_run formal scripts Makefile .gitignore` finds only the README line |
| F3 | `command_name` uses `^[a-z]+(?: check)?`. It cuts `build-plan` to `build` and `load-report` to `load`. A doc that names a mistyped command with a known prefix passes | Running `read_facts` prints the command keys `build` and `load` |
| F4 | No check runs the other way: every command of `USAGE` has a row in the README table | `docs_freshness.py` holds no such function |
| F5 | The Pages workflow runs only for pushes that touch `site/**`, `scripts/site/**`, `fixtures/results/**`, `pyproject.toml` and `uv.lock`. The site reads `README.md` and `docs/contract.md`, and shows test and gate counts. A README change does not rebuild the site | `.github/workflows/pages.yml`; `README_FILE` and `CONTRACT_FILE` in `scripts/site/extract.py` |
| F6 | `FILE_REFERENCE` needs a slash and a known suffix. A bare name such as `last_run.txt` is never checked | The pattern in `docs_freshness.py` |
| F7 | The Lean README states 110 theorems and the row count of each table. Verified now: 110 `theorem` lines and the JSON lengths 45, 12, 140, 30, 54, 32, 128 match the README. No script compares them, so a change goes stale without notice | `grep` over `formal/lean/Willitharness`; Python `len` of each JSON table |

## Gates to add or extend
Each gate has a bad input that must fail. Each task is in `07-backlog.md`.
| Gate | Checks | Bad input | Task |
|---|---|---|---|
| Header version | Each version statement equals the contract version. The statements are the title and first paragraph of each formal README, `formal/lean/contract-issues.md` and `CONTRACT_VERSION` | A copy of the repo with the contract at v0.9 | T85 |
| Formal numbers | Each count in the formal READMEs equals what the files hold: theorems, table rows, probes and mutants | A README with 111 theorems | T86 |
| File list | Each file named in a "Files" table exists in its folder. A generated file must be listed as ignored by git | The README row `last_run.txt` | T86 |
| Command names | The command name keeps its hyphen. Each command of `USAGE` has a README row | A doc with a mistyped `build-plna` | T87 |
| Pages trigger | The Pages workflow has no `paths` filter on push, so each merge rebuilds the site. Recommended: the cost is one Linux job per merge, seconds unmeasured | A workflow with a filter that omits README.md | T88 |
| Plan v1 | A path marked "(new)" does not exist while its task stands. An ID in this plan and in the contract has one text | A task whose output file exists | T89 |

## What stays generated
| Thing | How it is generated | Why it cannot go stale |
|---|---|---|
| The site pages | `scripts/site/build.py` reads README, contract, fixtures and gate output | `build.py --check` fails on a number it cannot trace to a source |
| The gate status file of the site | The build computes it. It is not tracked | `repo_checks.py` fails if it is tracked |
| `formal/tla/generated/` | `check_models.py` writes it | Same check |
| The v1 report numbers | The audit command computes them | No doc quotes them |

## Order of work
Fix F1 first, as the owner asked. The first gate (T85) fails today on the TLA+ README (v0.4) and the Lean README (v0.3).
A header is bumped only after the formal files are read against section 11 of the contract.
Inferred: the Lean tables may differ from v0.7. The checker's independent reading says "contract v0.3". No script compared it with newer sections.
Task T85 therefore runs the Lean and TLA+ gates (`make formal`) before it bumps a version, and states the result.

## Limits
- A script checks a claim only as well as its pattern reads the claim. Prose that no pattern reads is not checked. The deletion rule exists for that case.
- The site check proves the site matches its sources. It does not prove the sources are true.
