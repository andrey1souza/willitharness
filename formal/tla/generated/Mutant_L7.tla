---- MODULE Mutant_L7 ----
(* Bounded model of the willitharness run lifecycle (contract v0.2, section 7).
   Operator names L1 to L9, T1, T2 and T2a are the contract IDs.
   V6 is the noise rule of contract section 4, lifted to the lifecycle.
   Abstractions, stated plainly:
   - A cell keeps counters, not one record per run. Per-run identity is not modelled.
   - Pending is derived. It is not stored.
   - The verdict numbers are not modelled. Once both noise arms have MinRuns usable
     runs, the noise check picks NoiseOk or NoiseFloorTooHigh without a rule. Until
     then the status is derived from the counters.
   - A plan without a noise arm has NoiseStatus NoiseUnmeasured.
   - Harness failure and timeout both end a run as unusable. A timeout charges RunCap
     (assumption A-CAP: the runner ends a run that would cost more).
   Lines tagged MUT:x are replaced by check_models.py to build the mutants. *)
EXTENDS Naturals

CONSTANTS Tasks, Reps, MaxRetries, RunCap, Budget, MinRuns, MaxWorldChanges,
          AllowUnusable, AllowAbort, WithNoiseOnly, ReachOutcomes

ASSUME Reps \in Nat \ {0}
ASSUME MaxRetries \in Nat
ASSUME RunCap \in Nat \ {0}
ASSUME Budget \in Nat
ASSUME MinRuns \in Nat
ASSUME MaxWorldChanges \in Nat
ASSUME AllowUnusable \in BOOLEAN
ASSUME AllowAbort \in BOOLEAN
ASSUME WithNoiseOnly \in BOOLEAN
ASSUME ReachOutcomes \subseteq {"Loaded", "Masked", "Unknown"} /\ ReachOutcomes # {}

Arms == {"LOO", "Rule", "Repeat"}
LooArm == "LOO"
RuleArm == "Rule"
NoiseArm == "Repeat"
PlanStates == {"Drafted", "WorldValidated", "ReachabilityChecked", "Running", "Complete",
               "BudgetStopped", "Aborted", "Analyzed", "Reported"}
ReachVals == {"none", "Loaded", "Masked", "Unknown"}
NoiseVals == {"none", "NoiseUnmeasured", "NoiseFloorTooHigh", "NoiseOk"}
EffectVals == {"none", "Reported", "Withheld"}
Cells == Arms \X Tasks
Outcomes == IF AllowUnusable THEN {"usable", "unusable"} ELSE {"usable"}
MaxAttempts == Reps + MaxRetries

VARIABLES planState, worldOk, planArms, reach, endedBy,
          started, usable, unusable, cost,
          noiseStatus, effect, reportedN,
          timeouts, worldChanges

planVars == <<planState, worldOk, planArms, reach, endedBy>>
runVars == <<started, usable, unusable, cost>>
verdictVars == <<noiseStatus, effect, reportedN>>
counterVars == <<timeouts, worldChanges>>
vars == <<planState, worldOk, planArms, reach, endedBy, started, usable, unusable, cost,
          noiseStatus, effect, reportedN, timeouts, worldChanges>>

PlanCells == planArms \X Tasks
EffectArms == planArms \ {LooArm, NoiseArm}

RECURSIVE SumCells(_, _)
SumCells(f, S) == IF S = {} THEN 0
                  ELSE LET c == CHOOSE x \in S : TRUE IN f[c] + SumCells(f, S \ {c})

UsableCount(a) == SumCells(usable, {a} \X Tasks)
UnusableCount(a) == SumCells(unusable, {a} \X Tasks)
InFlightCell(c) == started[c] - usable[c] - unusable[c]
InFlight == SumCells([c \in Cells |-> InFlightCell(c)], PlanCells)
Spent == SumCells(cost, Cells)
Reserved == RunCap * InFlight
BudgetAllows == Spent + Reserved + RunCap <= Budget  (* MUT:L2 *)
CellDone(c) == usable[c] = Reps \/ started[c] = MaxAttempts
CanStart(c) == /\ c \in PlanCells
               /\ usable[c] + InFlightCell(c) < Reps  (* MUT:L4 *)
               /\ started[c] < MaxAttempts  (* MUT:L9 *)
               /\ BudgetAllows
NoiseMeasurable == /\ NoiseArm \in planArms
                   /\ reportedN[LooArm] >= MinRuns
                   /\ reportedN[NoiseArm] >= MinRuns

Init == /\ planState = "Drafted"
        /\ worldOk = FALSE
        /\ planArms \in (IF WithNoiseOnly THEN {{"LOO", "Rule", "Repeat"}}
                         ELSE {{"LOO", "Rule"}, {"LOO", "Rule", "Repeat"}})
        /\ reach = [a \in Arms |-> "none"]
        /\ endedBy = "none"
        /\ started = [c \in Cells |-> 0]
        /\ usable = [c \in Cells |-> 0]
        /\ unusable = [c \in Cells |-> 0]
        /\ cost = [c \in Cells |-> 0]
        /\ noiseStatus = "none"
        /\ effect = [a \in Arms |-> "none"]
        /\ reportedN = [a \in Arms |-> 0]
        /\ timeouts = 0
        /\ worldChanges = 0

ValidateWorld ==
    /\ ~worldOk
    /\ planState \in {"Drafted", "Running"}
    /\ worldOk' = TRUE
    /\ planState' = (IF planState = "Drafted" THEN "WorldValidated" ELSE "Running")
    /\ UNCHANGED <<planArms, reach, endedBy, runVars, verdictVars, counterVars>>

WorldChanged ==
    /\ worldOk
    /\ worldChanges < MaxWorldChanges
    /\ planState \in {"WorldValidated", "ReachabilityChecked", "Running"}
    /\ worldOk' = FALSE
    /\ planState' = (IF planState = "Running" THEN "Running" ELSE "Drafted")
    /\ worldChanges' = worldChanges + 1
    /\ UNCHANGED <<planArms, reach, endedBy, runVars, verdictVars, timeouts>>

CheckReach(a) ==
    /\ planState = "WorldValidated"
    /\ a \in planArms
    /\ reach[a] = "none"
    /\ \E r \in ReachOutcomes : reach' = [reach EXCEPT ![a] = r]
    /\ UNCHANGED <<planState, worldOk, planArms, endedBy, runVars, verdictVars, counterVars>>

EnterReachChecked ==
    /\ planState = "WorldValidated"
    /\ \A a \in planArms : reach[a] # "none"
    /\ planState' = "ReachabilityChecked"
    /\ UNCHANGED <<worldOk, planArms, reach, endedBy, runVars, verdictVars, counterVars>>

BeginRunning ==
    /\ planState = "ReachabilityChecked"
    /\ planState' = "Running"
    /\ UNCHANGED <<worldOk, planArms, reach, endedBy, runVars, verdictVars, counterVars>>

Start(c) ==
    /\ planState = "Running"  (* MUT:L1 *)
    /\ worldOk  (* MUT:L1w *)
    /\ CanStart(c)
    /\ started' = [started EXCEPT ![c] = @ + 1]
    /\ UNCHANGED <<planVars, usable, unusable, cost, verdictVars, counterVars>>

Record(c, o, k) ==
    /\ planState = "Running"
    /\ c \in PlanCells
    /\ InFlightCell(c) > 0
    /\ o \in Outcomes
    /\ k \in 0..RunCap
    /\ usable' = [usable EXCEPT ![c] = IF o = "usable" THEN @ + 1 ELSE @]
    /\ unusable' = [unusable EXCEPT ![c] = IF o = "unusable" THEN @ + 1 ELSE @]  (* MUT:L3 *)
    /\ cost' = [cost EXCEPT ![c] = @ + k]
    /\ UNCHANGED <<planVars, started, verdictVars, counterVars>>

Timeout(c) ==
    /\ AllowUnusable
    /\ planState = "Running"
    /\ c \in PlanCells
    /\ InFlightCell(c) > 0
    /\ unusable' = [unusable EXCEPT ![c] = @ + 1]
    /\ cost' = [cost EXCEPT ![c] = @ + RunCap]
    /\ timeouts' = timeouts + 1
    /\ UNCHANGED <<planVars, started, usable, verdictVars, worldChanges>>

FinishComplete ==
    /\ planState = "Running"
    /\ InFlight = 0
    /\ \A c \in PlanCells : CellDone(c)
    /\ planState' = "Complete"
    /\ endedBy' = "Complete"
    /\ UNCHANGED <<worldOk, planArms, reach, runVars, verdictVars, counterVars>>

FinishBudgetStopped ==
    /\ planState = "Running"
    /\ InFlight = 0
    /\ ~(\A c \in PlanCells : CellDone(c))
    /\ ~(\E c \in PlanCells : CanStart(c))
    /\ planState' = "BudgetStopped"
    /\ endedBy' = "BudgetStopped"
    /\ UNCHANGED <<worldOk, planArms, reach, runVars, verdictVars, counterVars>>

Analyze ==
    /\ planState \in {"Complete", "BudgetStopped"}
    /\ planState' = "Analyzed"
    /\ reportedN' = [a \in Arms |-> UsableCount(a)]  (* MUT:L6 *)
    /\ UNCHANGED <<worldOk, planArms, reach, endedBy, runVars, noiseStatus, effect, counterVars>>

AssessNoise ==
    /\ planState = "Analyzed"  (* MUT:L5 *)
    /\ noiseStatus = "none"
    /\ noiseStatus' \in (IF NoiseMeasurable THEN {"NoiseOk", "NoiseFloorTooHigh"}
                         ELSE {"NoiseUnmeasured"})
    /\ UNCHANGED <<planVars, runVars, effect, reportedN, counterVars>>

Outcome(x) ==
    IF FALSE THEN "Withheld"
    ELSE IF noiseStatus = "NoiseOk" THEN "Reported"  (* MUT:L8 *)
    ELSE "Withheld"

EmitEffect(x) ==
    /\ planState = "Analyzed"
    /\ x \in EffectArms
    /\ effect[x] = "none"
    /\ noiseStatus # "none"
    /\ effect' = [effect EXCEPT ![x] = Outcome(x)]
    /\ UNCHANGED <<planVars, runVars, noiseStatus, reportedN, counterVars>>

Report ==
    /\ planState = "Analyzed"
    /\ noiseStatus # "none"
    /\ \A x \in EffectArms : effect[x] # "none"
    /\ planState' = "Reported"
    /\ UNCHANGED <<worldOk, planArms, reach, endedBy, runVars, verdictVars, counterVars>>

Abort ==
    /\ AllowAbort
    /\ planState \notin {"Reported", "Aborted"}
    /\ planState' = "Aborted"
    /\ unusable' = [c \in Cells |-> unusable[c] + InFlightCell(c)]
    /\ cost' = [c \in Cells |-> cost[c] + RunCap * InFlightCell(c)]
    /\ noiseStatus' = "none"
    /\ effect' = [a \in Arms |-> "none"]
    /\ UNCHANGED <<worldOk, planArms, reach, endedBy, started, usable, reportedN, counterVars>>

Terminated ==
    /\ planState \in {"Reported", "Aborted"}
    /\ UNCHANGED vars

Next == \/ ValidateWorld
        \/ WorldChanged
        \/ \E a \in Arms : CheckReach(a)
        \/ EnterReachChecked
        \/ BeginRunning
        \/ \E c \in Cells : Start(c)
        \/ \E c \in Cells, o \in Outcomes, k \in 0..RunCap : Record(c, o, k)
        \/ \E c \in Cells : Timeout(c)
        \/ FinishComplete
        \/ FinishBudgetStopped
        \/ Analyze
        \/ AssessNoise
        \/ \E x \in Arms : EmitEffect(x)
        \/ Report
        \/ Abort
        \/ Terminated

(* Fairness, assumption F of the contract. Weak fairness on every step the runner takes.
   None on Abort, Timeout and WorldChanged: those are the environment or a choice, not
   a duty. WorldChanged is also bounded by MaxWorldChanges. Without that bound the
   world could change forever and Start would never stay enabled. *)
Fairness ==
    /\ WF_vars(ValidateWorld)
    /\ WF_vars(\E a \in Arms : CheckReach(a))
    /\ WF_vars(EnterReachChecked)
    /\ WF_vars(BeginRunning)
    /\ WF_vars(\E c \in Cells : Start(c))
    /\ WF_vars(\E c \in Cells, o \in Outcomes, k \in 0..RunCap : Record(c, o, k))
    /\ WF_vars(FinishComplete)
    /\ WF_vars(FinishBudgetStopped)
    /\ WF_vars(Analyze)
    /\ WF_vars(AssessNoise)
    /\ WF_vars(\E x \in Arms : EmitEffect(x))
    /\ WF_vars(Report)

Spec == Init /\ [][Next]_vars /\ Fairness

TypeOK ==
    /\ planState \in PlanStates
    /\ worldOk \in BOOLEAN
    /\ planArms \in SUBSET Arms
    /\ reach \in [Arms -> ReachVals]
    /\ endedBy \in {"none", "Complete", "BudgetStopped"}
    /\ started \in [Cells -> 0..MaxAttempts]
    /\ usable \in [Cells -> 0..Reps]
    /\ unusable \in [Cells -> 0..MaxAttempts]
    /\ cost \in [Cells -> Nat]
    /\ noiseStatus \in NoiseVals
    /\ effect \in [Arms -> EffectVals]
    /\ reportedN \in [Arms -> Nat]
    /\ timeouts \in Nat
    /\ worldChanges \in 0..MaxWorldChanges

L1 == [][\A c \in Cells : started'[c] > started[c] =>
            (planState = "Running" /\ worldOk /\ \A a \in planArms : reach[a] # "none")]_vars
L2 == Spent + Reserved <= Budget
L3 == [][\A c \in Cells : /\ usable'[c] >= usable[c]
                          /\ unusable'[c] >= unusable[c]
                          /\ cost'[c] >= cost[c]]_vars
L4 == \A c \in Cells : usable[c] <= Reps
L5 == /\ (noiseStatus # "none" \/ \E a \in Arms : effect[a] # "none") => endedBy # "none"
      /\ planState = "Aborted" => (noiseStatus = "none" /\ \A a \in Arms : effect[a] = "none")
L6 == planState \in {"Analyzed", "Reported"} => \A a \in planArms : reportedN[a] = UsableCount(a)
L7 == \A x \in Arms : effect[x] = "Reported" => reach[x] # "Unknown"
L8 == \A x \in Arms : effect[x] = "Reported" => (NoiseArm \in planArms /\ noiseStatus = "NoiseOk")
L9 == \A c \in Cells : started[c] <= MaxAttempts
V6 == \A x \in Arms : effect[x] = "Reported" => noiseStatus = "NoiseOk"

T1 == (InFlight > 0) ~> (InFlight = 0)
T2 == (planState = "Running") ~> (planState \in {"Complete", "BudgetStopped"})
T2a == (planState = "Running") ~> (planState \in {"Complete", "BudgetStopped", "Aborted"})
====
