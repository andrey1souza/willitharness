# 03. Formal model of the audit pipeline

This file plans two models and their tasks. It does not hold the models.
The existing pattern is in `../../../formal/tla/README.md` and `../../../formal/lean/README.md`.
Both models are bounded and cover logic only. They do not cover what an agent does, shell parsing or the `claude` CLI (contract section 9).

## Part 1. TLA+ model of the pipeline (task T94)

### The pipeline
Stages, in order: Scan, Classify, FreeReport, ProposePlan, OptIn, Run, PaidReport.
The free stages end at FreeReport. The paid stages need an explicit OptIn.

### State
| Variable | Meaning |
|---|---|
| files | The set of files of the audited folder, as hashes. It starts as a fixed set |
| stage | One of the stages above, or Refused |
| freeReport | The content of the free report. A function of the scan only |
| optIn | Whether the user opted in, and the cap that came with it (0 means none) |
| spent, reserved | Money recorded and money held for runs in flight |
| inFlight | The number of runs in flight |
| applied | The set of proposals applied to the folder. It must stay empty |

### Actions
| Action | Rule |
|---|---|
| Scan, Classify | Read the files. They never change `files` |
| ProduceFreeReport | Sets `freeReport` once, from the scan |
| ProposePlan | Needs `freeReport` set. Adds a plan and its worst case |
| GiveOptIn(cap) | Needs a plan. Needs cap at least the worst case. Sets `optIn` |
| StartRun | Needs `optIn`. Needs spent + reserved + run cap at most the cap |
| EndRun | Settles a run as usable or unusable. Cost is between 0 and the run cap |
| Timeout, Denied | End a run as unusable. A timeout charges the run cap. A denial charges 0 |
| ProducePaidReport | Adds a section. Never edits `freeReport` |
| Intruder | Writes a file or applies a proposal. Enabled only in a mutant |

### Invariants and properties
| Name | Statement | Contract ID | Kind |
|---|---|---|---|
| NoWrite | `files` equals its start value in every state | RO1 | invariant |
| NeverApplied | `applied` is empty in every state | RO3 | invariant |
| NoSpendWithoutOptIn | spent above 0 or reserved above 0 implies a cap above 0 from an opt-in | SC1 | invariant |
| CapCoversWorstCase | An opt-in exists only when its cap is at least the worst case | SC2 | invariant |
| SpendWithinCap | spent + reserved is at most the cap | SC3 | invariant |
| FreeReportStable | After ProduceFreeReport, `freeReport` never changes | SC4 | action property |
| FreeNeverNeedsPaid | ProduceFreeReport is enabled with no opt-in and no run | SC4 | invariant over the enabled actions |
| DeniedStillReports | A denied or timed-out run still allows ProduceFreeReport | SC5 | property |
| OptInIsSingleUse | After a run ends, a new StartRun of another plan needs a new opt-in | SC6 | action property |

### Scenarios (one cfg each)
| Scenario | What it covers |
|---|---|
| nominal | One plan, one run, all stages |
| denied | The runner denies a run |
| timeout | A run times out and charges the run cap |
| cap_tight | The cap equals the worst case exactly |
| two_plans | Two plans in one audit. The opt-in covers one |
| no_optin | The user never opts in. The free report must still end the audit |

### Probes
Each probe states "this never happens". TLC must violate it, so the model can reach the case.
Probes: a run starts. A paid report is made. A run times out. A run is denied. The cap is reached exactly. Two plans exist.

### Mutants
Each mutant breaks one rule. TLC must report the matching invariant. A mutant that passes means the invariant cannot fail.
| Mutant | Must violate |
|---|---|
| Intruder writes a file | NoWrite |
| Intruder applies a proposal | NeverApplied |
| StartRun without optIn | NoSpendWithoutOptIn |
| GiveOptIn accepts a cap below the worst case | CapCoversWorstCase |
| StartRun ignores `reserved` | SpendWithinCap |
| ProducePaidReport rewrites `freeReport` | FreeReportStable |
| ProduceFreeReport waits for a run | FreeNeverNeedsPaid |
| Timeout charges 0 | SpendWithinCap, when runs repeat |
| A second plan reuses the first opt-in | OptInIsSingleUse |

### Replay against the code
The v0 replay (`formal/tla/replay_traces.py`) walks the model and applies each action to the real lifecycle code.
Verified on 2026-11-25: `uv run python formal/tla/replay_traces.py` prints "152 walks, 1829 states compared, 11972 refusal probes, 18.3 s".
The same pattern needs a pipeline that has explicit stages in code. Task T94 first extracts that state machine from the audit command.
If the extraction costs more than the box of task T94, the replay becomes its own task. Until then TLC alone checks the model.

### Tasks of part 1
| Step | Output | Gate |
|---|---|---|
| 1 | Pipeline state machine in code with the stages above (new module) | Unit test: each refused action raises, with a rule and a fix |
| 2 | TLA+ module AuditPipeline.tla (new), cfgs, probes | `check_models.py` runs the scenarios and every probe is violated |
| 3 | Mutant specs for the table above | `check_models.py` reports each mutant violating its invariant |
| 4 | IDs RO1, RO3, SC1 to SC6 as TLA+ operators with those names | `scripts/gates/trace_check.py` finds each ID in the TLA+ files |
| 5 | Replay of the walks through the state machine | Replay prints walks and states compared, and a seeded divergence exits 1 |
| 6 | The TLA+ README states the contract version it checks | Gate of task T85 |

## Part 2. Lean tables for the component recommendation (task T95)

### The function
The function is `recommend`. Its inputs and values:
| Input | Values |
|---|---|
| usage | Used, Unobserved, TooFewSessions, NotObservable |
| backing | ScriptBacked, NoScript |
| duplicate | Duplicate, Unique |
| evidence | NotTested, KeepComponent, ReplaceWithPrompt, DeleteCandidate, Inconclusive, InsuranceKeep |

The evidence values are the values of the three-arm verdict in section 6a of the contract.
The output values: Keep, Remove, ReplaceByScript, Shrink, Undecided.
The domain has 4 x 2 x 2 x 6 = 96 inputs. The table holds one row for each.

### The rule, first match wins
| Rule | Condition | Value | ID |
|---|---|---|---|
| 1 | evidence is DeleteCandidate | Remove | RC2 |
| 2 | evidence is ReplaceWithPrompt | Shrink | RC3 |
| 3 | evidence is KeepComponent or InsuranceKeep | Keep | RC4 |
| 4 | duplicate is Duplicate | Shrink | RC5 |
| 5 | backing is ScriptBacked | ReplaceByScript | RC6 |
| 6 | usage is Unobserved | Remove | RC7 |
| 7 | usage is TooFewSessions or NotObservable | Undecided | RC7 |
| 8 | usage is Used | Keep, marked "free signal" | RC8 |

Evidence NotTested and Inconclusive fall through to rule 4. Both mean no measurement.
The table is a policy, like INSURANCE_MAX_RATE. It is not a measurement. The report says so.

### Golden-table pattern
| Part | Existing example | New work |
|---|---|---|
| Lean definition and theorems | `formal/lean/Willitharness/ThreeArm.lean` (TA1 to TA8) | A new Lean file for `recommend`, one theorem per rule |
| Exhaustive check | `TA1_allArmInputs_complete` | `RC1_allRecommendInputs_complete`, by `decide` over 96 inputs |
| Export | `lake exe export_table arms` | A new case `recommendation` that prints the table as JSON |
| Table file | `formal/lean/arms_table.json` | A new table file for the recommendation (new) |
| Independent reading | `check_lean.py` reads the contract text again in Python | A second reading of the table in Python, compared row by row |
| Wrong variants | `formal/lean/WrongVariants.lean` | The variants below. Each must fail to build |
| Python conformance | `tests/golden` compares code to the tables | The Python `recommend` equals the table on all 96 rows |

### Wrong variants that must fail
| Variant | The false claim | Why it matters |
|---|---|---|
| A free signal overrides KeepComponent | ScriptBacked and KeepComponent gives ReplaceByScript | A free signal must never beat a measurement (RC4) |
| Few sessions gives Remove | TooFewSessions and NoScript gives Remove | Unobserved is not unused (US2) |
| Duplicate checked before evidence | Duplicate and DeleteCandidate gives Shrink | A measurement comes first |
| Not total | One input has no row | RC1 |
| Not deterministic | Two rows for one input | RC1 |
| Used gives Keep before ScriptBacked | ScriptBacked and Used gives Keep | A script-backed prose rule is redundant |

### Tasks of part 2
| Step | Output | Gate |
|---|---|---|
| 1 | Lean definition, theorems RC1 to RC8, the exhaustive check | `python3 formal/lean/check_lean.py` builds, no `sorry`, `#print axioms` clean |
| 2 | Export case and table file with 96 rows | The Python reading and the Lean table agree on every row |
| 3 | Wrong variants | `check_lean.py` reports each variant failing to build |
| 4 | The Python `recommend` conforms | A golden test fails when one row is edited |
| 5 | The Lean README states the contract version it proves | Gate of task T85 |

## Limits
- TLA+ checks a bounded model with small constants. A pass is not a proof for all sizes (contract section 9).
- The Lean tables check the policy. They do not check that "unobserved" or "script-backed" is detected correctly. Tests and experiments check that.
- The model does not cover the `claude` CLI, its denials, or time. The simulation spike (`04-simulation-spike.md`) tests those with a fake runner.
