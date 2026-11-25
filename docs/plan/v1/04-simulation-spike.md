# 04. Simulation spike: go or no-go

This is a spike. It is not a commitment. It has a time box, a question and numbers that end it.
Task T97 runs it. The owner decided that the spike runs, with the time box and the go and no-go numbers below. A no-go deletes the spike code and keeps one dated note.

## What exists today
| Item | What it does | Evidence |
|---|---|---|
| Seeded fake agent | A run draws from a random generator seeded with the seed and the run index. The same seed gives the same run | Verified: `src/willitharness/fakeagent.py` (`random.Random(f"{behavior.seed}:{run_index}")`) |
| Monte Carlo gate | Draws counts for two arms and checks the false-positive rate and the power of the verdict function. It does not run the runner | Verified: `scripts/gates/simulate.py`, run by the `simulate` target of the Makefile with a fixed seed |
| Trace replay | TLC takes seeded random walks of the lifecycle model. Each action is applied to the real lifecycle code | Verified: `uv run python formal/tla/replay_traces.py` prints a total line with walks, states compared and refusal probes. It replays the walks of the stored fixtures |
| Live run | A real agent run that costs money. It is the non-deterministic check | Verified: `scripts/gates/three_arm_live.sh` |

Inferred: the fake agent covers the run loop of the lifecycle. It does not cover a repository scan, a transcript read or a hook file.
The dossier said the same: it did not check how much of the real runner the fake agent covers.

## What the audit pipeline adds
| New surface | Why the current checks do not reach it |
|---|---|
| Reading a repository: files, symlinks, odd encodings, huge files | The lifecycle model has no file system |
| Reading session transcripts: thousands of files and gigabytes on this machine (see `01-goals-and-scope.md`) | The lifecycle model has no input data |
| Reading hook files in more than one format (the overwatch `hooks.json` is a module registry, not the Claude Code layout) | The v0 audit reads one layout |
| A budget across several plans in one audit | The lifecycle budget covers one plan |
| A runner that can be denied or can time out | Verified: the auto-mode classifier denied a paid run in an earlier session (dossier `willitharness-session-retrospective`). The fake agent never denies |
| The promise that nothing is written to the audited folder | A test checks fixtures. No check explores fault combinations |

## What the dossiers say
The user wrote these notes in the commonsense repository. They are evidence, not orders.

What the stream says, quoted from `tigerbeetle-resonate-deterministic-simulation-testing-stream.dossier.txt`:
- "if you seed yet another universe with the same seed, it unfolds exactly the same way".
- "Minimize surface area of the interface, make it very narrow.".
- "DST doesn't promise that. It just gives you confidence that as far as you're as far as you are exploring the state space".
- The first version of the TigerBeetle simulator took weeks to write. The dossier gives the number.
- A non-deterministic run is "like a canary because you should never be finding bugs there".

What the dossier warned:
- "The talk gives no data on how often deterministic simulation finds bugs a normal test suite misses."
- "the speakers are the vendors of the two products they describe", and every number is their own report from memory.
- The first simulator of TigerBeetle took weeks. The time box below is far shorter. The spike tests a much smaller thing.

What the dossier decided for this repository:
- `project=willitharness verdict=drop strength=moderate evaluated_at=2026-11-24`.
- Its reason: "The idea is already built, so the verdict is drop." It read the top of `simulate.py` and the Makefile only.
- A second dossier (`aws-formal-methods`) also moved willitharness to drop, because the replay of TLA+ walks through the lifecycle code exists.
- The trace validation note says trace validation "is not exhaustive". It reports two data-loss bugs from about a dozen runs, in the author's own project.

## Why this plan runs the spike anyway
1. The drop verdict judged the v0 runner. The v1 pipeline reads files, transcripts and hooks. The verdict did not cover them (Inferred, from the dates: the verdict is of 2026-11-24, before this plan).
2. The dossier states that it did not check how much of the real runner the fake agent covers. The spike measures that.
3. The owner wants spikes to decide, not dossiers.
4. The cost is bounded: one day. A no-go deletes the code. The spike has a number for each outcome.
5. The risk that the spike repeats work is real. The no-go rule below covers it: a defect that a one-fault test finds does not count.

## The narrow ports
The simulator controls four ports. The pipeline code must reach the world only through them.
| Port | Operations | What the simulator does with it |
|---|---|---|
| Agent runner | start a run, end a run, with cost and transcript | Returns an outcome from the seed. Can return Denied or Timeout |
| File system | read text, list a folder, stat, and write | Serves a fixture tree. Records every write. A write to the audited folder is a violation |
| Clock | now, and wait | Virtual time. A wait costs no real time |
| Budget | reserve, settle, spent | The existing ledger of `src/willitharness/budget.py`, driven by the fake runner |

Inferred: the audit code reads the file system directly today. The spike adds the port in the one module that reads.

## The fault list
Each fault is a seeded event. A run draws zero or more faults.
| Fault | Port | Invariant it tests |
|---|---|---|
| Runner returns Denied | Runner | SC5, the free report survives |
| Runner times out | Runner, Clock | SC3, the cap holds (A-CAP) |
| Runner cost above the run cap | Runner | SC3 |
| Runner returns a malformed transcript | Runner | SC5 |
| A transcript line is not JSON | File system | US4 |
| A transcript file is unreadable | File system | US4 |
| A transcript file is very large | File system, Clock | RO2, the free audit ends |
| A file in the folder is a symlink to a file outside it | File system | RO2, no read outside the folder |
| A hooks file is in a non-Claude layout | File system | IN3 |
| Another process writes into the folder during the audit | File system | RO1 |
| The output folder is inside the audited folder | File system | RO4 |
| The user gives a cap equal to the worst case | Budget | SC2 |
| Two paid steps in one audit | Budget | SC6 |

## The spike
- Name: S-SIM. Task T97.
- Smallest simulator: one script and one fixture tree (both new). The script runs the free audit and one paid step with the four ports faked. A seed in gives a trace out. After each run it checks the invariants RO1, RO2, SC1, SC3, SC4 and SC5.
- Question: does the simulator find a defect that the current gates miss, planted or real?
- Time box: 8 working hours. The spike stops at the box, whatever its state. [param]

### Method
1. Write 5 planted defects in a scratch copy of the pipeline. Each defect shows only under a fault. Proposed list: [param]
   - a timed-out run is charged 0, not the run cap;
   - a denied run raises and the free report is lost;
   - the free report reads a cached paid result;
   - a missing transcript folder makes the audit create it inside the audited folder;
   - a symlink in the folder is followed and its text enters the report.
2. Run the existing gates on each defect: the unit tests, the mutation modules, the trace gate, the repo checks and the TLA+ replay. Record which gates fail. This is the "gates miss" count.
3. Run the simulator on 1000 seeds for each defect. Record which defects it finds and the first seed that shows each. [param]
4. Check determinism: run the same seed twice for 100 seeds and compare the trace hash. [param]
5. Time the 1000-seed run. [param]

### Go criteria
All must hold.
| Criterion | Number |
|---|---|
| The simulator finds planted defects that the existing gates all miss | at least 3 of 5 [param] |
| Each counted defect needs two or more faults in one run. A one-fault defect has a cheaper unit test and does not count | every counted defect |
| Determinism: the same seed gives the same trace hash | 100 of 100 reruns [param] |
| The run of 1000 seeds ends in | at most 60 seconds on this machine [param] |
| The simulator script is at most | 400 lines [param] |
| The invariants and ports above are enough, with no port added | 4 ports [param] |

### No-go criteria
Any one ends the spike with no-go.
| Criterion | Number |
|---|---|
| The simulator finds fewer than 3 defects that the gates miss | fewer than 3 of 5 [param] |
| The pipeline cannot reach the world through 4 ports without a rewrite larger than the box | over 8 hours [param] |
| Determinism fails once | 1 divergence in 100 reruns [param] |
| The 1000-seed run is slower than | 60 seconds [param] |
| The existing gates already find 3 or more of the 5 defects | the gates are enough [param] |

### What each result decides
| Result | Decision |
|---|---|
| Go | Add the simulator to `make check` as one more target. Keep the ports. Open a task to widen the fault list |
| No-go with gates missing 1 or 2 defects | Add one failing-first test for each missed defect class. Delete the simulator [param] |
| No-go with gates catching 3 or more | Delete the simulator. Record that the gates are enough [param] |

The result goes in a dated note in this folder. It states the counts and the first seed of each find.
The baseline cost is the seconds of the full check target of the Makefile. The spike measures it first and reports it.

## Limits
- Five planted defects are written by the plan author. They may fit the simulator. A real defect found counts above a planted one.
- The simulator checks logic under faults. It does not check the real `claude` CLI. The live run stays the canary.
- A pass does not prove the absence of defects. It gives confidence over the faults explored (quote above).
