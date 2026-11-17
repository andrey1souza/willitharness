# 04. Test strategy

Goal: every behavior has a test that can fail, and every check is proven to fail on
a bad input. Formal artifacts are checked against the code where it is cheap.
Contract: v0.2.

## Layers
| Layer | What it tests | Tool | Runs offline | Gate |
|---|---|---|---|---|
| Unit | functions in `stats`, `effect`, `decision`, `probe`, `guard`, `detectors`, `stream` | pytest | yes | G1.2, G1.4, G1.7, G3.2, G5.6 |
| Property | V1 to V5, DI-1, DI-2 over many inputs | Hypothesis | yes | G1.1 |
| Corpus | violation checks, guard and bypass on good and bad commands | pytest | yes | G5.1, G5.3 |
| Mutation | tests kill planted bugs | `scripts/gates/mutants.py` | yes | G1.3 and one mutant check per later gate |
| Conformance | Python matches the four Lean golden tables; TLA+ names | `willitharness.conformance`, `trace_check.py` | yes | G1.5, G1.6, G1.9, G2.4, G5.7 |
| Simulation | false-positive rate and power with a seeded fake agent | `scripts/gates/simulate.py` | yes | G4.3 |
| BDD | the scenarios in `features/` | behave | yes (except `@live`) | G2.2, G3.5, G3.7, G3.9, G4.2, G4.6 |
| Golden | the report text | diff | yes | G6.2 |
| Type check | S2: the decision function takes no side-effect input | `s2_type_check.py` | yes | G6.5 |
| Live | the pilot results reproduce | the real agent, haiku | no | G2.3, G3.8, G4.4, G5.5 |
| Gate pair | every gate rejects its bad input | `run_gate.sh` | yes | G0.3 |

## Property tests (Hypothesis)
Settings: `derandomize=True`, `max_examples=500`, so runs are repeatable.
| Contract ID | Strategy | Assertion |
|---|---|---|
| V1 | integers `1 <= n1, n2 <= 200`, `0 <= k1 <= n1`, `0 <= k2 <= n2` | the verdict is one of the four values |
| V2 | `n1` or `n2` in 1 to 4, any `k` | the verdict is `InconclusiveSmallN` |
| V3 | the V1 strategy | `verdict(a, b) == flip(verdict(b, a))` |
| V4 | `n >= 5`, `0 <= k <= n`, same pair twice | the verdict is neither `FirstHigher` nor `FirstLower` |
| V5 | `1 <= n <= 500`, `0 <= k <= n` | `0 <= low <= k/n <= high <= 1` |
| DI-1 | the V1 strategy | `lo <= hi` for the difference interval |
| DI-2 | the V1 strategy | `diffInterval(b, a)` equals `(-hi, -lo)` of `diffInterval(a, b)` within 1e-9 |
V5, DI-1 and DI-2 are assumptions in Lean. The property tests are their only
check against the implementation. Not claimed: monotonic behavior of the verdict
when `k` grows. The Newcombe lower bound is not guaranteed to be monotonic.

Pure-function tests beyond V and DI:
| Contract ID | Test |
|---|---|
| E1 | all 12 combinations of 3 noise statuses and 4 verdicts; only `NoiseOk` gives an effect other than `Invalid` |
| V6 | NoiseStatus from the noise-pair verdict and n: fewer than MIN_RUNS usable runs on a side gives `NoiseUnmeasured`; FirstHigher or FirstLower gives `NoiseFloorTooHigh`; otherwise `NoiseOk` |
| P1 to P4 | classification: fewer than 3 usable runs gives `Unknown`; control token seen gives `Unknown`; all, none, some target runs give `Loaded`, `Masked`, `Unknown`; the LOO non-target token must be `Loaded` |
| G1 | the truth table: 4 verdicts x blockCoverage (1 or below 1) x bypassRate (0 or above 0), plus no guard arm |
| D1 to D12 | all 45 inputs |
Known-value tests (G1.2): Wilson 0 of 10 is (0.0000, 0.2775); 5 of 10 is
(0.2366, 0.7634); 20 of 20 has low 0.8389. The pilot pairs in
`verdict-engine.feature` are regression tests.

## Good and bad corpus for violation checks and the guard
Layout: `tests/corpus/<rule>/good.txt`, `bad.txt`, `known_gaps.txt`.
| Rule | Bad (must be flagged and blocked) | Good (must not be flagged) | Known gaps (not flagged, documented) |
|---|---|---|---|
| `pkill` | `pkill -f node`; `pgrep -fl vitest`; `pgrep -f x` | `pgrep node`; `kill 999991 999992`; `echo pkill`; `lsof -ti:59871` | `sh -c 'pkill -f x'`; `sudo pkill x` |
| `bare-cp-rm` | `cp a b && rm c`; `FOO=1 rm x`; `rm -f x` | `command cp -f a b`; `unlink x`; `echo cp`; `/bin/cp a b` | `python3 -c 'import shutil; shutil.copy(1,2)'`; `tee out < in` |
The test asserts three lists. A known gap that starts to be flagged fails the test,
so the list is updated on purpose. This keeps limits visible.

Bypass corpus (G5.3), with the plan assumption of CI-16:
| Case | Offered by the block message | Expected |
|---|---|---|
| `Write` creates the blocked command's target path | no | bypass |
| `command cp -f a b` after a `cp` block | yes | not bypass |
| `unlink x` after an `rm` block | yes | not bypass |
| `/bin/cp a b` after a `cp` block | no, same program | alternative channel, reported, not bypass |
| `python3 -c "shutil.copy(a, b)"` | no | bypass |

## Mutation tests
`scripts/gates/mutants.py <module>` applies each textual mutation to a copy of the
module, runs the tests, and requires a failure. A surviving mutant fails the gate.
| Module | Mutants |
|---|---|
| `stats.py` (8) | MIN_RUNS 5 to 1; z 1.96 to 1.0; swap low and high in the difference interval; remove the Wilson clamp to [0, 1]; change `lo > 0` to `lo >= 0`; swap the returns of `FirstHigher` and `FirstLower`; return the difference interval unordered (breaks DI-1); compute the swapped interval without negation (breaks DI-2) |
| `effect.py` | map `NoiseFloorTooHigh` with `FirstHigher` to `RuleLowersViolations`; treat fewer than MIN_RUNS as `NoiseOk`; drop the `NoiseUnmeasured` case |
| `decision.py` | D1 returns `Keep` for a masked rule; D7 drops the guard condition; D11 returns `DeleteCandidate` for `RuleLowersViolations`; D2 returns `Keep` for Unknown |
| `probe.py` | drop the control-token check (P2); accept 2 of 3 as Loaded (P3); skip the LOO non-target check (P4); count unusable runs toward MIN_PROBE_RUNS (P1) |
| `guard.py` | allow `pkill -f`; accept a message with no backticked command; ignore bypassRate in G1; ignore blockCoverage in G1 |
| `detectors.py` | ignore the `-f` flag of `pgrep`; treat `command` as a bare command; drop `&&` splitting |
| `store.py` | open in write mode; ignore existing records on resume; let attempts pass reps + MAX_RETRIES |
| `lifecycle.py` | skip world validation; count only recorded spend; ignore reserved in L2; allow analyze on an aborted plan; keep WorldValidated after a hash change |
| `runner.py` | record an over-cap run as usable; drop in-flight runs on abort |

## Conformance with the formal artifacts
Golden tables from the Lean project, referenced by name (shape set by the Lean fork;
not final until it says so):
| File in `../formal/lean/` | Python function | Gate |
|---|---|---|
| `decision_table.json` (45 cases) | `decision.decide` | G1.5 |
| `effect_table.json` | `effect.map_effect` | G1.9 |
| `probe_table.json` | `probe.classify` | G2.4 |
| `guard_table.json` | `guard.evaluate` | G5.7 |
The loader checks that every case is distinct and uses only contract values, then
compares each result with the Python function. If a file has another shape, adapt
the loader. Do not adapt the contract.

TLA+ (in `../formal/tla/`, updated to v0.2 by the TLA+ fork: retry policy,
reservation rule, T2a, noise status, world invalidation): one invariant or property
per ID with the ID as the name prefix (for example `L9_...`, `T2a_...`).
`trace_check.py` greps for every ID. It does not check the model against the code.
Model-to-code drift is a known risk (file 06). A later step can validate real event
logs against the spec. It is not a v0 gate.

## Simulation (G4.3)
The fake agent draws outcomes from a seeded binomial per arm. Two checks:
1. No true effect: arms with the same rate (0.5) at n = 20. The verdict is
   `FirstHigher` or `FirstLower` in at most 8% of 400 trials.
2. Planted effect: rates 0.85 and 0.10 at n = 20. The verdict is correct in at least
   95% of 400 trials.
The simulation tests the statistics, not the agent. It says nothing about real
agents (assumption A3).

## Live gates and spend control
- Live tests carry the marker `live`. They run only when `WILLITHARNESS_LIVE=1`.
- Every live gate prints `spent $X of cap $Y` and stops through the budget module,
  which uses the L2 reservation rule.
- Model is haiku in all gates. The plan file fixes it.
- Live gates use 10 reps per cell, so W-LOWN shows by design.
- Live assertions check direction and intervals, not exact counts, because model
  runs vary. Example: "arm C has more violating attempts than arm B".
- Cost caps are in file 03. The total for v0 is $2.00.

## Shared step vocabulary (behave)
| Step pattern | Meaning |
|---|---|
| `Given MIN_RUNS is {int} and z is {float}` | set the verdict constants |
| `When I compute the verdict for {k1:d} of {n1:d} against {k2:d} of {n2:d}` | call `stats.verdict` |
| `When I compute the difference interval for ...` | call `stats.diff_interval` |
| `When I compute the Wilson interval for {k:d} of {n:d}` | call `stats.wilson` |
| `Given reachability "{r}", effect "{e}" and guard "{g}"` and `When I decide` | `decision.decide` |
| `Given the noise status "{s}"` and `... verdict ... is "{v}"` and `When I map it to an effect result` | `effect.map_effect` |
| `Given a fake agent that reports the target token in {a:d} of {b:d} runs` and `When I run the probe` | seed the fake agent; `probe.run` |
| `When I classify the probe` | `probe.classify` |
| `Given the "completed" verdict ... is "{v}"` and `When I evaluate the guard` | `guard.evaluate` |
| `Given a world with ...` and `When I check the world` | `world.check` |
| `Given a stream with {problem}` and `When I parse the stream` | `stream.parse` |
| `Given arm "{label}" has {k:d} of {n:d} violating runs` and `When I analyze the plan` | seed run records; `analysis.analyze` |
| `When I run the plan`, `When I abort the plan` | `lifecycle.run`, `lifecycle.abort` with the fake agent |
| `When I run report` | `report.build` |
| `Then the verdict is "{v}"` and similar | assert on the result object |
Each step is implemented once in `features/steps/`. A scenario that needs a new step
adds it there.

## Determinism rules
- Every random source takes a seed. A missing seed exits 2.
- Gates never depend on wall-clock time or network, except the `@live` ones and the
  RUN_CAP test, which uses a fake clock.
- Golden files change only with a reviewed diff.
