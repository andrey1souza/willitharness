import Willitharness

open Willitharness

namespace Wrong

def wrongMaskedKeep : Reach → EffectResult → GuardResult → Decision
  | .masked, _, _ => .keep
  | r, e, g => decideRule r e g

theorem wrong_D1_masked_keep (e : EffectResult) (g : GuardResult) :
    wrongMaskedKeep .masked e g = .fixLoading := by
  rfl

def wrongDeleteWhenGuardWorse : Reach → EffectResult → GuardResult → Decision
  | .loaded, .ruleLowersViolations, .guardWorse => .deleteCandidate
  | r, e, g => decideRule r e g

theorem wrong_D11_delete_when_rule_lowers (r : Reach) (g : GuardResult) :
    wrongDeleteWhenGuardWorse r .ruleLowersViolations g ≠ .deleteCandidate := by
  cases r <;> cases g <;> simp [wrongDeleteWhenGuardWorse, decideRule]

def wrongVerdictNoSmallNGuard [DiffOracle] (a b : Counts) : Verdict :=
  if 0 < (DiffOracle.diff a b).1 then .firstHigher
  else if (DiffOracle.diff a b).2 < 0 then .firstLower
  else .inconclusive

theorem wrong_V2_no_small_n_guard [DiffOracle] (a b : Counts) (h : min a.n b.n < MinRuns) :
    wrongVerdictNoSmallNGuard a b = .inconclusiveSmallN := by
  unfold wrongVerdictNoSmallNGuard
  split <;> simp_all

def wrongVerdictNonStrict [DiffOracle] (a b : Counts) : Verdict :=
  if min a.n b.n < MinRuns then .inconclusiveSmallN
  else if 0 ≤ (DiffOracle.diff a b).1 then .firstHigher
  else if (DiffOracle.diff a b).2 < 0 then .firstLower
  else .inconclusive

theorem wrong_V4_non_strict_lower_bound [DiffOracle] (c : Counts) :
    wrongVerdictNonStrict c c ≠ .firstHigher := by
  unfold wrongVerdictNonStrict
  split <;> simp_all

def wrongEffectUnmeasuredOk : NoiseStatus → Verdict → EffectResult
  | .noiseFloorTooHigh, _ => .invalid
  | .noiseUnmeasured, v => effectOf .noiseOk v
  | .noiseOk, v => effectOf .noiseOk v

theorem wrong_E1_unmeasured_maps_to_ok (v : Verdict) :
    wrongEffectUnmeasuredOk .noiseUnmeasured v = .invalid := by
  cases v <;> rfl

def wrongProbeIgnoresControl (runs t _c : Nat) : Reach :=
  if runs < MinProbeRuns then .unknown
  else if t = runs then .loaded
  else if t = 0 then .masked
  else .unknown

theorem wrong_P2_control_ignored (runs t c : Nat) (h : 0 < c) :
    wrongProbeIgnoresControl runs t c = .unknown := by
  unfold wrongProbeIgnoresControl
  split <;> simp_all

def wrongGuardIgnoresBypass : Option Verdict → Rat → Rat → GuardResult
  | none, _, _ => .guardUntested
  | some completed, blockCoverage, _ =>
    if completed ≠ .firstLower ∧ completed ≠ .inconclusiveSmallN ∧ blockCoverage = 1
    then .guardMatchesRule else .guardWorse

theorem wrong_G1_bypass_ignored (cv : Option Verdict) (bc br : Rat) (h : br ≠ 0) :
    wrongGuardIgnoresBypass cv bc br ≠ .guardMatchesRule := by
  cases cv with
  | none => simp [wrongGuardIgnoresBypass]
  | some v => simp [wrongGuardIgnoresBypass]

end Wrong
