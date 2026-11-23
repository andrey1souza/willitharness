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

def wrongGuardIgnoresBypass : Option Verdict → Coverage → Rat → GuardResult
  | none, _, _ => .guardUntested
  | some completed, coverage, _ =>
    if GuardEvidenceMissing completed coverage then .guardUntested
    else if completed ≠ .firstLower ∧ completed ≠ .inconclusiveSmallN ∧ coverage = .full
    then .guardMatchesRule else .guardWorse

theorem wrong_G1_bypass_ignored (cv : Option Verdict) (cov : Coverage) (br : Rat) (h : br ≠ 0) :
    wrongGuardIgnoresBypass cv cov br ≠ .guardMatchesRule := by
  cases cv with
  | none => simp [wrongGuardIgnoresBypass]
  | some v => simp [wrongGuardIgnoresBypass]

def wrongGuardSmallNWorse : Option Verdict → Coverage → Rat → GuardResult
  | none, _, _ => .guardUntested
  | some completed, coverage, bypassRate =>
    if coverage = .noneSeen then .guardUntested
    else if GuardConditions completed coverage bypassRate then .guardMatchesRule else .guardWorse

theorem wrong_G1_small_n_is_worse (cov : Coverage) (br : Rat) :
    wrongGuardSmallNWorse (some .inconclusiveSmallN) cov br = .guardUntested := by
  cases cov <;> simp [wrongGuardSmallNWorse, GuardConditions]

def wrongGuardNoneSeenAsFull : Option Verdict → Coverage → Rat → GuardResult
  | none, _, _ => .guardUntested
  | some completed, coverage, bypassRate =>
    if completed = .inconclusiveSmallN then .guardUntested
    else if completed ≠ .firstLower ∧ coverage ≠ .partly ∧ bypassRate = 0 then .guardMatchesRule
    else .guardWorse

theorem wrong_G1_none_seen_matches (br : Rat) (h : br = 0) :
    wrongGuardNoneSeenAsFull (some .inconclusive) .noneSeen br = .guardUntested := by
  simp [wrongGuardNoneSeenAsFull, h]

def wrongCanReportNoPairNeeded (p : PlanFacts) : Prop :=
  p.noise = .noiseOk ∧ LooValid p.looProbe ∧ p.ruleReach ≠ .unknown

theorem wrong_L8_no_pair_needed (p : PlanFacts) (h : p.hasNoisePair = false) :
    ¬ wrongCanReportNoPairNeeded p := by
  intro hp
  simp_all [wrongCanReportNoPairNeeded, LooValid]

def wrongArmsNoInsurance : Verdict → Verdict → Bool → ArmVerdict
  | p, n, _ => threeArmVerdict p n false

theorem wrong_TA3_insurance_ignored :
    wrongArmsNoInsurance .firstHigher .firstHigher true = .insuranceKeep := by
  decide

def wrongArmsInsuranceBeforeSmallN : Verdict → Verdict → Bool → ArmVerdict
  | _, _, true => .insuranceKeep
  | p, n, false => threeArmVerdict p n false

theorem wrong_TA2_insurance_before_small_n :
    wrongArmsInsuranceBeforeSmallN .inconclusiveSmallN .firstHigher true = .inconclusive := by
  decide

def wrongArmsWorseThanNothingInconclusive : Verdict → Verdict → Bool → ArmVerdict
  | _, .firstLower, false => .inconclusive
  | p, n, clean => threeArmVerdict p n clean

theorem wrong_TA8_worse_than_nothing_not_delete :
    wrongArmsWorseThanNothingInconclusive .inconclusive .firstLower false = .deleteCandidate := by
  decide

def wrongArmsKeepIgnoresNothing : Verdict → Verdict → Bool → ArmVerdict
  | .firstHigher, .firstLower, false => .keepComponent
  | p, n, clean => threeArmVerdict p n clean

theorem wrong_TA4_keep_when_worse_than_nothing :
    wrongArmsKeepIgnoresNothing .firstHigher .firstLower false ≠ .keepComponent := by
  decide

def wrongArmsEqualNothingReplaced : Verdict → Verdict → Bool → ArmVerdict
  | .inconclusive, .inconclusive, false => .replaceWithPrompt
  | p, n, clean => threeArmVerdict p n clean

theorem wrong_TA6_equal_to_nothing_replaced :
    wrongArmsEqualNothingReplaced .inconclusive .inconclusive false = .deleteCandidate := by
  decide

def wrongArmsWorseThanPromptKept : Verdict → Verdict → Bool → ArmVerdict
  | .firstLower, .firstHigher, false => .keepComponent
  | p, n, clean => threeArmVerdict p n clean

theorem wrong_TA7_worse_than_prompt_kept :
    wrongArmsWorseThanPromptKept .firstLower .firstHigher false ≠ .keepComponent := by
  decide

def wrongArmsEqualPromptKept : Verdict → Verdict → Bool → ArmVerdict
  | .inconclusive, .firstHigher, false => .keepComponent
  | p, n, clean => threeArmVerdict p n clean

theorem wrong_TA5_equal_to_prompt_kept :
    wrongArmsEqualPromptKept .inconclusive .firstHigher false = .replaceWithPrompt := by
  decide

end Wrong
