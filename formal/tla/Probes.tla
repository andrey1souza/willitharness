---- MODULE Probes ----
(* Each probe says that something never happens. TLC reports a violation when it can,
   and the trace is the proof that the state is reachable. So an invariant of
   WillItHarness cannot hold only because the state it guards is unreachable.
   The runner expects every probe to be violated in the scenario named in
   check_models.py. *)
EXTENDS WillItHarness

NeverBudgetStopped == planState # "BudgetStopped"
NeverReported == planState # "Reported"
NeverUnusableRun == \A c \in Cells : unusable[c] = 0
NeverTimeout == timeouts = 0
NeverExtraAttempt == \A c \in Cells : started[c] <= Reps
NeverAttemptCapReached == \A c \in Cells : started[c] < MaxAttempts
NeverNoiseOk == noiseStatus # "NoiseOk"
NeverNoiseTooHigh == noiseStatus # "NoiseFloorTooHigh"
NeverNoiseUnmeasured == noiseStatus # "NoiseUnmeasured"
NeverNoPairReported == ~(planState = "Reported" /\ NoiseArm \notin planArms)
NeverEffectReported == \A x \in Arms : effect[x] # "Reported"
NeverWithheldForUnknown == \A x \in Arms : ~(effect[x] = "Withheld" /\ reach[x] = "Unknown")
NeverAborted == planState # "Aborted"
NeverAbortAfterVerdict == ~(planState = "Aborted" /\ endedBy # "none")
NeverReachMasked == \A a \in Arms : reach[a] # "Masked"
NeverWorldChanged == worldChanges = 0
NeverStartBlockedByWorld == ~(planState = "Running" /\ ~worldOk /\ \E c \in PlanCells : CanStart(c))
====
