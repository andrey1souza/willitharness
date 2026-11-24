# 05. Traceability matrix (contract v0.7)

Every contract ID maps to features, tests, a TLA+ item, a Lean item and a gate.
All cells are `planned`. Owners: features and tests belong to the plan fork's
backlog. TLA+ items belong to the TLA+ fork (`../formal/tla/`).
Lean items belong to the Lean fork (`../formal/lean/`, golden tables
`decision_table.json`, `effect_table.json`, `probe_table.json`, `guard_table.json`
in progress). The naming convention for formal items is the ID as a name prefix,
for example `L9_...` or `P2_...`. Gate G1.6 checks it.

Legend: F = feature file. n/a = not the right tool for this ID. Contract section 8
decides which tool covers which group. 66 IDs in total.

## Verdict properties and assumptions
| ID | Feature scenarios | Python tests | TLA+ | Lean | Gate |
|---|---|---|---|---|---|
| V1 | F verdict-engine: "Every valid input has exactly one verdict", pilot examples; F effect-with-noise: "Outcomes are counted per task cell and per outcome", "A pooled verdict carries a label and a warning"; F warnings: pooled | `test_stats_properties.py::test_v1_total`, `test_analysis_outcomes.py` | n/a | `V1_...` (Lean fork) | G1.1, G4.5 |
| V2 | F verdict-engine: "Too few runs always gives InconclusiveSmallN"; F effect-with-noise: "Too few runs gives NotEnoughRuns" | `test_v2_small_n` | n/a | `V2_...` | G1.1 |
| V3 | F verdict-engine: "Swapping the arms flips the verdict" | `test_v3_swap` | n/a | `V3_...` given DI-1 and DI-2 | G1.1 |
| V4 | F verdict-engine: "Identical counts never give FirstHigher or FirstLower" | `test_v4_identical` | n/a | `V4_...` | G1.1 |
| V5 | F verdict-engine: "Wilson interval has the known bounds" | `test_v5_bounds`, `test_stats_known.py` | n/a | `V5_...` oracle assumption, not proven | G1.1, G1.2 |
| V6 | F effect-with-noise: noise scenarios (NoiseOk, NoiseFloorTooHigh, NoiseUnmeasured, noise pair repeats the LOO arm); F decision-table: E1 outline; F report: "A report explains each noise status"; F warnings: W-LOWN | `test_effect.py`, `test_plan.py::test_noise_pair_repeats_loo` | n/a | `V6_...` NoiseStatus and mapping | G1.7, G1.8, G4.2 |
| E1 | F decision-table: "The verdict and the noise status map to an effect result", "The mapping is total over 3 noise statuses and 4 verdicts"; F effect-with-noise; F reachability: "A LOO arm that does not load the non-target token is invalid" | `test_effect.py::test_e1_total` | n/a | `E1_...` and `effect_table.json` | G1.7, G1.9 |
| DI-1 | F verdict-engine: "The difference interval is ordered" | `test_stats_properties.py::test_di1_ordered` | n/a | `DI1_...` oracle assumption | G1.1 |
| DI-2 | F verdict-engine: "Swapping the arms negates and reverses the difference interval" | `test_stats_properties.py::test_di2_swap` | n/a | `DI2_...` oracle assumption | G1.1 |

## Probe rules and guard result
| ID | Feature scenarios | Python tests | TLA+ | Lean | Gate |
|---|---|---|---|---|---|
| P1 | F reachability: "Fewer than MIN_PROBE_RUNS usable runs per arm give Unknown", "The command refuses a run count below MIN_PROBE_RUNS", "Unusable probe runs do not count" | `test_probe.py::test_p1` | n/a | `P1_...` and `probe_table.json` | G2.2, G2.4 |
| P2 | F reachability: "A control token that appears makes the probe invalid" | `test_p2` | n/a | `P2_...` | G2.2, G2.4 |
| P3 | F reachability: target token in every, no, some runs; ancestor masks AGENTS.md; agents-only (live) | `test_p3` | n/a | `P3_...` | G2.2, G2.3, G2.4 |
| P4 | F reachability: "The LOO arm must still load a non-target token", "A LOO arm that does not load the non-target token is invalid" | `test_p4` | n/a | `P4_...` | G2.2, G2.4, G4.1 |
| G1 | F guard-test: "A guard that matches the rule", "G1 truth table", usable message, bad message, no guard arm, bypass, block coverage | `test_guard_result.py`, `test_bypass.py`, `test_guard_corpus.py` | n/a | `G1_...` definition and `guard_table.json` | G5.1, G5.3, G5.6, G5.7 |

## Decision properties
| ID | Feature scenarios | Python tests | TLA+ | Lean | Gate |
|---|---|---|---|---|---|
| D1 | F decision-table: "A masked rule is always a loading problem" | `test_decision.py::test_d1` | n/a | `D1_...` | G1.4, G1.5 |
| D2 | F decision-table: "An unknown reachability result cannot be decided"; F reachability: L7 scenario | `test_d2` | n/a | `D2_...` | G1.4, G1.5 |
| D3 | F decision-table row D3; F effect-with-noise: noise differs | `test_d3` | n/a | `D3_...` | G1.4, G1.5 |
| D4 | F decision-table row D4; F effect-with-noise: too few runs | `test_d4` | n/a | `D4_...` | G1.4, G1.5 |
| D5 | F decision-table row D5; F effect-with-noise: rule raises violations | `test_d5` | n/a | `D5_...` | G1.4, G1.5 |
| D6 | F decision-table row D6 and "The delete-candidate text ..."; F effect-with-noise: saturated baseline; F report: delete candidate; F warnings: saturated | `test_d6` | n/a | `D6_...` | G1.4, G1.5, G4.6 |
| D7 | F decision-table row D7; F guard-test: "A guard with a usable message completes as often as the rule" | `test_d7` | n/a | `D7_...` | G1.4, G1.5 |
| D8 | F decision-table row D8; F guard-test: "No guard arm means GuardUntested" | `test_d8` | n/a | `D8_...` | G1.4, G1.5 |
| D9 | F decision-table: "The table is total and deterministic"; F warnings: "Warnings never change a verdict or a decision" | `test_d9_total` | n/a | `D9_...` totality | G1.4, G1.5, G5.4 |
| D10 | F decision-table: "ReplaceWithGuard has strict preconditions" | `test_d10` | n/a | `D10_...` | G1.4, G1.5 |
| D11 | F decision-table: "A rule that lowers violations is never a delete candidate" | `test_d11` | n/a | `D11_...` | G1.4, G1.5 |
| D12 | F decision-table: "A masked rule gets no verdict on its content" | `test_d12` | n/a | `D12_...` | G1.4, G1.5 |

## Three-arm verdict
| ID | Feature scenarios | Python tests | TLA+ | Lean | Gate |
|---|---|---|---|---|---|
| TA1 | F three-arm-verdict: "The function is total and deterministic" | `test_three_arm_unit.py::test_TA1_...`, `test_golden_tables.py::test_TA1_arms_table_conforms` | n/a | `TA1_...` totality and `arms_table.json` | G1.10 |
| TA2 | F three-arm-verdict: "An arm with too few runs gives no verdict" | `test_TA2_...` | n/a | `TA2_...` | G1.10 |
| TA3 | F three-arm-verdict: "Almost no violations in arm N gives insurance, as a policy choice" | `test_TA3_...` | n/a | `TA3_...` | G1.10 |
| TA4 | F three-arm-verdict: "A component that beats its own text as a prompt is kept" | `test_TA4_...` | n/a | `TA4_...` | G1.10 |
| TA5 | F three-arm-verdict: "A component equal to its prompt and better than nothing is replaced" | `test_TA5_...` | n/a | `TA5_...` | G1.10 |
| TA6 | F three-arm-verdict: "A component equal to nothing is a delete candidate" | `test_TA6_...` | n/a | `TA6_...` | G1.10 |
| TA7 | F three-arm-verdict: "A component worse than its prompt alone gives Inconclusive" | `test_TA7_...` | n/a | `TA7_...` | G1.10 |
| TA8 | F three-arm-verdict: "A component worse than nothing is a delete candidate" | `test_TA8_...` | n/a | `TA8_...` | G1.10 |

## Content against filler
| ID | Feature scenarios | Python tests | TLA+ | Lean | Gate |
|---|---|---|---|---|---|
| PB1 | F placebo-verdict: "The function is total and deterministic" | `test_placebo_unit.py::test_PB1_...`, `test_golden_tables.py::test_PB1_placebo_table_conforms` | n/a | `PB1_...` totality and `placebo_table.json` | G1.11 |
| PB2 | F placebo-verdict: "An arm with too few runs gives no content verdict" | `test_PB2_...` | n/a | `PB2_...` | G1.11 |
| PB3 | F placebo-verdict: "Almost no violations in arm N leaves no room to help, as a policy choice" | `test_PB3_...` | n/a | `PB3_...` | G1.11, G6.7 |
| PB4 | F placebo-verdict: "A component that beats the filler text has content that helps" | `test_PB4_...` | n/a | `PB4_...` | G1.11, G6.7 |
| PB5 | F placebo-verdict: "Filler text that beats the component is reported" | `test_PB5_...` | n/a | `PB5_...` | G1.11, G6.7 |
| PB6 | F placebo-verdict: "A component equal to the filler text, and both better than nothing, shows that added text helps"; "The report shows turns and cost for arm PL"; "Decide prints the content verdict after the three-arm verdict" | `test_PB6_...` | n/a | `PB6_...` | G1.11, G6.7 |
| PB7 | F placebo-verdict: "A component equal to the filler text and equal to nothing shows that nothing helps" | `test_PB7_...` | n/a | `PB7_...` | G1.11, G6.7 |
| PB8 | F placebo-verdict: "A component equal to the filler text, with only one of them better than nothing, is unclear" | `test_PB8_...` | n/a | `PB8_...` | G1.11, G6.7 |
| PB9 | F placebo-verdict: "A plan without arm PL is reported as before" | `test_placebo_report.py::test_PB9_...` | n/a | n/a | G6.7 |

## Side effects and world
| ID | Feature scenarios | Python tests | TLA+ | Lean | Gate |
|---|---|---|---|---|---|
| R1 | F detectors: required action present, missing, and a cut-off transcript | `test_detectors.py::test_r1` (pending, M3) | n/a | n/a | G3.2 |
| S1 | F side-effects: command listed with counts, no difference, turns and cost, alternative channels; F report: side-effect section | `test_side_effects.py` | n/a | n/a | G6.1 |
| S2 | F side-effects: "Side effects never change the decision", "The decision function takes no side-effect input"; F report | `test_side_effects.py::test_s2_same_decision`, `s2_type_check.py` | n/a | n/a (by type in Python) | G6.5 |
| W1 | F world-validation: task command with a stub, declared real, no stub | `test_world.py::test_w1` | n/a | n/a | G3.3 |
| W2 | F world-validation: valid world, stub outside the world, stub never changes real files | `test_world.py::test_w2` | n/a | n/a | G3.3 |
| W3 | F world-validation: "A changed world hash ends the validation", "Runs do not start after a world change ..." | `test_world.py::test_w3`, `test_lifecycle.py::test_world_invalidation` | world invalidation is modeled by the TLA+ fork (item name chosen by that fork; not checked by G1.6) | n/a | G3.9 |
| W4 | F world-validation: "A task without a prompt file is invalid" | `test_world_unit.py::test_W4_...`, `test_world_gate.py::test_W4_...` | n/a | n/a | G3.3 |
| W5 | F world-validation: "A prompt that names a measurement word is invalid" | `test_world_unit.py::test_W5_...`, `test_world_gate.py::test_W5_...` | n/a | n/a | G3.3 |

## Lifecycle safety and liveness
| ID | Feature scenarios | Python tests | TLA+ | Lean | Gate |
|---|---|---|---|---|---|
| L1 | F budget-and-resume: "No run starts before the plan is Running", reachability for every arm, Unknown counts; F world-validation: unvalidated world, W3 scenarios | `test_lifecycle.py::test_l1` | `L1_...` invariant (TLA+ fork) | n/a | G3.7, G7.1 |
| L2 | F budget-and-resume: "The budget stops the plan", "Parallel runners cannot overspend", "A record replaces the reservation ...", RUN_CAP cost; F runner-isolation: RUN_CAP scenario | `test_budget_parallel.py`, `test_run_cap.py`, `test_abort.py` | `L2_...` | n/a | G3.6, G3.10, G3.11, G7.1 |
| L3 | F budget-and-resume: "A recorded run cannot change", "Counters never decrease" | `test_store.py::test_append_only` | `L3_...` (counters never decrease) | n/a | G3.4, G7.1 |
| L4 | F budget-and-resume: "Resume skips full cells", "A finished plan resumes to nothing", "The default number of reps is 20" | `test_store.py::test_resume` | `L4_...` | n/a | G3.5, G7.1 |
| L5 | F budget-and-resume: no verdict before Complete, aborted plan, BudgetStopped plan, abort scenario; F report: refuses before analysis, refuses when aborted | `test_lifecycle.py::test_l5` | `L5_...` | n/a | G3.7, G3.11, G7.1 |
| L6 | F runner-isolation: usable per outcome, broken runs, denials; F effect-with-noise: outcomes per cell; F warnings: W-DENIAL; F report: what the counts mean | `test_stream_corpus.py`, `test_analysis_outcomes.py` | `L6_...` | n/a | G3.2, G4.5, G7.1 |
| L7 | F reachability: "An arm with Unknown reachability gets no effect verdict" | `test_analysis.py::test_l7` | `L7_...` | n/a | G2.2, G7.1 |
| L8 | F effect-with-noise: noise pair repeats LOO, no noise pair, LOO arm removes one section; F report | `test_analysis.py::test_l8`, `test_plan.py` | `L8_...` | n/a | G1.8, G4.2, G7.1 |
| L9 | F budget-and-resume: "An unusable run does not use a rep, and attempts are capped", "Retries stop when the cell is full" | `test_store.py::test_attempt_cap` | `L9_...` | n/a | G3.5, G7.1 |
| L10 | F budget-and-resume: "A BudgetStopped plan resumes with a higher budget", Complete, changed world, changed plan fingerprint, edited overlay file and Analyzed plans cannot resume, analyze warns | none yet; pending T61 (`trace_pending.json`) | `L10` action property; mutants RA, RD | n/a | G3.7, G7.1 |
| L11 | F budget-and-resume: "A resume with a budget that is not higher is refused" | none yet; pending T61 | `L11` action property; mutant RB | n/a | G3.7, G7.1 |
| L12 | F budget-and-resume: "A resumed plan is not marked as ended" | none yet; pending T61 | `L12` invariant; mutant RC | n/a | G3.7, G7.1 |
| T1 | F budget-and-resume: "A timed-out run still ends", RUN_CAP scenario; F runner-isolation: broken-run outline | `test_run_cap.py`, `test_timeout.py` | `T1_...` temporal property | n/a | G3.7, G3.10, G7.1 |
| T2 | F budget-and-resume: "A running plan that is never aborted finishes" | `test_lifecycle.py::test_t2` | `T2_...` temporal property | n/a | G3.7, G7.1 |
| T2a | F budget-and-resume: "A running plan that may be aborted ends in one of three states" | `test_lifecycle.py::test_t2a` | `T2a_...` temporal property | n/a | G3.7, G7.1 |

## Non-ID rules covered in features
| Rule | Feature | Tests | Gate |
|---|---|---|---|
| Warnings W-LOWN, W-DENIAL, saturated, AtBound, pooled | `warnings.feature`, `effect-with-noise.feature`, `report.feature` | `test_warnings.py` | G4.6 |
| `audit` prints one read-only report: every rule, its class, a loading prediction, proposed diffs, limits | none | `test_rule_class_unit.py`, `test_audit.py`, `test_plugin_checks.py` | T83 |
| Channel per arm (file, skill, hook, system_prompt) | `plan-arms.feature` | `tests/bdd/test_plan_arms.py` | G1.8 |
| The system_prompt channel is a file flag for the run and the probe | `runner-isolation.feature` | `test_real_runner.py`, `test_agent_tools.py`, `test_probe_command.py` | G3.10 |
| A `guard_only` arm blocks through a hook in `--settings`; the rules file stays out of the workspace; the repro prints `no difference` for one message | `guard-test.feature` | `test_guard_hook_unit.py`, `test_guard_hook_gate.py`, `test_real_runner.py`, `test_guard_repro_dry.py`, `test_guard_repro_live_path.py` | G3.10, G5.5 |
| `decide` reads the guard arm: transcripts and `guard-rules.json` give the guard result; missing evidence gives GuardUntested (T83) | `guard-test.feature` | `test_decide_guard_arm.py`, `test_decide_command.py`, `test_report_golden.py` | G5.4 |
| A completed check reads the transcript: every text in one Bash call, a blocked call never counts | `detectors.feature` | `test_detectors_unit.py`, `test_detectors_scenarios.py`, `test_plan_unit.py`, `test_transcript_completed_gate.py` | G5.8 |
| Outcomes per task cell, usable per outcome | `runner-isolation.feature`, `effect-with-noise.feature` | `test_analysis_outcomes.py` | G3.2, G4.5 |
| DEFAULT_REPS 20, MAX_RETRIES 2, MIN_PROBE_RUNS 3 | `budget-and-resume.feature`, `reachability.feature` | `test_plan.py` | G1.8 |
| A-CAP enforcement and timeout transition | `runner-isolation.feature`, `budget-and-resume.feature` | `test_run_cap.py` | G3.10 |
| Abort records in-flight runs unusable and charges RUN_CAP | `budget-and-resume.feature` | `test_abort.py` | G3.11 |

## Coverage check
Gate G1.6 reads the 66 contract IDs from the contract and fails if one is missing
from the features or the tests, or (for V, E, P, G, D, DI) from the Lean files, or
(for L and T) from the TLA+ files. Remove an ID and the gate must fail.
