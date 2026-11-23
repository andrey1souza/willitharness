import Willitharness

open Willitharness

def verdictName : Verdict → String
  | .inconclusiveSmallN => "InconclusiveSmallN"
  | .firstHigher => "FirstHigher"
  | .firstLower => "FirstLower"
  | .inconclusive => "Inconclusive"

def noiseName : NoiseStatus → String
  | .noiseUnmeasured => "NoiseUnmeasured"
  | .noiseFloorTooHigh => "NoiseFloorTooHigh"
  | .noiseOk => "NoiseOk"

def completedName : Option Verdict → String
  | none => "NoGuardArm"
  | some v => verdictName v

def boolName (b : Bool) : String := if b then "true" else "false"

def jsonList (rows : List String) : String :=
  "[\n" ++ ",\n".intercalate rows ++ "\n]"

def decisionRow (r : Reach) (e : EffectResult) (g : GuardResult) : String :=
  "  {\"reach\": \"" ++ r.name ++ "\", \"effect\": \"" ++ e.name ++
    "\", \"guard\": \"" ++ g.name ++ "\", \"decision\": \"" ++ (decideRule r e g).name ++ "\"}"

def effectRow (n : NoiseStatus) (v : Verdict) : String :=
  "  {\"noise\": \"" ++ noiseName n ++ "\", \"verdict\": \"" ++ verdictName v ++
    "\", \"effect\": \"" ++ (effectOf n v).name ++ "\"}"

def probeRow (runs t c : Nat) : String :=
  "  {\"runs\": " ++ toString runs ++ ", \"targetHits\": " ++ toString t ++
    ", \"controlHits\": " ++ toString c ++ ", \"result\": \"" ++ (probeResult runs t c).name ++ "\"}"

def guardRow (cv : Option Verdict) (coverage : Coverage) (zeroBypass : Bool) : String :=
  "  {\"completed\": \"" ++ completedName cv ++ "\", \"coverage\": \"" ++ coverage.name ++
    "\", \"bypassRateZero\": " ++ boolName zeroBypass ++ ", \"guard\": \"" ++
    (guardOfBool cv coverage zeroBypass).name ++ "\"}"

def reportedRow (p : PlanFacts) : String :=
  "  {\"hasNoisePair\": " ++ boolName p.hasNoisePair ++ ", \"noise\": \"" ++ noiseName p.noise ++
    "\", \"looProbe\": \"" ++ p.looProbe.name ++ "\", \"ruleReach\": \"" ++ p.ruleReach.name ++
    "\", \"canReport\": " ++ boolName (decide (CanReport p)) ++ "}"

def armRow (p n : Verdict) (clean : Bool) : String :=
  "  {\"promptVsComponent\": \"" ++ verdictName p ++ "\", \"nothingVsComponent\": \"" ++
    verdictName n ++ "\", \"nothingClean\": " ++ boolName clean ++ ", \"verdict\": \"" ++
    (threeArmVerdict p n clean).name ++ "\"}"

def placeboRow (p n c : Verdict) (clean : Bool) : String :=
  "  {\"placeboVsComponent\": \"" ++ verdictName p ++ "\", \"nothingVsPlacebo\": \"" ++
    verdictName n ++ "\", \"nothingVsComponent\": \"" ++ verdictName c ++
    "\", \"nothingClean\": " ++ boolName clean ++ ", \"verdict\": \"" ++
    (contentVerdict p n c clean).name ++ "\"}"

def maxProbeRuns : Nat := 6

def decisionTable : String :=
  jsonList (allInputs.map fun (r, e, g) => decisionRow r e g)

def effectTable : String :=
  jsonList (allNoise.flatMap fun n => allVerdict.map fun v => effectRow n v)

def probeTable : String :=
  jsonList ((List.range (maxProbeRuns + 1)).flatMap fun runs =>
    (List.range (runs + 1)).flatMap fun t => (List.range (runs + 1)).map fun c => probeRow runs t c)

def guardTable : String :=
  let completedValues : List (Option Verdict) := none :: allVerdict.map some
  jsonList (completedValues.flatMap fun cv =>
    allCoverage.flatMap fun coverage => [false, true].map fun zeroBypass =>
      guardRow cv coverage zeroBypass)

def reportedTable : String :=
  jsonList (allPlanFacts.map reportedRow)

def armsTable : String :=
  jsonList (allArmInputs.map fun (p, n, clean) => armRow p n clean)

def placeboTable : String :=
  jsonList (allContentInputs.map fun (p, n, c, clean) => placeboRow p n c clean)

def main (args : List String) : IO UInt32 := do
  match args with
  | ["decision"] => IO.println decisionTable; return 0
  | ["effect"] => IO.println effectTable; return 0
  | ["probe"] => IO.println probeTable; return 0
  | ["guard"] => IO.println guardTable; return 0
  | ["reported"] => IO.println reportedTable; return 0
  | ["arms"] => IO.println armsTable; return 0
  | ["placebo"] => IO.println placeboTable; return 0
  | _ =>
    IO.eprintln "usage: export_table decision|effect|probe|guard|reported|arms|placebo"
    return 2
